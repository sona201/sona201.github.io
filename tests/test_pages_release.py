"""Exercise release transactions without changing GitHub or the live site."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pages_release as releases


class ReleaseTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.release = {"id": 1, "tag_name": "pages-state"}
        self.base = {"tag": "pages-snapshot-base", "release_id": 10,
                     "manifest_sha256": "a" * 64}
        self.candidate = {"tag": "pages-snapshot-321-2", "release_id": 11,
                          "manifest_sha256": "b" * 64}
        self.transaction = {
            "schema_version": 1, "id": "pages-snapshot-321-2", "kind": "production",
            "base": self.base, "candidate": self.candidate, "state_release_id": 1,
            "run_id": "321", "run_attempt": "2", "workflow_sha": "c" * 40,
            "verified": False, "restored": False,
        }
        self.state = {"schema_version": 1, "active": self.base, "pending": None}
        self.client = Mock()
        self.client.request.return_value = {"id": self.candidate["release_id"],
            "body": json.dumps({"manifest_sha256": self.candidate["manifest_sha256"]})}
        self.write_transaction()

    def write_transaction(self):
        (self.work / "transaction.json").write_text(json.dumps(self.transaction))

    def pending(self):
        return {key: copy.deepcopy(self.transaction[key]) for key in (
            "id", "base", "candidate", "run_id", "run_attempt", "workflow_sha")}

    def state_mocks(self):
        read = patch.object(releases, "load_state", return_value=(
            copy.deepcopy(self.release), copy.deepcopy(self.state)))
        write = patch.object(releases, "write_state")
        return read, write

    def test_begin_records_both_snapshots_before_deployment(self):
        read, write = self.state_mocks()
        with read, write as save:
            releases.begin(self.work, self.client)
        save.assert_called_once()
        stored = save.call_args.args[-1]
        self.assertEqual(stored["active"], self.base)
        self.assertEqual(stored["pending"]["id"], self.transaction["id"])
        self.assertEqual(stored["pending"]["base"], self.base)
        self.assertEqual(stored["pending"]["candidate"], self.candidate)

    def test_begin_refuses_baseline_changed_after_prepare(self):
        self.state["active"] = {**self.base, "tag": "pages-snapshot-newer"}
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.begin(self.work, self.client)
        save.assert_not_called()

    def test_begin_refuses_an_interrupted_or_other_pending_transaction(self):
        self.state["pending"] = {**self.pending(), "id": "pages-snapshot-interrupted"}
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.begin(self.work, self.client)
        save.assert_not_called()

    def test_commit_requires_completed_online_verification(self):
        self.state["pending"] = self.pending()
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.commit(self.work, self.client)
        save.assert_not_called()

    def test_verified_commit_atomically_advances_active_and_clears_pending(self):
        self.transaction["verified"] = True
        self.write_transaction()
        self.state["pending"] = self.pending()
        read, write = self.state_mocks()
        with read, write as save:
            releases.commit(self.work, self.client)
        save.assert_called_once()
        stored = save.call_args.args[-1]
        self.assertEqual(stored["active"], self.candidate)
        self.assertIsNone(stored["pending"])

    def test_commit_cannot_advance_another_pending_transaction(self):
        self.transaction["verified"] = True
        self.write_transaction()
        self.state["pending"] = {**self.pending(), "id": "pages-snapshot-another"}
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.commit(self.work, self.client)
        save.assert_not_called()

    def test_commit_refuses_a_changed_active_baseline(self):
        self.transaction["verified"] = True
        self.write_transaction()
        self.state["pending"] = self.pending()
        self.state["active"] = {**self.base, "tag": "pages-snapshot-newer"}
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.commit(self.work, self.client)
        save.assert_not_called()

    def test_abort_requires_verified_restoration(self):
        self.state["pending"] = self.pending()
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.abort(self.work, self.client)
        save.assert_not_called()

    def test_abort_keeps_previous_active_only_after_restoration(self):
        self.transaction["restored"] = True
        self.write_transaction()
        self.state["pending"] = self.pending()
        read, write = self.state_mocks()
        with read, write as save:
            releases.abort(self.work, self.client)
        save.assert_called_once()
        stored = save.call_args.args[-1]
        self.assertEqual(stored["active"], self.base)
        self.assertIsNone(stored["pending"])

    def test_abort_cannot_clear_another_pending_transaction(self):
        self.transaction["restored"] = True
        self.write_transaction()
        self.state["pending"] = {**self.pending(), "id": "pages-snapshot-another"}
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.abort(self.work, self.client)
        save.assert_not_called()

    def test_abort_cannot_rewind_a_newer_active_state(self):
        self.transaction["restored"] = True
        self.write_transaction()
        self.state["pending"] = self.pending()
        self.state["active"] = {**self.base, "tag": "pages-snapshot-newer"}
        read, write = self.state_mocks()
        with read, write as save, self.assertRaises(ValueError):
            releases.abort(self.work, self.client)
        save.assert_not_called()

    def test_lost_commit_response_does_not_roll_back_committed_site(self):
        self.state.update(active=self.candidate, pending=None)
        read, write = self.state_mocks()
        with read, write as save, patch.object(releases, "wait_terminal") as wait, \
                patch.object(releases, "output") as output:
            releases.quiesce(self.work, self.client, deployment_outcome="success")
        wait.assert_not_called()
        save.assert_not_called()
        output.assert_called_once_with(recovery_needed=False)

    def test_quiesce_rejects_someone_elses_pending_transaction(self):
        self.state["pending"] = {**self.pending(), "id": "pages-snapshot-another"}
        read, write = self.state_mocks()
        with read, write, patch.object(releases, "wait_terminal") as wait, \
                patch.object(releases, "output") as output, self.assertRaises(ValueError):
            releases.quiesce(self.work, self.client, deployment_outcome="failure")
        wait.assert_not_called()
        output.assert_not_called()

    def test_quiesce_must_confirm_failed_deployment_has_stopped(self):
        self.state["pending"] = self.pending()
        read, write = self.state_mocks()
        with read, write, patch.object(releases, "wait_terminal",
                side_effect=ValueError("status unknown")) as wait, \
                patch.object(releases, "output") as output, self.assertRaises(ValueError):
            releases.quiesce(self.work, self.client, deployment_outcome="failure")
        wait.assert_called_once_with(self.client, self.transaction["workflow_sha"], cancel=True)
        output.assert_not_called()

    def test_quiesce_allows_restore_after_terminal_confirmation(self):
        self.state["pending"] = self.pending()
        read, write = self.state_mocks()
        with read, write, patch.object(releases, "wait_terminal", return_value="deployment_cancelled") as wait, \
                patch.object(releases, "output") as output:
            releases.quiesce(self.work, self.client, deployment_outcome="failure")
        wait.assert_called_once_with(self.client, self.transaction["workflow_sha"], cancel=True)
        output.assert_called_once_with(recovery_needed=True)

    def test_failed_action_cannot_use_older_same_sha_success_to_authorize_restore(self):
        self.state["pending"] = self.pending()
        candidate_marker = json.dumps({"schema_version": 1, "snapshot_id": self.transaction["id"]}).encode()
        (self.work / "site").mkdir()
        (self.work / "site" / releases.snapshot.GENERATION_FILE).write_bytes(candidate_marker)
        older_marker = json.dumps({"schema_version": 1, "snapshot_id": "pages-snapshot-older"}).encode()
        read, write = self.state_mocks()
        with read, write as save, patch.object(releases, "wait_terminal", return_value="succeed"), \
                patch.object(releases, "fetch_public", return_value=older_marker), \
                patch.object(releases, "output") as output, self.assertRaises(ValueError):
            releases.quiesce(self.work, self.client, deployment_outcome="failure")
        save.assert_not_called()
        output.assert_not_called()

    def test_failed_action_can_restore_after_candidate_generation_is_confirmed(self):
        self.state["pending"] = self.pending()
        marker = json.dumps({"schema_version": 1, "snapshot_id": self.transaction["id"]}).encode()
        (self.work / "site").mkdir()
        (self.work / "site" / releases.snapshot.GENERATION_FILE).write_bytes(marker)
        read, write = self.state_mocks()
        with read, write, patch.object(releases, "wait_terminal", return_value="succeed"), \
                patch.object(releases, "fetch_public", return_value=marker) as fetch, \
                patch.object(releases, "output") as output:
            releases.quiesce(self.work, self.client, deployment_outcome="failure")
        self.assertIn(releases.snapshot.GENERATION_FILE, fetch.call_args.args[0])
        self.assertIn(self.transaction["id"], fetch.call_args.args[0])
        output.assert_called_once_with(recovery_needed=True)

    def test_prepare_cleanup_accepts_minimal_authorization_context(self):
        context = self.work / "context.json"
        context.write_text(json.dumps({"action": "cleanup", "pr_number": "7"}))
        args = SimpleNamespace(work=self.work / "prepared", kind="cleanup", site=None,
                               context=context, target=None)
        with patch.object(releases, "load_state", return_value=(self.release, self.state)), \
                patch.object(releases, "download_snapshot"), \
                patch.object(releases, "verify_tree"), \
                patch.object(releases.snapshot, "compose") as compose, \
                patch.object(releases, "reconcile_previews", return_value=[9]), \
                patch.object(releases, "upload_snapshot", return_value=self.candidate), \
                patch.dict(releases.os.environ, {"GITHUB_RUN_ID": "321", "GITHUB_RUN_ATTEMPT": "2",
                                                "GITHUB_SHA": "c" * 40}):
            releases.prepare(args, self.client)
        self.assertEqual(compose.call_args.kwargs["kind"], "cleanup")
        self.assertEqual(compose.call_args.kwargs["pr_number"], 7)
        self.assertIsNone(compose.call_args.kwargs["identity"])
        self.assertIsNone(compose.call_args.kwargs["site"])
        self.assertEqual(json.loads((args.work / 'transaction.json').read_text())['removed_previews'], [9])
        with patch.dict(releases.os.environ, {'GITHUB_STEP_SUMMARY': str(self.work / 'summary.md')}), patch('builtins.print'):
            releases.summary(args.work)
        self.assertIn('pr-9', (self.work / 'summary.md').read_text())


class InterruptedDeploymentRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.pending = {'run_id': '321', 'run_attempt': '2', 'workflow_sha': 'c' * 40}
        self.run = {'id': 321, 'run_attempt': 2, 'status': 'completed'}
        self.job = {'id': 901, 'run_id': 321, 'run_attempt': 2, 'status': 'completed',
                    'name': 'publish / transaction', 'head_sha': 'd' * 40, 'steps': [
            {'name': 'Persist the pending deployment transaction', 'number': 10,
             'status': 'completed', 'conclusion': 'cancelled'},
            {'name': 'Deploy candidate through official GitHub Pages action', 'number': 11,
             'status': 'completed', 'conclusion': 'skipped'},
            {'name': 'Restore the previous complete site through GitHub Pages', 'number': 16,
             'status': 'completed', 'conclusion': 'skipped'},
        ]}
        self.pages = {1: {'total_count': 1, 'jobs': [self.job]}}
        self.attempts = {2: {'id': 321, 'run_attempt': 2, 'status': 'completed'}}
        self.later_pages = {}
        self.deployment_error = 404
        self.client = Mock()
        self.client.request.side_effect = self.request

    def request(self, path):
        if path == '/actions/runs/321':
            return copy.deepcopy(self.run)
        if path == '/pages/deployments/' + 'c' * 40:
            if self.deployment_error:
                error = HTTPError('https://api.github.com' + path, self.deployment_error, 'Test response', {}, io.BytesIO())
                self.addCleanup(error.close)
                raise error
            return {'status': 'succeed'}
        prefix = '/actions/runs/321/attempts/'
        if path.startswith(prefix):
            rest = path[len(prefix):]
            if '/' not in rest:
                return copy.deepcopy(self.attempts[int(rest)])
            attempt, page = rest.split('/jobs?per_page=100&page=')
            pages = self.pages if int(attempt) == 2 else self.later_pages[int(attempt)]
            return copy.deepcopy(pages[int(page)])
        self.fail('Unexpected request: ' + path)

    def recover(self):
        releases.confirm_pending_deployment_stopped(self.client, self.pending)

    def test_completed_attempt_with_both_deployments_skipped_can_recover(self):
        self.recover()
        self.assertEqual(self.client.request.call_count, 5)
        self.assertIn('/attempts/2/jobs?', self.client.request.call_args_list[3].args[0])

    def test_prepare_active_continues_after_proven_predeployment_interruption(self):
        base = {'tag': 'pages-snapshot-base', 'release_id': 10, 'manifest_sha256': 'a' * 64}
        state = {'schema_version': 1, 'active': base, 'pending': self.pending}
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'recovery'
            args = SimpleNamespace(work=work, kind='rollback', target='active', site=None, context=None)
            with patch.object(releases, 'load_state', return_value=({'id': 1}, state)), \
                    patch.object(releases, 'download_snapshot') as download, \
                    patch.object(releases, 'verify_tree') as verify, \
                    patch.object(releases.snapshot, 'compose') as compose, \
                    patch.object(releases, 'reconcile_previews', return_value=[]), \
                    patch.object(releases, 'upload_snapshot', return_value=base), \
                    patch.dict(releases.os.environ, {'GITHUB_RUN_ID': '456', 'GITHUB_RUN_ATTEMPT': '1',
                                                    'GITHUB_SHA': 'e' * 40}):
                releases.prepare(args, self.client)
            download.assert_called_once()
            verify.assert_not_called()
            self.assertEqual(compose.call_args.kwargs['site'], work / 'previous')
            self.assertEqual(json.loads((work / 'transaction.json').read_text())['recovering_pending'], self.pending)

    def test_known_terminal_deployment_keeps_legacy_pending_compatible(self):
        self.deployment_error = None
        self.pending.pop('run_attempt')
        self.recover()
        self.assertEqual(self.client.request.call_count, 2)

    def test_job_attempt_field_is_optional_on_the_attempt_specific_endpoint(self):
        self.job.pop('run_attempt')
        self.job['name'] = 'rollback / transaction'
        self.recover()

    def test_running_original_workflow_is_never_overridden(self):
        self.run['status'] = 'in_progress'
        with self.assertRaisesRegex(ValueError, 'still active'):
            self.recover()
        self.client.request.assert_called_once_with('/actions/runs/321')

    def test_non_404_deployment_error_never_uses_skipped_step_fallback(self):
        for code in (403, 500):
            with self.subTest(code=code):
                self.deployment_error = code
                self.client.reset_mock()
                with self.assertRaises(HTTPError):
                    self.recover()
                self.assertEqual(self.client.request.call_count, 2)

    def test_404_during_quiescence_is_not_treated_as_no_deployment(self):
        self.deployment_error = None
        original = self.request
        self.client.request.side_effect = lambda path: (
            {'status': 'deployment_in_progress'} if path.startswith('/pages/deployments/') else original(path))
        error = HTTPError('test', 404, 'Missing', {}, io.BytesIO())
        self.addCleanup(error.close)
        with patch.object(releases, 'wait_terminal', side_effect=error) as wait:
            with self.assertRaises(HTTPError):
                self.recover()
        wait.assert_called_once_with(self.client, 'c' * 40, cancel=True)
        self.assertEqual(self.client.request.call_count, 2)

    def test_never_uses_another_run_or_attempt_as_absence_evidence(self):
        for change in ({'id': 999}, {'run_attempt': 1}):
            with self.subTest(change=change):
                self.run.update(change)
                with self.assertRaisesRegex(ValueError, 'Cannot bind'):
                    self.recover()
                self.run = {'id': 321, 'run_attempt': 2, 'status': 'completed'}
        self.pending.pop('run_attempt')
        with self.assertRaisesRegex(ValueError, 'Cannot bind'):
            self.recover()

    def test_executed_or_ambiguous_candidate_and_restore_steps_block_recovery(self):
        for index in (1, 2):
            for conclusion in ('success', 'failure', 'cancelled', 'timed_out', None):
                with self.subTest(step=index, conclusion=conclusion):
                    self.job['steps'][index]['conclusion'] = conclusion
                    with self.assertRaisesRegex(ValueError, 'may have started'):
                        self.recover()
            self.job['steps'][index]['conclusion'] = 'skipped'
            self.job['steps'][index]['status'] = 'queued'
            with self.assertRaisesRegex(ValueError, 'may have started'):
                self.recover()
            self.job['steps'][index]['status'] = 'completed'

    def test_missing_duplicate_or_reordered_steps_are_not_evidence(self):
        original = copy.deepcopy(self.job['steps'])
        variants = [original[:-1], original + [original[1]],
                    [{**original[0], 'number': 12}, *original[1:]]]
        for steps in variants:
            with self.subTest(steps=steps):
                self.job['steps'] = steps
                with self.assertRaises(ValueError):
                    self.recover()

    def test_wrong_job_identity_or_incomplete_job_is_rejected(self):
        original = copy.deepcopy(self.job)
        for change in ({'run_id': 999}, {'run_attempt': 1}, {'status': 'in_progress'}, {'id': None}):
            with self.subTest(change=change):
                self.job.update(change)
                with self.assertRaisesRegex(ValueError, 'do not match'):
                    self.recover()
                self.job.clear()
                self.job.update(copy.deepcopy(original))

    def paginated_jobs(self):
        others = [{'id': number, 'run_id': 321, 'status': 'completed', 'name': 'other'}
                  for number in range(100)]
        self.pages = {1: {'total_count': 101, 'jobs': others},
                      2: {'total_count': 101, 'jobs': [self.job]}}

    def test_reads_later_job_pages_before_accepting_evidence(self):
        self.paginated_jobs()
        self.recover()
        self.assertIn('/attempts/2/jobs?per_page=100&page=2', self.client.request.call_args_list[4].args[0])

    def test_duplicate_transaction_on_later_page_blocks_recovery(self):
        self.paginated_jobs()
        self.pages[1]['jobs'][0] = {**self.job, 'id': 900}
        with self.assertRaisesRegex(ValueError, 'one interrupted'):
            self.recover()

    def test_partial_changing_or_duplicate_pagination_blocks_recovery(self):
        for case in ('partial', 'changing', 'duplicate', 'empty'):
            with self.subTest(case=case):
                self.paginated_jobs()
                if case == 'partial':
                    self.pages[1]['jobs'].pop()
                elif case == 'changing':
                    self.pages[2]['total_count'] = 102
                elif case == 'duplicate':
                    self.pages[2]['jobs'][0] = self.pages[1]['jobs'][0]
                else:
                    self.pages[2]['jobs'] = []
                with self.assertRaises(ValueError):
                    self.recover()

    def test_rerun_started_during_evidence_check_blocks_recovery(self):
        original = self.request
        def request(path):
            result = original(path)
            if '/attempts/2/jobs?' in path:
                self.run.update(run_attempt=3, status='in_progress')
            return result
        self.client.request.side_effect = request
        with self.assertRaisesRegex(ValueError, 'changed while checking'):
            self.recover()

    def add_blocked_rerun(self, attempt):
        self.run['run_attempt'] = attempt
        self.attempts[attempt] = {'id': 321, 'run_attempt': attempt, 'status': 'completed'}
        job = copy.deepcopy(self.job)
        job.update(id=900 + attempt, run_attempt=attempt)
        job['steps'][0]['conclusion'] = 'skipped'
        job['steps'].insert(0, {'name': 'Prepare a complete immutable site snapshot', 'number': 7,
                                'status': 'completed', 'conclusion': 'failure'})
        self.later_pages[attempt] = {1: {'total_count': 1, 'jobs': [job]}}
        return job

    def test_completed_reruns_blocked_in_prepare_do_not_prevent_recovery(self):
        self.add_blocked_rerun(3)
        self.add_blocked_rerun(4)
        self.recover()
        for attempt in (2, 3, 4):
            self.assertIn(unittest.mock.call(f'/actions/runs/321/attempts/{attempt}'),
                          self.client.request.call_args_list)

    def test_any_later_attempt_that_deployed_blocks_recovery(self):
        for index in (2, 3):
            with self.subTest(index=index):
                job = self.add_blocked_rerun(3)
                job['steps'][index]['conclusion'] = 'failure'
                with self.assertRaisesRegex(ValueError, 'may have started'):
                    self.recover()

    def test_skipped_begin_without_failed_prepare_is_not_evidence(self):
        job = self.add_blocked_rerun(3)
        job['steps'][0]['conclusion'] = 'skipped'
        with self.assertRaisesRegex(ValueError, 'stopped before'):
            self.recover()

    def test_original_attempt_cannot_claim_a_skipped_begin(self):
        self.job['steps'][0]['conclusion'] = 'skipped'
        with self.assertRaisesRegex(ValueError, 'may have started'):
            self.recover()

    def test_each_attempt_metadata_must_match_and_be_completed(self):
        for change in ({'id': 999}, {'run_attempt': 3}, {'status': 'in_progress'}):
            with self.subTest(change=change):
                self.attempts[2] = {'id': 321, 'run_attempt': 2, 'status': 'completed', **change}
                with self.assertRaisesRegex(ValueError, 'completed interrupted'):
                    self.recover()


class PreviewReconciliationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.previous = self.root / 'previous'
        self.previous.mkdir()
        self.component(self.previous)
        (self.previous / 'deployment-info.json').write_text(json.dumps({
            'schema_version': 1, 'snapshot_id': 'pages-snapshot-test'}))
        for number in (7, 8):
            self.component(self.previous / 'previews' / f'pr-{number}', number)
        self.site = self.root / 'candidate'
        shutil.copytree(self.previous, self.site)
        self.client = Mock(repo='owner/site')
        self.prs = {number: {'number': number, 'state': 'open', 'base': {'ref': 'main'},
            'head': {'sha': 'b' * 40, 'repo': {'full_name': 'owner/site'}},
            'labels': [{'name': 'preview'}]} for number in (7, 8)}
        self.client.request.side_effect = lambda path: self.prs[int(path.rsplit('/', 1)[-1])]
        self.previous_files = self.files(self.previous)

    def files(self, root):
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob('*') if path.is_file()}

    def component(self, root, number=None):
        root.mkdir(parents=True, exist_ok=True)
        (root / 'index.html').write_text('reviewed public content')
        (root / 'build-info.json').write_text(json.dumps({
            'schema_version': 1, 'source_sha': 'a' * 40, 'run_id': '1-1',
            'kind': 'production' if number is None else 'preview',
            'base_url': 'https://example.invalid/' + (f'previews/pr-{number}/' if number else '')}))
        (root / 'site-manifest.json').write_text(json.dumps({'schema_version': 1, 'files': {
            name: hashlib.sha256(body).hexdigest() for name, body in self.files(root).items()}}))

    def test_authorized_preview_is_retained_even_if_pr_head_changed(self):
        self.assertEqual(releases.reconcile_previews(self.site, self.client), [])
        self.assertEqual(self.files(self.site), self.previous_files)

    def test_retired_preview_is_removed_only_from_candidate(self):
        for reason in ('closed', 'retargeted', 'unlabeled', 'other_repo', 'deleted_repo'):
            with self.subTest(reason=reason):
                shutil.rmtree(self.site)
                shutil.copytree(self.previous, self.site)
                pr = copy.deepcopy(self.prs[8])
                pr['number'] = 7
                if reason == 'closed':
                    pr['state'] = 'closed'
                elif reason == 'retargeted':
                    pr['base']['ref'] = 'maintenance'
                elif reason == 'unlabeled':
                    pr['labels'] = []
                elif reason == 'other_repo':
                    pr['head']['repo']['full_name'] = 'other/site'
                else:
                    pr['head']['repo'] = None
                self.prs[7] = pr
                self.assertEqual(releases.reconcile_previews(self.site, self.client), [7])
                self.assertFalse((self.site / 'previews/pr-7').exists())
                self.assertTrue((self.site / 'previews/pr-8').exists())
                self.assertEqual(self.files(self.previous), self.previous_files)
                self.assertEqual(set(releases.snapshot.validate(self.site)['previews']), {'8'})

    def test_api_404_does_not_delete_a_preview_or_partially_change_candidate(self):
        self.prs[7]['state'] = 'closed'
        error = HTTPError('test', 404, 'not found', {}, io.BytesIO())
        self.addCleanup(error.close)
        self.client.request.side_effect = [self.prs[7], error]
        with self.assertRaises(HTTPError):
            releases.reconcile_previews(self.site, self.client)
        self.assertEqual(self.files(self.site), self.previous_files)
        self.assertEqual(self.files(self.previous), self.previous_files)

    def test_missing_or_inconsistent_authority_does_not_authorize_deletion(self):
        original = copy.deepcopy(self.prs[7])
        for change in ({'number': 9}, {'state': 'unknown'}, {'base': {}}, {'head': {}},
                       {'labels': None}, {'labels': [{}]}, {'head': {'repo': {}}}):
            with self.subTest(change=change):
                self.prs[7] = {**original, **change}
                with self.assertRaises(ValueError):
                    releases.reconcile_previews(self.site, self.client)
                self.assertEqual(self.files(self.site), self.previous_files)

    def test_invalid_snapshot_is_rejected_before_any_authority_lookup(self):
        (self.site / 'previews/pr-7/index.html').write_text('unexpected change')
        with self.assertRaises(ValueError):
            releases.reconcile_previews(self.site, self.client)
        self.client.request.assert_not_called()


class PrivacyRollbackPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = releases.privacy_policy()
        self.baseline = {**self.policy['reviewed_baselines'][0], 'release_id': 10}
        self.future = {'tag': 'pages-snapshot-900-1', 'release_id': 11,
                       'manifest_sha256': 'b' * 64,
                       'privacy_policy_version': self.policy['policy_version'],
                       'privacy_gate_passed': True}

    def test_exact_reviewed_baseline_is_allowed_without_relying_on_source_history(self):
        self.assertEqual(releases.require_safe_snapshot(self.baseline), self.baseline)
        for change in ({'tag': 'pages-snapshot-other'}, {'manifest_sha256': 'f' * 64}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'privacy policy'):
                releases.require_safe_snapshot({**self.baseline, **change})

    def test_future_snapshot_requires_current_policy_and_successful_gate(self):
        self.assertEqual(releases.require_safe_snapshot(self.future), self.future)
        for change in ({'privacy_policy_version': 'old'}, {'privacy_gate_passed': False},
                       {'privacy_gate_passed': 'true'}, {'privacy_policy_version': None}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'privacy policy'):
                releases.require_safe_snapshot({**self.future, **change})

    def test_verified_alone_does_not_authorize_a_historical_rollback(self):
        client = Mock()
        client.request.return_value = {'id': 10, 'body': json.dumps({
            'verified': True, 'manifest_sha256': 'a' * 64})}
        with self.assertRaisesRegex(ValueError, 'privacy policy'):
            releases.pointer_for_tag(client, 'pages-snapshot-old')

    def test_release_body_cannot_spoof_the_reviewed_baseline_tag(self):
        client = Mock()
        client.request.return_value = {'id': 10, 'body': json.dumps({**self.baseline, 'verified': True})}
        with self.assertRaisesRegex(ValueError, 'privacy policy'):
            releases.pointer_for_tag(client, 'pages-snapshot-old')

    def test_unsafe_baseline_is_rejected_before_download(self):
        client = Mock()
        with self.assertRaisesRegex(ValueError, 'privacy policy'):
            releases.download_snapshot(client, {'tag': 'pages-snapshot-old', 'release_id': 10,
                                               'manifest_sha256': 'a' * 64}, Path('unused'), Path('unused'))
        client.request.assert_not_called()

    def test_legacy_sha_is_rejected_before_any_state_or_filesystem_change(self):
        client = Mock()
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / 'unused'
            args = SimpleNamespace(kind='rollback', target='c' * 40, work=work)
            with self.assertRaisesRegex(ValueError, 'Legacy SHA'):
                releases.prepare(args, client)
            self.assertFalse(work.exists())
        client.request.assert_not_called()

    def test_failed_gate_never_creates_a_release(self):
        client = Mock()
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(releases, 'run_privacy_gate', side_effect=ValueError('rejected')), \
                patch.object(releases.snapshot, 'make_archive') as archive:
            with self.assertRaisesRegex(ValueError, 'rejected'):
                releases.upload_snapshot(client, Path(temporary), Path(temporary), 'pages-snapshot-900-1')
        archive.assert_not_called()
        client.request.assert_not_called()

    def test_successful_trusted_gate_attests_the_new_release(self):
        client = Mock()
        client.request.side_effect = [{'commit': {'sha': 'c' * 40}}, {'id': 11}]
        def archive(site, zip_path, manifest_path, **kwargs):
            zip_path.write_bytes(b'test archive')
            manifest_path.write_text('{}')
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(releases, 'run_privacy_gate') as gate, \
                patch.object(releases.snapshot, 'make_archive', side_effect=archive):
            pointer = releases.upload_snapshot(client, Path(temporary), Path(temporary), 'pages-snapshot-900-1')
        gate.assert_called_once()
        self.assertTrue(pointer['privacy_gate_passed'])
        self.assertEqual(pointer['privacy_policy_version'], self.policy['policy_version'])
        self.assertTrue(json.loads(client.request.call_args.args[2]['body'])['privacy_gate_passed'])


class RedirectAndDeploymentTests(unittest.TestCase):
    def test_asset_redirect_removes_bearer_on_host_change(self):
        handler = releases.SafeRedirects()
        request = Request("https://api.github.com/repos/owner/blog/releases/assets/1",
                          headers={"Authorization": "Bearer test-secret", "Accept": "application/octet-stream"})
        redirected = handler.redirect_request(request, None, 302, "Found", {},
            "https://release-assets.githubusercontent.com/assets/1?signature=example")
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")

    def test_untrusted_or_plain_http_asset_redirect_is_rejected(self):
        handler = releases.SafeRedirects()
        request = Request("https://api.github.com/repos/owner/blog/releases/assets/1",
                          headers={"Authorization": "Bearer test-secret"})
        for url in ("https://attacker.example/file", "http://release-assets.githubusercontent.com/file",
                    "https://api.github.com.attacker.example/file"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, "Found", {}, url)

    def test_terminal_deployment_is_not_cancelled(self):
        client = Mock()
        client.request.return_value = {"status": "succeed"}
        releases.wait_terminal(client, "c" * 40, cancel=True)
        client.request.assert_called_once_with("/pages/deployments/" + "c" * 40)

    def test_cancellation_waits_until_terminal_status(self):
        client = Mock()
        client.request.side_effect = [{"status": "deployment_in_progress"}, {},
                                      {"status": "deployment_cancelled"}]
        with patch.object(releases.time, "sleep") as sleep:
            releases.wait_terminal(client, "c" * 40, cancel=True)
        self.assertEqual(client.request.call_args_list[1].args,
                         ("/pages/deployments/" + "c" * 40 + "/cancel", "POST"))
        self.assertEqual(client.request.call_count, 3)
        sleep.assert_called_once()

    def test_ambiguous_deployment_status_timeout_is_fail_closed(self):
        client = Mock()
        client.request.return_value = {"status": "unknown_status"}
        with patch.object(releases.time, "monotonic", side_effect=[0, 0, 121]), \
                patch.object(releases.time, "sleep"), self.assertRaises(ValueError):
            releases.wait_terminal(client, "c" * 40, cancel=True)


if __name__ == "__main__":
    unittest.main()
