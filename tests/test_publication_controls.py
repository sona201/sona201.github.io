import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import check_public_manifest
import recover_site


class PublicManifestTests(unittest.TestCase):
    def test_unmapped_duplicate_and_missing_articles_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "migration").mkdir()
            (root / "content/post").mkdir(parents=True)
            (root / "content/post/a.md").write_text("Public")
            entry = {"source": "博客/a.md", "target": "content/post/a.md"}
            manifest = root / "migration/published-manifest.json"
            for entries, valid in (([entry], True), ([], False), ([entry, entry], False),
                                   ([{"source": "博客/b.md", "target": "content/post/b.md"}], False)):
                manifest.write_text(json.dumps({"version": 1, "entries": entries}))
                if valid: check_public_manifest.check_manifest(root)
                else:
                    with self.assertRaises(ValueError): check_public_manifest.check_manifest(root)


class RecoveryTests(unittest.TestCase):
    def test_recovery_binds_expected_head_and_records_verification_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"ok": True, "action": "deploy", "kind": "production",
                      "previous_commit": "a" * 40, "published_commit": "b" * 40}
            restore = Mock(return_value={"ok": True, "published_commit": "c" * 40})
            verify = Mock(side_effect=ValueError("still unavailable"))
            output = root / "recovery.json"
            with self.assertRaises(ValueError):
                recover_site.recover(root, record, output, restore=restore, verify=verify)
            self.assertEqual(restore.call_args.args[0].expected_head, "b" * 40)
            self.assertEqual(restore.call_args.args[0].commit, "a" * 40)
            self.assertEqual(json.loads(output.read_text())["verification"], "failure")

    def test_preview_cannot_request_production_recovery(self):
        with self.assertRaises(ValueError):
            recover_site.recover(Path("."), {"ok": True, "action": "deploy", "kind": "preview"}, Path("unused"))

    def test_legacy_rollback_requires_exact_homepage_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_bytes(b"expected")
            with self.assertRaises(ValueError):
                recover_site.verify_legacy(site, attempts=1, fetch=lambda: b"wrong but HTTP 200")
            result = recover_site.verify_legacy(site, attempts=1, fetch=lambda: b"expected")
            self.assertEqual(result["verification"], "success")


if __name__ == "__main__":
    unittest.main()
