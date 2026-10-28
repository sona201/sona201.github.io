"""Exercise release transactions without changing GitHub or the live site."""
import copy
import io
import json
from pathlib import Path
import sys
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
                patch.object(releases, "upload_snapshot", return_value=self.candidate), \
                patch.dict(releases.os.environ, {"GITHUB_RUN_ID": "321", "GITHUB_RUN_ATTEMPT": "2",
                                                "GITHUB_SHA": "c" * 40}):
            releases.prepare(args, self.client)
        self.assertEqual(compose.call_args.kwargs["kind"], "cleanup")
        self.assertEqual(compose.call_args.kwargs["pr_number"], 7)
        self.assertIsNone(compose.call_args.kwargs["identity"])
        self.assertIsNone(compose.call_args.kwargs["site"])


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
        prefix = '/actions/runs/321/attempts/2/jobs?per_page=100&page='
        if path.startswith(prefix):
            return copy.deepcopy(self.pages[int(path[len(prefix):])])
        self.fail('Unexpected request: ' + path)

    def recover(self):
        releases.confirm_pending_deployment_stopped(self.client, self.pending)

    def test_completed_attempt_with_both_deployments_skipped_can_recover(self):
        self.recover()
        self.assertEqual(self.client.request.call_count, 4)
        self.assertIn('/attempts/2/jobs?', self.client.request.call_args_list[2].args[0])

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
        for change in ({'id': 999}, {'run_attempt': 3}):
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
        self.assertIn('/attempts/2/jobs?per_page=100&page=2', self.client.request.call_args_list[3].args[0])

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
