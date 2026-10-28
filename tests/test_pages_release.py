"""Exercise release transactions without changing GitHub or the live site."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
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
        with read, write, patch.object(releases, "wait_terminal") as wait, \
                patch.object(releases, "output") as output:
            releases.quiesce(self.work, self.client, deployment_outcome="failure")
        wait.assert_called_once_with(self.client, self.transaction["workflow_sha"], cancel=True)
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
