"""Snapshot composition and hostile ZIP tests, entirely on local temporary files."""
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pages_snapshot as snapshots


class PagesSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.serial = 0
        self.empty = self.root / "empty"
        self.empty.mkdir()

    def path(self, prefix="output"):
        self.serial += 1
        return self.root / f"{prefix}-{self.serial}"

    def write_json(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def files(self, root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    def component(self, label, number=None, extras=None, base="https://example.invalid/"):
        site = self.path("component")
        site.mkdir()
        (site / "index.html").write_text(label)
        (site / ".nojekyll").write_text("")
        (site / "assets").mkdir()
        (site / "assets/app.css").write_text("body{}")
        for name, text in (extras or {}).items():
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        identity = {"schema_version": 1, "source_sha": hashlib.sha1(label.encode()).hexdigest(),
                    "run_id": label, "kind": "preview" if number is not None else "production",
                    "base_url": base + f"previews/pr-{number}/" if number is not None else base}
        self.write_json(site / "build-info.json", identity)
        self.restamp(site)
        return site, identity

    def restamp(self, site):
        hashes = {name: hashlib.sha256(body).hexdigest() for name, body in self.files(site).items()
                  if name != "site-manifest.json"}
        self.write_json(site / "site-manifest.json", {"schema_version": 1, "files": hashes})

    def production(self, label="production", extras=None):
        component, identity = self.component(label, extras=extras)
        destination = self.path("snapshot")
        snapshots.compose(self.empty, destination, kind="production", snapshot_id=label,
                          site=component, identity=identity)
        return destination

    def preview(self, previous, number, label):
        component, identity = self.component(label, number)
        destination = self.path("snapshot")
        snapshots.compose(previous, destination, kind="preview", snapshot_id=label,
                          site=component, identity=identity, pr_number=number)
        return destination

    def archive(self, site):
        archive, manifest = self.path("archive.zip"), self.path("manifest.json")
        value = snapshots.make_archive(site, archive, manifest)
        return archive, manifest, value

    def hostile_archive(self, site, extra_entries):
        archive, manifest, value = self.archive(site)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "a") as bundle:
                for name, body, mode in extra_entries:
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = mode << 16
                    bundle.writestr(entry, body)
        value["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.write_json(manifest, value)
        return archive, manifest

    def test_production_withdraws_old_pages_and_preserves_current_previews(self):
        old = self.production("old", {"withdrawn/index.html": "withdraw me"})
        previous = self.preview(old, 7, "preview-seven")
        component, identity = self.component("new")
        destination = self.path()
        result = snapshots.compose(previous, destination, kind="production", snapshot_id="release-new",
                                   site=component, identity=identity)
        self.assertEqual((destination / "index.html").read_text(), "new")
        self.assertFalse((destination / "withdrawn").exists())
        self.assertEqual(self.files(previous / "previews"), self.files(destination / "previews"))
        self.assertEqual(result["snapshot_id"], "release-new")
        self.assertEqual(result["production"], identity)
        self.assertEqual(set(result["previews"]), {"7"})
        self.assertTrue((previous / "withdrawn/index.html").exists())

    def test_preview_update_and_cleanup_only_change_the_selected_component(self):
        previous = self.preview(self.preview(self.production(), 7, "seven-old"), 8, "eight")
        updated = self.preview(previous, 7, "seven-new")
        self.assertEqual((updated / "index.html").read_bytes(), (previous / "index.html").read_bytes())
        self.assertEqual(self.files(updated / "previews/pr-8"), self.files(previous / "previews/pr-8"))
        self.assertEqual((updated / "previews/pr-7/index.html").read_text(), "seven-new")
        cleaned = self.path()
        result = snapshots.compose(updated, cleaned, kind="cleanup", snapshot_id="cleanup-seven", pr_number=7)
        self.assertFalse((cleaned / "previews/pr-7").exists())
        self.assertEqual(self.files(cleaned / "previews/pr-8"), self.files(previous / "previews/pr-8"))
        self.assertEqual(set(result["previews"]), {"8"})

    def test_cleanup_missing_preview_is_safe_and_has_a_new_generation(self):
        previous = self.production()
        destination = self.path()
        result = snapshots.compose(previous, destination, kind="cleanup", snapshot_id="cleanup-missing", pr_number=99)
        self.assertEqual(result["snapshot_id"], "cleanup-missing")
        self.assertEqual((previous / "build-info.json").read_bytes(), (destination / "build-info.json").read_bytes())

    def test_rollback_does_not_resurrect_historical_previews(self):
        history = self.preview(self.production("historical", {"old-page.html": "old"}), 1, "closed-preview")
        current = self.preview(self.production("current", {"new-page.html": "new"}), 2, "open-preview")
        destination = self.path()
        snapshots.compose(current, destination, kind="rollback", snapshot_id="rollback", site=history)
        self.assertEqual((destination / "index.html").read_text(), "historical")
        self.assertTrue((destination / "old-page.html").is_file())
        self.assertFalse((destination / "new-page.html").exists())
        self.assertFalse((destination / "previews/pr-1").exists())
        self.assertEqual(self.files(destination / "previews/pr-2"), self.files(current / "previews/pr-2"))
        self.assertEqual(snapshots.validate(history)["snapshot_id"], "closed-preview")

    def test_rollback_accepts_a_clean_component_but_rejects_invalid_snapshot_metadata(self):
        current = self.production("current")
        component, _ = self.component("historical")
        destination = self.path()
        snapshots.compose(current, destination, kind="rollback", snapshot_id="rollback", site=component)
        self.assertEqual((destination / "index.html").read_text(), "historical")
        self.write_json(destination / snapshots.GENERATION_FILE, {"snapshot_id": "invalid"})
        with self.assertRaisesRegex(snapshots.SnapshotError, "generation marker"):
            snapshots.compose(current, self.path(), kind="rollback", snapshot_id="reject", site=destination)

    def test_component_copy_projects_clean_production_or_preview(self):
        whole = self.preview(self.production(), 42, "preview")
        production, preview = self.path(), self.path()
        snapshots.component_copy(whole, production)
        snapshots.component_copy(whole, preview, 42)
        self.assertFalse((production / snapshots.GENERATION_FILE).exists())
        self.assertFalse((production / "previews").exists())
        self.assertEqual(self.files(preview), self.files(whole / "previews/pr-42"))
        self.assertEqual((production / "build-info.json").read_bytes(), (whole / "build-info.json").read_bytes())

    def test_incoming_identity_is_exact_and_failure_does_not_create_destination(self):
        previous = self.production()
        component, identity = self.component("next")
        for field, value in (("source_sha", "f" * 40), ("run_id", "wrong"), ("kind", "preview"),
                             ("base_url", "https://elsewhere.invalid/"), ("base_url", "https://example.invalid")):
            with self.subTest(field=field, value=value):
                destination = self.path()
                with self.assertRaisesRegex(snapshots.SnapshotError, "identity"):
                    snapshots.compose(previous, destination, kind="production", snapshot_id="next",
                                      site=component, identity={**identity, field: value})
                self.assertFalse(destination.exists())

    def test_build_cannot_supply_a_global_marker_or_previews_even_if_hashed(self):
        previous = self.production()
        for name in (snapshots.GENERATION_FILE, "previews/pr-7/index.html"):
            with self.subTest(name=name):
                component, identity = self.component("bad", extras={name: "reserved"})
                with self.assertRaisesRegex(snapshots.SnapshotError, "reserved"):
                    snapshots.compose(previous, self.path(), kind="production", snapshot_id="bad",
                                      site=component, identity=identity)

    def test_previous_and_incoming_component_tampering_is_rejected(self):
        previous = self.production()
        (previous / "index.html").write_text("tampered")
        component, identity = self.component("new")
        with self.assertRaisesRegex(snapshots.SnapshotError, "checksum"):
            snapshots.compose(previous, self.path(), kind="production", snapshot_id="new", site=component, identity=identity)
        previous = self.production("untouched")
        (component / "index.html").write_text("tampered")
        with self.assertRaisesRegex(snapshots.SnapshotError, "checksum"):
            snapshots.compose(previous, self.path(), kind="production", snapshot_id="new", site=component, identity=identity)

    def test_preview_cannot_change_the_site_origin(self):
        previous = self.production()
        component, identity = self.component("foreign", 7, base="https://other.invalid/")
        destination = self.path()
        with self.assertRaisesRegex(snapshots.SnapshotError, "base_url"):
            snapshots.compose(previous, destination, kind="preview", snapshot_id="foreign",
                              site=component, identity=identity, pr_number=7)
        self.assertFalse(destination.exists())

    def test_generation_marker_schema_and_reserved_aliases_are_rejected(self):
        for marker in ({"schema_version": True, "snapshot_id": "x"},
                       {"schema_version": 1, "snapshot_id": "../escape"},
                       {"schema_version": 1, "snapshot_id": "x", "active": "override"}):
            site = self.production()
            self.write_json(site / snapshots.GENERATION_FILE, marker)
            with self.assertRaises(snapshots.SnapshotError):
                snapshots.validate(site)
        site = self.production()
        (site / snapshots.GENERATION_FILE).rename(site / "Deployment-Info.json")
        with self.assertRaisesRegex(snapshots.SnapshotError, "canonical"):
            snapshots.validate(site, allow_legacy=True)

    def test_legacy_requires_explicit_opt_in_even_after_archiving(self):
        legacy = self.path()
        legacy.mkdir()
        (legacy / "index.html").write_text("old website")
        with self.assertRaises(snapshots.SnapshotError):
            snapshots.validate(legacy)
        self.assertIsNone(snapshots.validate(legacy, allow_legacy=True)["production"])
        destination = self.path()
        with self.assertRaises(snapshots.SnapshotError):
            snapshots.compose(self.empty, destination, kind="rollback", snapshot_id="legacy", site=legacy)
        snapshots.compose(self.empty, destination, kind="rollback", snapshot_id="legacy", site=legacy, allow_legacy=True)
        archive, manifest = self.path(), self.path()
        with self.assertRaises(snapshots.SnapshotError):
            snapshots.make_archive(destination, archive, manifest)
        snapshots.make_archive(destination, archive, manifest, allow_legacy=True)
        extracted = self.path()
        with self.assertRaises(snapshots.SnapshotError):
            snapshots.extract_archive(archive, manifest, extracted)
        state = snapshots.extract_archive(archive, manifest, extracted, allow_legacy=True)
        self.assertIsNone(state["production"])
        self.assertEqual(self.files(destination), self.files(extracted))

    def test_partial_metadata_and_unversioned_preview_are_never_legacy(self):
        site = self.production()
        (site / "build-info.json").unlink()
        with self.assertRaises(snapshots.SnapshotError):
            snapshots.validate(site, allow_legacy=True)
        site = self.production()
        preview = site / "previews/pr-1"
        preview.mkdir(parents=True)
        (preview / "index.html").write_text("unversioned")
        with self.assertRaises(snapshots.SnapshotError):
            snapshots.validate(site, allow_legacy=True)

    def test_preview_directory_names_must_be_canonical(self):
        for name in ("pr-0", "pr-01", "arbitrary"):
            site = self.preview(self.production(), 7, "preview")
            (site / "previews/pr-7").rename(site / "previews" / name)
            with self.assertRaisesRegex(snapshots.SnapshotError, "pr-N"):
                snapshots.validate(site)

    def test_archive_round_trip_preserves_all_bytes_and_component_identities(self):
        site = self.preview(self.production(), 7, "preview")
        archive, manifest, value = self.archive(site)
        destination = self.path()
        result = snapshots.extract_archive(archive, manifest, destination)
        self.assertEqual(result, snapshots.validate(site))
        self.assertEqual(self.files(site), self.files(destination))
        self.assertEqual(set(value["files"]), set(self.files(site)))
        self.assertEqual(value["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_archive_checksum_and_file_hash_are_both_enforced(self):
        archive, manifest, value = self.archive(self.production())
        archive.write_bytes(archive.read_bytes() + b"tamper")
        destination = self.path()
        with self.assertRaisesRegex(snapshots.SnapshotError, "Archive checksum"):
            snapshots.extract_archive(archive, manifest, destination)
        self.assertFalse(destination.exists())
        value["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        value["files"]["index.html"] = "0" * 64
        with self.assertRaisesRegex(snapshots.SnapshotError, "file checksum"):
            snapshots.extract_archive(archive, value, destination)
        self.assertFalse(destination.exists())

    def test_manifest_file_set_and_snapshot_identity_are_enforced(self):
        archive, _, value = self.archive(self.production())
        for update, message in (({"snapshot_id": "wrong"}, "identity"),
                                ({"files": {**value["files"], "extra.html": "0" * 64}}, "file set")):
            with self.subTest(update=update):
                with self.assertRaisesRegex(snapshots.SnapshotError, message):
                    snapshots.extract_archive(archive, {**value, **update}, self.path())

    def test_archive_rejects_traversal_absolute_backslash_git_and_symlink_entries(self):
        site = self.production()
        for name, mode in (("../escape", stat.S_IFREG), ("/escape", stat.S_IFREG),
                           ("a/../escape", stat.S_IFREG), ("a\\escape", stat.S_IFREG),
                           (".git/config", stat.S_IFREG), ("link", stat.S_IFLNK)):
            with self.subTest(name=name):
                archive, manifest = self.hostile_archive(site, [(name, b"malicious", mode | 0o644)])
                destination = self.path()
                with self.assertRaises(snapshots.SnapshotError):
                    snapshots.extract_archive(archive, manifest, destination)
                self.assertFalse(destination.exists())
        self.assertFalse((self.root / "escape").exists())

    def test_archive_rejects_duplicate_case_unicode_and_parent_file_conflicts(self):
        site = self.production()
        for entries in (("index.html",), ("Index.html",), ("A/one", "a/two"),
                        ("caf\u00e9", "cafe\u0301"), ("assets",)):
            with self.subTest(entries=entries):
                archive, manifest = self.hostile_archive(site, [(name, b"bad", stat.S_IFREG | 0o644) for name in entries])
                with self.assertRaises(snapshots.SnapshotError):
                    snapshots.extract_archive(archive, manifest, self.path())

    def test_archive_expansion_and_entry_count_are_bounded(self):
        archive, manifest, _ = self.archive(self.production())
        with patch.object(snapshots, "MAX_BYTES", 10):
            with self.assertRaisesRegex(snapshots.SnapshotError, "size limit"):
                snapshots.extract_archive(archive, manifest, self.path())
        with patch.object(snapshots, "MAX_FILES", 1):
            with self.assertRaises(snapshots.SnapshotError):
                snapshots.extract_archive(archive, manifest, self.path())

    def test_small_compressed_archive_cannot_exceed_the_expanded_size_budget(self):
        archive, manifest, _ = self.archive(self.production("compressible", {"large.txt": "x" * 200_000}))
        self.assertLess(archive.stat().st_size, 50_000)
        destination = self.path()
        with patch.object(snapshots, "MAX_BYTES", 50_000):
            with self.assertRaisesRegex(snapshots.SnapshotError, "size limit"):
                snapshots.extract_archive(archive, manifest, destination)
        self.assertFalse(destination.exists())

    def test_directory_entries_count_toward_archive_limit(self):
        site = self.production()
        archive, manifest = self.hostile_archive(site, [(f"empty-{number}/", b"", stat.S_IFDIR | 0o755)
                                                       for number in range(10)])
        with patch.object(snapshots, "MAX_FILES", len(self.files(site)) + 1):
            with self.assertRaisesRegex(snapshots.SnapshotError, "file count"):
                snapshots.extract_archive(archive, manifest, self.path())

    def test_symlinks_existing_destinations_and_overlap_cannot_be_published(self):
        site = self.production()
        (site / "link").symlink_to(site / "index.html")
        with self.assertRaisesRegex(snapshots.SnapshotError, "symlinks"):
            snapshots.validate(site)
        (site / "link").unlink()
        component, identity = self.component("new")
        with self.assertRaisesRegex(snapshots.SnapshotError, "overlap"):
            snapshots.compose(site, site / "nested", kind="production", snapshot_id="new", site=component, identity=identity)
        destination = self.path()
        destination.mkdir()
        (destination / "keep").write_text("keep")
        with self.assertRaisesRegex(snapshots.SnapshotError, "must not exist"):
            snapshots.component_copy(site, destination)
        self.assertEqual((destination / "keep").read_text(), "keep")

    def test_duplicate_metadata_keys_and_unsafe_manifest_paths_are_rejected(self):
        archive, manifest, value = self.archive(self.production())
        manifest.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(snapshots.SnapshotError, "Duplicate"):
            snapshots.extract_archive(archive, manifest, self.path())
        for name in ("../escape", "A/one", "a/two"):
            bad = {**value, "files": {**value["files"], name: "0" * 64}}
            if name != "../escape":
                bad["files"].update({"A/one": "0" * 64, "a/two": "0" * 64})
            with self.assertRaises(snapshots.SnapshotError):
                snapshots.extract_archive(archive, bad, self.path())


if __name__ == "__main__":
    unittest.main()
