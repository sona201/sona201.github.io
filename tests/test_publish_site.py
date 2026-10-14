"""Exercise publication against temporary local bare remotes, never GitHub."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_site as publisher


def git(repo, *arguments):
    command = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
               "-c", "commit.gpgsign=false", "-C", str(repo), *arguments]
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


class PublishSiteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.remote = self.root / "remote.git"
        self.repo = self.root / "pages"
        git(self.root, "init", "--bare", "--initial-branch=master", str(self.remote))
        git(self.root, "clone", str(self.remote), str(self.repo))
        (self.repo / "index.html").write_text("old production")
        (self.repo / "withdrawn.html").write_text("must disappear on next publish")
        preview = self.repo / "previews" / "pr-1"
        preview.mkdir(parents=True)
        (preview / "index.html").write_text("existing preview")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "seed")
        git(self.repo, "push", "origin", "master")
        self.seed = git(self.repo, "rev-parse", "HEAD")
        self.source_sha = "a" * 40

    def artifact(self, kind="production", number=None):
        site = self.root / f"site-{kind}-{number}"
        site.mkdir()
        base = "https://example.invalid/" if kind == "production" else f"https://example.invalid/previews/pr-{number}/"
        info = {"schema_version": 1, "source_sha": self.source_sha, "run_id": "123",
                "kind": kind, "base_url": base}
        (site / "index.html").write_text("new " + kind)
        (site / ".nojekyll").write_text("")
        (site / "assets").mkdir()
        (site / "assets" / "app.css").write_text("body{}")
        (site / "build-info.json").write_text(json.dumps(info))
        self.manifest(site)
        return SimpleNamespace(site=site, repo_dir=self.repo, kind=kind, pr_number=number,
                               source_sha=self.source_sha, run_id="123", base_url=base)

    def manifest(self, site):
        files = {path.relative_to(site).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in site.rglob("*") if path.is_file() and path.name != "site-manifest.json"}
        (site / "site-manifest.json").write_text(json.dumps({"schema_version": 1, "files": files}))

    def assert_remote(self, commit):
        self.assertEqual(git(self.remote, "rev-parse", "master"), commit)

    def test_production_removes_withdrawn_pages_and_preserves_previews(self):
        result = publisher.deploy(self.artifact())
        self.assertEqual((self.repo / "index.html").read_text(), "new production")
        self.assertFalse((self.repo / "withdrawn.html").exists())
        self.assertEqual((self.repo / "previews/pr-1/index.html").read_text(), "existing preview")
        self.assertEqual(result["previous_commit"], self.seed)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD^"), self.seed)
        self.assert_remote(result["published_commit"])

    def test_preview_only_changes_its_pr_directory_and_cleanup_really_deletes(self):
        args = self.artifact("preview", 7)
        result = publisher.deploy(args)
        self.assertEqual((self.repo / "index.html").read_text(), "old production")
        self.assertTrue((self.repo / "withdrawn.html").exists())
        self.assertEqual((self.repo / "previews/pr-7/index.html").read_text(), "new preview")
        self.assertTrue((self.repo / "previews/pr-1/index.html").exists())
        cleaned = publisher.cleanup(SimpleNamespace(repo_dir=self.repo, pr_number=7))
        self.assertFalse((self.repo / "previews/pr-7").exists())
        self.assertTrue((self.repo / "previews/pr-1/index.html").exists())
        self.assertEqual(cleaned["previous_commit"], result["published_commit"])
        self.assert_remote(cleaned["published_commit"])

    def test_artifact_identity_must_match(self):
        args = self.artifact()
        args.source_sha = "b" * 40
        with self.assertRaisesRegex(publisher.PublishError, "identity"):
            publisher.deploy(args)
        self.assert_remote(self.seed)
        self.assertEqual((self.repo / "index.html").read_text(), "old production")

    def test_build_info_cannot_override_publish_control_fields(self):
        args = self.artifact()
        marker = args.site / "build-info.json"
        original = json.loads(marker.read_text())
        for key, value in (("ok", False), ("action", "rollback"), ("previous_commit", "b" * 40)):
            with self.subTest(key=key):
                marker.write_text(json.dumps({**original, key: value}))
                self.manifest(args.site)
                with self.assertRaisesRegex(publisher.PublishError, "five supported identity fields"):
                    publisher.deploy(args)
                self.assert_remote(self.seed)
                self.assertEqual(git(self.repo, "status", "--porcelain"), "")
                self.assertEqual((self.repo / "index.html").read_text(), "old production")

    def test_boolean_schema_version_is_not_an_integer_version(self):
        args = self.artifact()
        marker = args.site / "build-info.json"
        info = json.loads(marker.read_text())
        info["schema_version"] = True
        marker.write_text(json.dumps(info))
        self.manifest(args.site)
        with self.assertRaisesRegex(publisher.PublishError, "five supported identity fields"):
            publisher.deploy(args)
        self.assert_remote(self.seed)

    def test_preview_url_must_match_pr(self):
        args = self.artifact("preview", 7)
        args.pr_number = 8
        args.base_url = None
        with self.assertRaisesRegex(publisher.PublishError, "PR number"):
            publisher.deploy(args)
        self.assert_remote(self.seed)

    def test_manifest_rejects_tampering_extra_files_and_traversal(self):
        args = self.artifact()
        original = (args.site / "index.html").read_text()
        (args.site / "index.html").write_text("tampered")
        with self.assertRaisesRegex(publisher.PublishError, "checksum mismatch"):
            publisher.deploy(args)
        (args.site / "index.html").write_text(original)
        (args.site / "extra.txt").write_text("unlisted")
        with self.assertRaisesRegex(publisher.PublishError, "every artifact file"):
            publisher.deploy(args)
        (args.site / "extra.txt").unlink()
        (args.site / "site-manifest.json").write_text(json.dumps({
            "schema_version": 1, "files": {"../escape.txt": "0" * 64},
        }))
        with self.assertRaisesRegex(publisher.PublishError, "traversal"):
            publisher.deploy(args)
        self.assert_remote(self.seed)

    def test_artifact_symlinks_and_git_workflows_are_rejected(self):
        args = self.artifact()
        link = args.site / "escape"
        link.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(publisher.PublishError, "Symlinks"):
            publisher.deploy(args)
        link.unlink()
        (args.site / ".github").mkdir()
        with self.assertRaisesRegex(publisher.PublishError, "workflow paths"):
            publisher.deploy(args)
        self.assert_remote(self.seed)

    def test_symlink_git_directory_is_rejected(self):
        unsafe = self.root / "unsafe"
        unsafe.mkdir()
        (unsafe / ".git").symlink_to(self.repo / ".git", target_is_directory=True)
        args = self.artifact()
        args.repo_dir = unsafe
        with self.assertRaisesRegex(publisher.PublishError, "independent clone"):
            publisher.deploy(args)

    def test_rollback_adds_new_commit_and_preserves_current_previews(self):
        publisher.deploy(self.artifact())
        preview = publisher.deploy(self.artifact("preview", 9))
        result = publisher.rollback(SimpleNamespace(repo_dir=self.repo, commit=self.seed,
                                                    expected_head=preview["published_commit"]))
        self.assertEqual((self.repo / "index.html").read_text(), "old production")
        self.assertTrue((self.repo / "withdrawn.html").exists())
        self.assertFalse((self.repo / "assets").exists())
        self.assertEqual((self.repo / "previews/pr-9/index.html").read_text(), "new preview")
        self.assertNotEqual(result["published_commit"], self.seed)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD^"), preview["published_commit"])
        self.assert_remote(result["published_commit"])

    def test_rollback_rejects_stale_expected_head_and_nonancestor(self):
        current = publisher.deploy(self.artifact())["published_commit"]
        with self.assertRaisesRegex(publisher.PublishError, "expected-head"):
            publisher.rollback(SimpleNamespace(repo_dir=self.repo, commit=self.seed, expected_head=self.seed))
        orphan = git(self.repo, "commit-tree", git(self.repo, "rev-parse", "HEAD^{tree}"), "-m", "unrelated")
        with self.assertRaisesRegex(publisher.PublishError, "history"):
            publisher.rollback(SimpleNamespace(repo_dir=self.repo, commit=orphan, expected_head=current))
        self.assert_remote(current)

    def test_rollback_validates_modern_artifact_and_restores_it(self):
        args = self.artifact()
        first = publisher.deploy(args)["published_commit"]
        (args.site / "index.html").write_text("second production")
        self.manifest(args.site)
        second = publisher.deploy(args)["published_commit"]
        result = publisher.rollback(SimpleNamespace(repo_dir=self.repo, commit=first,
                                                    expected_head=second, base_url=args.base_url))
        self.assertEqual((self.repo / "index.html").read_text(), "new production")
        self.assertEqual(result["source_sha"], self.source_sha)
        self.assert_remote(result["published_commit"])

    def test_rollback_refuses_marker_without_manifest(self):
        args = self.artifact()
        publisher.deploy(args)
        (self.repo / "site-manifest.json").unlink()
        git(self.repo, "add", "--all")
        git(self.repo, "commit", "-m", "historical incomplete artifact")
        git(self.repo, "push", "origin", "master")
        target = git(self.repo, "rev-parse", "HEAD")
        with self.assertRaisesRegex(publisher.PublishError, "site-manifest.json"):
            publisher.rollback(SimpleNamespace(repo_dir=self.repo, commit=target,
                                               expected_head=target, base_url=args.base_url))
        self.assert_remote(target)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_rollback_rejects_bad_hash_preview_identity_and_wrong_base_url(self):
        args = self.artifact()
        publisher.deploy(args)
        marker = self.repo / "build-info.json"
        original = json.loads(marker.read_text())
        for failure in ("checksum", "preview", "base_url"):
            with self.subTest(failure=failure):
                info = dict(original)
                (self.repo / "index.html").write_text("new production")
                if failure == "preview":
                    info["kind"] = "preview"
                elif failure == "base_url":
                    info["base_url"] = "https://unrelated.invalid/"
                marker.write_text(json.dumps(info))
                self.manifest(self.repo)
                # The target snapshot excludes previews from the production manifest.
                manifest = json.loads((self.repo / "site-manifest.json").read_text())
                manifest["files"] = {name: digest for name, digest in manifest["files"].items()
                                     if not name.startswith(("previews/", ".git/"))}
                (self.repo / "site-manifest.json").write_text(json.dumps(manifest))
                if failure == "checksum":
                    (self.repo / "index.html").write_text("corrupted after stamping")
                git(self.repo, "add", "--all")
                git(self.repo, "commit", "-m", "historical invalid " + failure)
                git(self.repo, "push", "origin", "master")
                target = git(self.repo, "rev-parse", "HEAD")
                expected = "checksum mismatch" if failure == "checksum" else "identity" if failure == "preview" else "deployment URL"
                with self.assertRaisesRegex(publisher.PublishError, expected):
                    publisher.rollback(SimpleNamespace(repo_dir=self.repo, commit=target,
                                                       expected_head=target, base_url=args.base_url))
                self.assert_remote(target)
                self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_remote_change_before_push_is_rejected_without_force(self):
        other = self.root / "other"
        git(self.root, "clone", str(self.remote), str(other))
        original = publisher.require_remote_head
        calls = 0

        def concurrent_publish(repo, expected):
            nonlocal calls
            calls += 1
            if calls == 2:
                (other / "index.html").write_text("concurrent publication")
                git(other, "add", ".")
                git(other, "commit", "-m", "someone else published")
                git(other, "push", "origin", "master")
            return original(repo, expected)

        with patch.object(publisher, "require_remote_head", side_effect=concurrent_publish):
            with self.assertRaisesRegex(publisher.PublishError, "Remote master changed"):
                publisher.deploy(self.artifact())
        self.assert_remote(git(other, "rev-parse", "HEAD"))
        self.assertNotEqual(git(self.repo, "rev-parse", "HEAD"), git(other, "rev-parse", "HEAD"))

    def test_cli_writes_machine_readable_output(self):
        args = self.artifact()
        output = self.root / "result.json"
        result = subprocess.run([
            sys.executable, str(Path(publisher.__file__)), "deploy", "--site", str(args.site),
            "--repo-dir", str(self.repo), "--kind", "production", "--source-sha", self.source_sha,
            "--run-id", "123", "--base-url", args.base_url, "--output", str(output),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(output.read_text()))
        self.assert_remote(json.loads(output.read_text())["published_commit"])

    def test_cli_refuses_output_inside_git_before_deploying(self):
        args = self.artifact()
        result = subprocess.run([
            sys.executable, str(Path(publisher.__file__)), "deploy", "--site", str(args.site),
            "--repo-dir", str(self.repo), "--kind", "production", "--source-sha", self.source_sha,
            "--run-id", "123", "--output", str(self.repo / ".git/config"),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside", json.loads(result.stdout)["error"])
        self.assert_remote(self.seed)


if __name__ == "__main__":
    unittest.main()
