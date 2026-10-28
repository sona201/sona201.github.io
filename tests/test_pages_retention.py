"""Snapshot pruning uses read-only plans and never removes protected releases."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pages_retention as retention

NOW = datetime(2026, 10, 29, 0, 0, tzinfo=timezone.utc)


def release(number, days=None, tag=None):
    published = NOW - timedelta(days=60 - number if days is None else days)
    return {'id': number, 'tag_name': tag or f'pages-snapshot-{number}-1', 'draft': False,
            'prerelease': True, 'published_at': published.isoformat(),
            'created_at': '2000-01-01T00:00:00Z', 'updated_at': published.isoformat(),
            'body': '{}', 'assets': [], 'target_commitish': 'main'}


def pointer(number, tag=None):
    return {'release_id': number, 'tag': tag or f'pages-snapshot-{number}-1', 'manifest_sha256': 'a' * 64}


class FakeGitHub:
    repo = 'owner/site'

    def __init__(self):
        self.releases = [release(number) for number in range(1, 16)]
        self.releases.append(release(100, 200, retention.BASELINE_TAG))
        self.state = {'schema_version': 1, 'active': pointer(1), 'pending': None}
        self.calls = []
        self.tag_sha = 'b' * 40
        self.on_delete = None
        self.detail_override = None

    def request(self, path, method='GET', data=None):
        self.calls.append((path, method))
        if path == '/releases/tags/pages-state':
            return {'id': 9999, 'body': json.dumps(self.state)}
        if path.startswith('/releases?per_page=100&page='):
            page = int(path.rsplit('=', 1)[1])
            return copy.deepcopy(self.releases[(page - 1) * 100:page * 100])
        if path.startswith('/git/ref/tags/'):
            return {'ref': 'refs/tags/' + path[len('/git/ref/tags/'):],
                    'object': {'type': 'commit', 'sha': self.tag_sha}}
        if path.startswith('/git/refs/tags/') and method == 'DELETE':
            return None
        if path.startswith('/releases/'):
            number = int(path.rsplit('/', 1)[1])
            if method == 'DELETE':
                self.releases = [item for item in self.releases if item['id'] != number]
                if self.on_delete:
                    self.on_delete()
                return None
            item = copy.deepcopy(next(item for item in self.releases if item['id'] == number))
            if self.detail_override:
                item.update(self.detail_override)
            return item
        raise AssertionError('Unexpected API request: ' + method + ' ' + path)

    def mutations(self):
        return [(path, method) for path, method in self.calls if method != 'GET']


class SnapshotRetentionTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeGitHub()

    def plan(self, **kwargs):
        return retention.plan_retention(self.client, now=NOW, **kwargs)

    def test_plan_is_read_only_and_preserves_recent_count_and_baseline(self):
        plan = self.plan()
        self.assertEqual([item['release_id'] for item in plan['delete']], [2, 3, 4, 5])
        self.assertIn(retention.BASELINE_TAG, [item['tag'] for item in plan['keep']])
        self.assertFalse(self.client.mutations())
        self.assertNotIn('body', json.dumps(plan))

    def test_active_pending_base_and_candidate_are_all_protected(self):
        self.client.state['pending'] = {'base': pointer(2), 'candidate': pointer(3)}
        plan = self.plan()
        self.assertEqual([item['release_id'] for item in plan['delete']], [4, 5])

    def test_protected_release_id_survives_even_if_its_tag_changed(self):
        self.client.state['active']['tag'] = 'pages-snapshot-alias'
        self.assertNotIn(1, [item['release_id'] for item in self.plan()['delete']])

    def test_every_snapshot_within_age_window_is_retained_even_beyond_count(self):
        self.client.releases = [release(number, 20) for number in range(1, 30)]
        self.assertEqual(self.plan()['delete'], [])

    def test_publication_age_not_source_commit_age_controls_retention(self):
        self.client.releases[1]['published_at'] = (NOW - timedelta(days=1)).isoformat()
        self.assertNotIn(2, [item['release_id'] for item in self.plan()['delete']])

    def test_cutoff_boundary_is_retained_and_future_releases_are_not_deleted(self):
        self.client.releases = [release(number, 30) for number in range(1, 20)] + [release(30, -1)]
        self.assertEqual(self.plan()['delete'], [])

    def test_non_snapshot_and_malformed_snapshot_tags_are_never_candidates(self):
        self.client.releases.extend([release(201, 500, 'v1'), release(202, 500, 'pages-state'),
                                     release(203, 500, 'pages-snapshot-../main')])
        plan = self.plan()
        self.assertTrue(all(item['release_id'] < 200 for item in plan['delete']))

    def test_drafts_remain_untouched_without_publication_time(self):
        self.client.releases[1].update(draft=True, published_at=None)
        plan = self.plan()
        self.assertNotIn(2, [item['release_id'] for item in plan['delete']])
        self.assertEqual(next(item for item in plan['keep'] if item['release_id'] == 2)['reason'], 'unpublished')

    def test_missing_or_invalid_publication_time_blocks_deletion_plan(self):
        for stamp in (None, 'invalid', '2020-01-01T00:00:00'):
            with self.subTest(stamp=stamp):
                self.client.releases[1]['published_at'] = stamp
                with self.assertRaises(ValueError):
                    self.plan()
        self.assertFalse(self.client.mutations())

    def test_incomplete_pending_is_not_silently_ignored(self):
        self.client.state['pending'] = {'base': pointer(2)}
        with self.assertRaisesRegex(ValueError, 'Incomplete pending'):
            self.plan()

    def test_pagination_reads_the_complete_inventory(self):
        self.client.releases = [release(number, 100) for number in range(1, 106)]
        plan = self.plan()
        self.assertEqual(len(plan['delete']), 94)
        self.assertIn(('/releases?per_page=100&page=2', 'GET'), self.client.calls)

    def test_duplicate_paginated_release_is_rejected(self):
        self.client.releases = [release(number, 100) for number in range(1, 101)] + [release(1, 100)]
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.plan()

    def test_apply_deletes_only_planned_exact_release_and_tag_pairs(self):
        plan = self.plan()
        result = retention.apply_retention(self.client, plan, now=NOW)
        self.assertEqual([item['release_id'] for item in result['deleted']], [2, 3, 4, 5])
        self.assertEqual(self.client.mutations(), [(path, 'DELETE') for number in range(2, 6)
                         for path in (f'/releases/{number}', f'/git/refs/tags/pages-snapshot-{number}-1')])

    def test_forged_candidate_or_other_repository_plan_never_mutates(self):
        plan = self.plan()
        for change in ('candidate', 'repository'):
            with self.subTest(change=change):
                forged = copy.deepcopy(plan)
                if change == 'candidate':
                    forged['delete'][0]['tag'] = 'main'
                else:
                    forged['repository'] = 'someone/else'
                with self.assertRaises(ValueError):
                    retention.apply_retention(self.client, forged, now=NOW)
                self.assertFalse(self.client.mutations())

    def test_retention_parameters_cannot_weaken_safe_defaults(self):
        for params in ({'keep_recent': 0}, {'keep_recent': 9}, {'keep_days': 29}, {'keep_days': True}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                self.plan(**params)

    def test_future_or_stale_plan_is_rejected(self):
        plan = self.plan()
        for apply_time in (NOW - timedelta(seconds=1), NOW + timedelta(days=2)):
            with self.subTest(time=apply_time), self.assertRaisesRegex(ValueError, 'future-dated'):
                retention.apply_retention(self.client, plan, now=apply_time)
        self.assertFalse(self.client.mutations())

    def test_changed_active_or_new_pending_invalidates_the_whole_plan(self):
        plan = self.plan()
        self.client.state['active'] = pointer(2)
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            retention.apply_retention(self.client, plan, now=NOW)
        self.assertFalse(self.client.mutations())

    def test_release_changed_after_inventory_recheck_is_not_deleted(self):
        plan = self.plan()
        self.client.detail_override = {'body': '{"modified":true}'}
        with self.assertRaisesRegex(ValueError, 'release changed'):
            retention.apply_retention(self.client, plan, now=NOW)
        self.assertFalse(self.client.mutations())

    def test_moved_tag_invalidates_plan_before_release_deletion(self):
        plan = self.plan()
        self.client.tag_sha = 'c' * 40
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            retention.apply_retention(self.client, plan, now=NOW)
        self.assertFalse(self.client.mutations())

    def test_tag_changed_after_release_deletion_is_retained(self):
        plan = self.plan()
        self.client.on_delete = lambda: setattr(self.client, 'tag_sha', 'c' * 40)
        with self.assertRaisesRegex(ValueError, 'tag retained'):
            retention.apply_retention(self.client, plan, now=NOW)
        self.assertEqual(self.client.mutations(), [('/releases/2', 'DELETE')])


if __name__ == '__main__':
    unittest.main()
