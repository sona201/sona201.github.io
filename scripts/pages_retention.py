#!/usr/bin/env python3
"""Plan then prune old Pages snapshots inside the serialized publishing queue.

Keep the newest ten snapshots OR anything published within thirty days, plus
active/pending pointers and the reviewed safety baseline. No state pointer is
changed. Run this only after a completed transaction, never as part of recovery.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError

import pages_release

BASELINE_TAG = 'pages-snapshot-40663809678-1'
SNAPSHOT_TAG = re.compile(r'pages-snapshot-[A-Za-z0-9-]+\Z')
DEFAULT_RECENT = 10
DEFAULT_DAYS = 30


class RetentionError(ValueError):
    pass


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _time(value):
    if not isinstance(value, str):
        raise RetentionError('Missing snapshot publication time')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise RetentionError('Invalid snapshot publication time') from error
    if result.tzinfo is None:
        raise RetentionError('Snapshot time must include a timezone')
    return result.astimezone(timezone.utc)


def _now(value=None):
    value = datetime.now(timezone.utc) if value is None else value
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RetentionError('Retention clock must include a timezone')
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _stamp(value):
    return value.isoformat().replace('+00:00', 'Z')


def _state(client):
    release, state = pages_release.load_state(client)
    protected_tags, protected_ids = {BASELINE_TAG}, set()
    pointers = [state['active']]
    if state.get('pending') is not None:
        pending = state['pending']
        if not isinstance(pending, dict) or not {'base', 'candidate'} <= set(pending):
            raise RetentionError('Incomplete pending snapshot protection')
        pointers.extend([pending['base'], pending['candidate']])
    for pointer in pointers:
        pages_release.check_pointer(pointer)
        protected_tags.add(pointer['tag'])
        protected_ids.add(pointer['release_id'])
    identity = {'release_id': release['id'], 'state_sha256': _hash(state),
                'protected_tags': sorted(protected_tags), 'protected_ids': sorted(protected_ids)}
    return identity


def _releases(client):
    result, ids, tags = [], set(), set()
    for page in range(1, 101):
        batch = client.request(f'/releases?per_page=100&page={page}')
        if not isinstance(batch, list) or len(batch) > 100:
            raise RetentionError('Invalid release listing')
        for release in batch:
            if (not isinstance(release, dict) or type(release.get('id')) is not int
                    or release['id'] <= 0 or release['id'] in ids):
                raise RetentionError('Duplicate or invalid release listing')
            ids.add(release['id'])
            tag = release.get('tag_name')
            if not isinstance(tag, str) or not SNAPSHOT_TAG.fullmatch(tag):
                continue
            if tag in tags:
                raise RetentionError('Duplicate snapshot tag')
            tags.add(tag)
            result.append(release)
        if len(batch) < 100:
            return result
    raise RetentionError('Release listing is too large to verify safely')


def _record(release):
    tag = release.get('tag_name')
    if (not isinstance(tag, str) or not SNAPSHOT_TAG.fullmatch(tag)
            or type(release.get('id')) is not int or release['id'] <= 0):
        raise RetentionError('Only identified pages-snapshot releases can be deleted')
    # Do not use created_at: GitHub may derive it from the target commit.
    published = _time(release.get('published_at'))
    assets = release.get('assets', [])
    if not isinstance(assets, list) or any(not isinstance(asset, dict) for asset in assets):
        raise RetentionError('Invalid snapshot assets')
    stable = {key: release.get(key) for key in (
        'id', 'tag_name', 'draft', 'prerelease', 'published_at', 'updated_at', 'body', 'target_commitish')}
    stable['assets'] = [{key: asset.get(key) for key in ('id', 'name', 'size', 'updated_at', 'digest')}
                        for asset in assets]
    return {'release_id': release['id'], 'tag': tag, 'published_at': _stamp(published),
            'metadata_sha256': _hash(stable)}


def _tag(client, tag):
    if not SNAPSHOT_TAG.fullmatch(tag):
        raise RetentionError('Refusing a non-snapshot tag')
    ref = client.request('/git/ref/tags/' + tag)
    obj = ref.get('object', {})
    if (ref.get('ref') != 'refs/tags/' + tag or obj.get('type') not in {'commit', 'tag'}
            or not isinstance(obj.get('sha'), str) or not re.fullmatch(r'[0-9a-f]{40}', obj['sha'])):
        raise RetentionError('Snapshot tag identity is ambiguous')
    return {'type': obj['type'], 'sha': obj['sha']}


def plan_retention(client, *, now=None, keep_recent=DEFAULT_RECENT, keep_days=DEFAULT_DAYS):
    """Read-only plan; parameters may retain more than the safe defaults, never less."""
    if (type(keep_recent) is not int or keep_recent < DEFAULT_RECENT
            or type(keep_days) is not int or keep_days < DEFAULT_DAYS):
        raise RetentionError('Retention cannot be shorter than ten snapshots and thirty days')
    clock = _now(now)
    state = _state(client)
    records, kept = [], []
    for release in _releases(client):
        if release.get('draft') is not False:
            kept.append({'release_id': release['id'], 'tag': release['tag_name'], 'reason': 'unpublished'})
            continue
        records.append(_record(release))
    records.sort(key=lambda record: (_time(record['published_at']), record['release_id']), reverse=True)
    cutoff, delete = clock - timedelta(days=keep_days), []
    for index, record in enumerate(records):
        if record['tag'] in state['protected_tags'] or record['release_id'] in state['protected_ids']:
            reason = 'protected'
        elif index < keep_recent:
            reason = 'recent_count'
        elif _time(record['published_at']) >= cutoff:
            reason = 'recent_age'
        else:
            delete.append({**record, 'tag_object': _tag(client, record['tag'])})
            continue
        kept.append({**record, 'reason': reason})
    if _state(client) != state:
        raise RetentionError('Pages state changed while planning retention')
    return {'schema_version': 1, 'repository': client.repo, 'planned_at': _stamp(clock),
            'keep_recent': keep_recent, 'keep_days': keep_days, 'state': state,
            'keep': sorted(kept, key=lambda record: record['tag']),
            'delete': sorted(delete, key=lambda record: (record['published_at'], record['release_id']))}


def apply_retention(client, plan, *, now=None):
    """Revalidate the entire plan, then recheck each exact release and tag before deletion."""
    if not isinstance(plan, dict) or plan.get('schema_version') != 1 or plan.get('repository') != client.repo:
        raise RetentionError('Invalid retention plan or repository mismatch')
    clock, planned = _now(now), _time(plan.get('planned_at'))
    if planned > clock or clock - planned > timedelta(days=1):
        raise RetentionError('Retention plan is future-dated or older than one day')
    expected = plan_retention(client, now=planned, keep_recent=plan.get('keep_recent'), keep_days=plan.get('keep_days'))
    if plan != expected:
        raise RetentionError('Retention plan no longer matches current repository state')
    deleted = []
    for item in expected['delete']:
        if _state(client) != expected['state']:
            raise RetentionError('Pages state changed before snapshot deletion')
        release = client.request('/releases/' + str(item['release_id']))
        if _record(release) != {key: value for key, value in item.items() if key != 'tag_object'}:
            raise RetentionError('Snapshot release changed before deletion')
        if _tag(client, item['tag']) != item['tag_object']:
            raise RetentionError('Snapshot tag changed before deletion')
        client.request('/releases/' + str(item['release_id']), 'DELETE')
        # External changes still stop cleanup; a leftover tag is safer than deleting a moved ref.
        if _state(client) != expected['state'] or _tag(client, item['tag']) != item['tag_object']:
            raise RetentionError('State or tag changed after release deletion; tag retained')
        client.request('/git/refs/tags/' + item['tag'], 'DELETE')
        deleted.append({'release_id': item['release_id'], 'tag': item['tag']})
    return {'deleted': deleted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--output', type=Path, required=True)
    plan.add_argument('--keep-recent', type=int, default=DEFAULT_RECENT)
    plan.add_argument('--keep-days', type=int, default=DEFAULT_DAYS)
    apply = commands.add_parser('apply')
    apply.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    try:
        client = pages_release.GitHub()
        if args.command == 'plan':
            result = plan_retention(client, keep_recent=args.keep_recent, keep_days=args.keep_days)
            pages_release.save_json(args.output, result)
        else:
            result = apply_retention(client, pages_release.read_json(args.plan))
        print(json.dumps(result, indent=2))
        return 0
    except HTTPError as error:
        print(f'GitHub retention request failed (HTTP {error.code}); no response body logged.', file=sys.stderr)
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
