import copy
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location("workflow_context", Path(__file__).resolve().parents[1] / "scripts/workflow_context.py")
context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(context)


class PublicationAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.event = {"workflow_run": {"id": 100, "run_attempt": 2}}
        self.run = {"id": 100, "workflow_id": 12, "run_attempt": 2, "status": "completed",
                    "conclusion": "success", "head_repository": {"full_name": "owner/blog"},
                    "event": "pull_request", "head_branch": "feature", "head_sha": self.sha,
                    "pull_requests": [{"number": 42}]}
        self.pr = {"state": "open", "base": {"ref": "main"},
                   "head": {"sha": self.sha, "repo": {"full_name": "owner/blog"}},
                   "labels": [{"name": "preview"}]}

    def get(self, path):
        return {"actions/runs/100": self.run, "actions/workflows/deploy.yml": {"id": 12},
                "pulls/42": self.pr, "branches/main": {"commit": {"sha": self.sha}}}[path]

    def resolve(self):
        return context.resolve("workflow_run", self.event, "owner/blog", self.get)

    def test_preview_binds_current_head_run_attempt_and_number_from_api(self):
        result = self.resolve()
        self.assertEqual(result["action"], "preview")
        self.assertEqual(result["artifact_name"], "blog-site-100-2")
        self.assertEqual(result["build_id"], "100-2")
        self.assertEqual(result["base_url"], "https://sona201.github.io/previews/pr-42/")

    def test_fork_closed_unlabelled_and_stale_pr_are_not_published(self):
        original = copy.deepcopy(self.pr)
        for field in ("fork", "closed", "label", "sha"):
            self.pr = copy.deepcopy(original)
            if field == "fork": self.pr["head"]["repo"]["full_name"] = "stranger/blog"
            if field == "closed": self.pr["state"] = "closed"
            if field == "label": self.pr["labels"] = []
            if field == "sha": self.pr["head"]["sha"] = "b" * 40
            with self.subTest(field=field):
                self.assertEqual(self.resolve(), {"action": "skip"})

    def test_wrong_workflow_failed_run_and_old_attempt_are_rejected(self):
        for key, value in (("workflow_id", 99), ("conclusion", "failure"), ("run_attempt", 3)):
            old = self.run[key]
            self.run[key] = value
            self.assertEqual(self.resolve(), {"action": "skip"})
            self.run[key] = old

    def test_production_requires_current_main(self):
        self.run.update(event="push", head_branch="main")
        self.assertEqual(self.resolve()["action"], "production")
        self.run["head_sha"] = "b" * 40
        self.assertEqual(self.resolve()["action"], "skip")

    def test_cleanup_rechecks_closed_or_revoked_state(self):
        event = {"action": "closed", "pull_request": {"number": 42}}
        self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get)["action"], "skip")
        self.pr["state"] = "closed"
        self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get)["action"], "cleanup")

    def test_retargeted_preview_is_cleaned_on_edit_close_and_unlabel(self):
        self.pr["base"]["ref"] = "maintenance"
        for action in ("edited", "closed", "unlabeled"):
            with self.subTest(action=action):
                event = {"action": action, "pull_request": {"number": 42}}
                self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get),
                                 {"action": "cleanup", "pr_number": "42"})

    def test_edited_valid_preview_is_not_removed_and_fork_cannot_request_cleanup(self):
        event = {"action": "edited", "pull_request": {"number": 42}}
        self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get), {"action": "skip"})
        self.pr["base"]["ref"] = "maintenance"
        self.pr["head"]["repo"]["full_name"] = "stranger/blog"
        self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get), {"action": "skip"})

    def test_cleanup_uses_current_api_labels_and_base_instead_of_stale_event(self):
        event = {"action": "unlabeled", "label": {"name": "preview"}, "pull_request": {"number": 42}}
        self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get), {"action": "skip"})
        self.pr["labels"] = []
        self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get),
                         {"action": "cleanup", "pr_number": "42"})

    def test_unhandled_target_event_cannot_trigger_cleanup(self):
        self.pr["state"] = "closed"
        event = {"action": "opened", "pull_request": {"number": 42}}
        self.assertEqual(context.resolve("pull_request_target", event, "owner/blog", self.get), {"action": "skip"})

    def test_retargeted_pr_is_never_published_from_an_old_successful_build(self):
        self.pr["base"]["ref"] = "maintenance"
        self.assertEqual(self.resolve(), {"action": "skip"})

    def test_main_dispatch_rechecks_retargeted_closed_and_revoked_preview(self):
        original = copy.deepcopy(self.pr)
        for state in ("retargeted", "closed", "revoked"):
            self.pr = copy.deepcopy(original)
            if state == "retargeted": self.pr["base"]["ref"] = "maintenance"
            if state == "closed": self.pr["state"] = "closed"
            if state == "revoked": self.pr["labels"] = []
            for ref in ("main", "refs/heads/main"):
                with self.subTest(state=state, ref=ref):
                    event = {"ref": ref, "inputs": {"cleanup_pr": "42"}}
                    result = context.resolve("workflow_dispatch", event, "owner/blog", self.get,
                                             workflow_ref="refs/heads/main")
                    self.assertEqual(result, {"action": "cleanup", "pr_number": "42"})

    def test_dispatch_cannot_bypass_current_preview_authority_or_fork_limit(self):
        event = {"ref": "main", "inputs": {"cleanup_pr": "42"}}
        self.assertEqual(context.resolve("workflow_dispatch", event, "owner/blog", self.get,
                                         workflow_ref="refs/heads/main"), {"action": "skip"})
        self.pr["state"] = "closed"
        self.pr["head"]["repo"]["full_name"] = "stranger/blog"
        self.assertEqual(context.resolve("workflow_dispatch", event, "owner/blog", self.get,
                                         workflow_ref="refs/heads/main"), {"action": "skip"})

    def test_dispatch_requires_main_runtime_ref_and_positive_pr_input(self):
        def forbidden_get(path):
            self.fail("Invalid dispatch must not fetch a PR: " + path)
        for event_ref, runtime_ref, number in (
                ("feature", "refs/heads/main", "42"),
                ("main", "refs/heads/feature", "42"),
                ("main", None, "42"),
                ("main", "refs/heads/main", ""),
                ("main", "refs/heads/main", "0"),
                ("main", "refs/heads/main", "-1"),
                ("main", "refs/heads/main", "42/../1"),
                ("main", "refs/heads/main", 42)):
            with self.subTest(event_ref=event_ref, runtime_ref=runtime_ref, number=number):
                event = {"ref": event_ref, "inputs": {"cleanup_pr": number}}
                self.assertEqual(context.resolve("workflow_dispatch", event, "owner/blog", forbidden_get,
                                                 workflow_ref=runtime_ref), {"action": "skip"})

    def test_incomplete_api_response_cannot_authorize_cleanup(self):
        original = copy.deepcopy(self.pr)
        event = {"ref": "main", "inputs": {"cleanup_pr": "42"}}
        for field in ("state", "base", "labels"):
            with self.subTest(field=field):
                self.pr = copy.deepcopy(original)
                del self.pr[field]
                with self.assertRaisesRegex(ValueError, "Incomplete PR state"):
                    context.resolve("workflow_dispatch", event, "owner/blog", self.get,
                                    workflow_ref="refs/heads/main")


class ArtifactExtractionTests(unittest.TestCase):
    def test_valid_archive_and_rejection_of_traversal_links_and_control_files(self):
        cases = [("index.html", None, True), ("../escape", None, False),
                 (".github/workflows/pwn.yml", None, False), ("link", stat.S_IFLNK | 0o777, False)]
        for name, mode, valid in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                download = root / "download"
                download.mkdir()
                with zipfile.ZipFile(download / "artifact.zip", "w") as bundle:
                    info = zipfile.ZipInfo(name)
                    if mode: info.external_attr = mode << 16
                    bundle.writestr(info, "example")
                if valid:
                    context.unpack(download, root / "site")
                    self.assertEqual((root / "site/index.html").read_text(), "example")
                else:
                    with self.assertRaises(ValueError): context.unpack(download, root / "site")
                    self.assertFalse((root / "site").exists())


if __name__ == "__main__":
    unittest.main()
