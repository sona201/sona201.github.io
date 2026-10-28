#!/usr/bin/env python3
"""Compose and archive complete Pages sites without changing Git or remote state.

The root production component and each ``previews/pr-N`` component retain their
own build metadata. ``deployment-info.json`` identifies the complete snapshot.
All destinations must be absent; failed validation never replaces a destination.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from types import SimpleNamespace
import unicodedata
import zipfile

import publish_site


GENERATION_FILE = "deployment-info.json"
SCHEMA_VERSION = 1
MAX_FILES = 50_000
MAX_BYTES = 1024 * 1024 * 1024
MAX_METADATA_BYTES = 16 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
SNAPSHOT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PREVIEW = re.compile(r"pr-([1-9][0-9]*)\Z")
IDENTITY_KEYS = {"source_sha", "run_id", "kind", "base_url"}


class SnapshotError(ValueError):
    """Invalid snapshot, component, or archive."""


def _snapshot_id(value):
    if not isinstance(value, str) or not SNAPSHOT_ID.fullmatch(value):
        raise SnapshotError("Invalid snapshot_id")
    return value


def _pr_number(value):
    if type(value) is not int or value < 1:
        raise SnapshotError("A positive integer PR number is required")
    return value


def _path(name):
    if not isinstance(name, str) or len(name) > 4096 or "\x7f" in name:
        raise SnapshotError("Invalid snapshot path")
    try:
        path = publish_site.relative_path(name, allow_previews=True)
    except publish_site.PublishError as exc:
        raise SnapshotError(str(exc)) from exc
    first = unicodedata.normalize("NFC", path.parts[0]).casefold()
    if first == "previews" and path.parts[0] != "previews":
        raise SnapshotError("The previews directory must use its canonical name")
    if first == GENERATION_FILE and path.parts[0] != GENERATION_FILE:
        raise SnapshotError("The generation marker must use its canonical name")
    return path


class _Paths:
    """Detect aliases and file/directory conflicts, including implicit parents."""

    def __init__(self):
        self.paths = {}
        self.explicit = set()

    def add(self, name, is_directory=False):
        parts = _path(name).parts
        if name in self.explicit:
            raise SnapshotError("Duplicate archive or manifest path")
        self.explicit.add(name)
        for length in range(1, len(parts) + 1):
            prefix = "/".join(parts[:length])
            directory = length < len(parts) or is_directory
            key = unicodedata.normalize("NFC", prefix).casefold()
            previous = self.paths.get(key)
            if previous is not None and previous != (prefix, directory):
                raise SnapshotError("Case/Unicode aliases or file/directory conflicts are forbidden")
            self.paths[key] = (prefix, directory)


def _inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise SnapshotError("Snapshot root must be a real directory")
    files, paths, total, count = {}, _Paths(), 0, 0
    for current, directories, names in os.walk(root, followlinks=False):
        for name in sorted(directories + names):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            metadata = path.lstat()
            is_directory = stat.S_ISDIR(metadata.st_mode)
            if not is_directory and not stat.S_ISREG(metadata.st_mode):
                raise SnapshotError("Only regular files and directories are allowed; symlinks are forbidden")
            if relative == GENERATION_FILE and is_directory:
                raise SnapshotError("The generation marker must be a regular file")
            paths.add(relative, is_directory)
            count += 1
            if not is_directory:
                files[relative] = path
                total += metadata.st_size
            if count > MAX_FILES or total > MAX_BYTES:
                raise SnapshotError("Snapshot exceeds file count or size limit")
    return dict(sorted(files.items()))


def _json_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_METADATA_BYTES:
        raise SnapshotError("Invalid or oversized metadata file")
    try:
        return publish_site.load_json(path)
    except publish_site.PublishError as exc:
        raise SnapshotError(str(exc)) from exc


def _write_json(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as output:
        try:
            json.dump(value, output, sort_keys=True, ensure_ascii=False, indent=2)
            output.write("\n")
        except Exception:
            path.unlink(missing_ok=True)
            raise


def _digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while block := source.read(CHUNK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def _destination(destination, *sources):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise SnapshotError("Destination must not exist")
    resolved = destination.resolve()
    for source in sources:
        source = Path(source).resolve()
        if resolved == source or resolved in source.parents or source in resolved.parents:
            raise SnapshotError("Source and destination must not overlap")
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _copy_files(files, destination):
    for name, source in files.items():
        target = destination / _path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _component_files(root, files, pr_number=None):
    if pr_number is None:
        return {name: path for name, path in files.items()
                if name != GENERATION_FILE and name.split("/", 1)[0] != "previews"}
    prefix = f"previews/pr-{_pr_number(pr_number)}/"
    result = {name[len(prefix):]: path for name, path in files.items() if name.startswith(prefix)}
    if not result:
        raise SnapshotError(f"Missing preview component: pr-{pr_number}")
    return result


def component_copy(root, dest, pr_number=None):
    """Project one component without the global marker or unrelated previews."""
    root = Path(root)
    files = _component_files(root, _inventory(root), pr_number)
    destination = _destination(dest, root)
    with tempfile.TemporaryDirectory(prefix=".pages-component-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "component"
        stage.mkdir()
        _copy_files(files, stage)
        stage.rename(destination)
    return destination


def _identity(value, kind):
    if not isinstance(value, dict) or set(value) not in (IDENTITY_KEYS, IDENTITY_KEYS | {"schema_version"}):
        raise SnapshotError("Identity must contain source_sha, run_id, kind and base_url")
    if "schema_version" in value and (type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION):
        raise SnapshotError("Invalid identity schema_version")
    if (value["kind"] != kind or not isinstance(value["source_sha"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", value["source_sha"])
            or not isinstance(value["run_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value["run_id"])
            or not isinstance(value["base_url"], str)):
        raise SnapshotError("Invalid component identity")
    return {**value, "schema_version": SCHEMA_VERSION}


def _verify_component(files, *, kind, pr_number=None, identity=None, allow_legacy=False):
    if GENERATION_FILE in files:
        raise SnapshotError("A component cannot overwrite the reserved generation marker")
    if "index.html" not in files or files["index.html"].stat().st_size == 0:
        raise SnapshotError("Component requires a nonempty index.html")
    has_info = "build-info.json" in files
    has_manifest = "site-manifest.json" in files
    if not has_info or not has_manifest:
        if allow_legacy and kind == "production" and not has_info and not has_manifest and identity is None:
            return None
        raise SnapshotError("Component requires both build-info.json and site-manifest.json")
    info = _identity(_json_file(files["build-info.json"]), kind)
    _json_file(files["site-manifest.json"])
    expected = _identity(identity, kind) if identity is not None else info
    if info != expected:
        raise SnapshotError("Component identity does not match the requested deployment")
    with tempfile.TemporaryDirectory(prefix="pages-component-check-") as temporary:
        component = Path(temporary)
        _copy_files(files, component)
        args = SimpleNamespace(**expected, pr_number=pr_number)
        try:
            verified, _ = publish_site.verify_artifact(component, args)
        except publish_site.PublishError as exc:
            raise SnapshotError(str(exc)) from exc
    return verified


def validate(root, allow_legacy=False):
    """Validate all components and the generation marker; return their identities.

    Only an explicit ``allow_legacy`` permits an old root without a generation
    marker, or production without both build metadata files. Previews are always
    required to have modern build metadata.
    """
    root = Path(root)
    files = _inventory(root)
    marker = {"schema_version": SCHEMA_VERSION, "snapshot_id": None}
    if GENERATION_FILE in files:
        marker = _json_file(files[GENERATION_FILE])
        if (set(marker) != {"schema_version", "snapshot_id"}
                or type(marker["schema_version"]) is not int or marker["schema_version"] != SCHEMA_VERSION):
            raise SnapshotError("Invalid generation marker schema")
        _snapshot_id(marker["snapshot_id"])
    elif not allow_legacy:
        raise SnapshotError("Missing generation marker")
    production = _verify_component(_component_files(root, files), kind="production", allow_legacy=allow_legacy)
    previews = {}
    preview_root = root / "previews"
    if preview_root.exists():
        if not preview_root.is_dir():
            raise SnapshotError("previews must be a directory")
        for preview in sorted(preview_root.iterdir()):
            match = PREVIEW.fullmatch(preview.name)
            if not match or not preview.is_dir():
                raise SnapshotError("Only previews/pr-N component directories are allowed")
            number = int(match.group(1))
            previews[str(number)] = _verify_component(
                _component_files(root, files, number), kind="preview", pr_number=number)
    base = production["base_url"] if production else None
    for number, info in previews.items():
        suffix = f"previews/pr-{number}/"
        if base is None:
            base = info["base_url"][:-len(suffix)]
        if info["base_url"] != base + suffix:
            raise SnapshotError("Preview base_url does not match the production site")
    return {**marker, "production": production, "previews": previews}


def compose(previous, destination, *, kind, snapshot_id, site=None, identity=None,
            pr_number=None, allow_legacy=False):
    """Create a new complete snapshot; rollback preserves current previews.

    An empty previous directory is permitted only when installing production or
    restoring production. Production and preview builds require exact expected
    identities. A rollback may read either a production directory or a complete
    historical snapshot; only its production files are copied.
    """
    _snapshot_id(snapshot_id)
    if kind not in {"production", "preview", "cleanup", "rollback"}:
        raise SnapshotError("Unsupported snapshot operation")
    if kind in {"preview", "cleanup"}:
        _pr_number(pr_number)
    elif pr_number is not None:
        raise SnapshotError("Production and rollback do not accept a PR number")
    if kind == "cleanup":
        if site is not None or identity is not None:
            raise SnapshotError("Cleanup does not accept a site or identity")
    elif site is None:
        raise SnapshotError("This operation requires a site")
    previous = Path(previous)
    previous_files = _inventory(previous)
    if any(previous.iterdir()):
        validate(previous, allow_legacy=allow_legacy)
    elif kind not in {"production", "rollback"}:
        raise SnapshotError("Preview and cleanup require an existing production site")
    incoming = None
    if site is not None:
        site = Path(site)
        source_files = _inventory(site)
        if kind == "rollback":
            if GENERATION_FILE in source_files or (site / "previews").exists():
                validate(site, allow_legacy=allow_legacy)
            incoming = _component_files(site, source_files)
            _verify_component(incoming, kind="production", identity=identity, allow_legacy=allow_legacy)
        else:
            if GENERATION_FILE in source_files or (site / GENERATION_FILE).exists():
                raise SnapshotError("A build cannot overwrite the reserved generation marker")
            if (site / "previews").exists():
                raise SnapshotError("A build cannot supply the reserved previews directory")
            incoming = source_files
            expected = _identity(identity, kind)
            _verify_component(incoming, kind=kind, pr_number=pr_number, identity=expected)
    destination = _destination(destination, previous, *([site] if site is not None else []))
    with tempfile.TemporaryDirectory(prefix=".pages-compose-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "site"
        stage.mkdir()
        retained = {name: path for name, path in previous_files.items() if name != GENERATION_FILE}
        if kind in {"production", "rollback"}:
            retained = {name: path for name, path in retained.items() if name.startswith("previews/")}
            _copy_files(retained, stage)
            _copy_files(incoming, stage)
        else:
            prefix = f"previews/pr-{pr_number}/"
            retained = {name: path for name, path in retained.items() if not name.startswith(prefix)}
            _copy_files(retained, stage)
            if kind == "preview":
                preview = stage / "previews" / f"pr-{pr_number}"
                preview.mkdir(parents=True)
                _copy_files(incoming, preview)
        _write_json(stage / GENERATION_FILE, {"schema_version": SCHEMA_VERSION, "snapshot_id": snapshot_id})
        result = validate(stage, allow_legacy=allow_legacy)
        stage.rename(destination)
    return result


def _manifest(value):
    value = _json_file(value) if not isinstance(value, dict) else value
    if (set(value) != {"schema_version", "snapshot_id", "archive_sha256", "files"}
            or type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION
            or not isinstance(value["files"], dict) or not value["files"]
            or len(value["files"]) > MAX_FILES):
        raise SnapshotError("Invalid snapshot manifest schema")
    _snapshot_id(value["snapshot_id"])
    if not isinstance(value["archive_sha256"], str) or not SHA256.fullmatch(value["archive_sha256"]):
        raise SnapshotError("Invalid archive checksum")
    paths = _Paths()
    for name, digest in value["files"].items():
        paths.add(name)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise SnapshotError("Invalid file checksum")
    if GENERATION_FILE not in value["files"]:
        raise SnapshotError("Snapshot manifest must include the generation marker")
    return value


def make_archive(site, archive, manifest, *, allow_legacy=False):
    """Write a ZIP and a JSON manifest of its bytes and every included file."""
    site = Path(site)
    state = validate(site, allow_legacy=allow_legacy)
    _snapshot_id(state["snapshot_id"])
    archive = _destination(archive, site)
    manifest = _destination(manifest, site)
    if archive.resolve() == manifest.resolve():
        raise SnapshotError("Archive and manifest paths must differ")
    files = _inventory(site)
    hashes = {name: _digest(path) for name, path in files.items()}
    created = []
    try:
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            created.append(archive)
            for name, source in files.items():
                bundle.write(source, name)
        if archive.stat().st_size > MAX_BYTES:
            raise SnapshotError("Archive exceeds size limit")
        if hashes != {name: _digest(path) for name, path in _inventory(site).items()}:
            raise SnapshotError("Snapshot changed while creating its archive")
        result = {"schema_version": SCHEMA_VERSION, "snapshot_id": state["snapshot_id"],
                  "archive_sha256": _digest(archive), "files": hashes}
        _manifest(result)
        _write_json(manifest, result)
        created.append(manifest)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return result


def extract_archive(archive, manifest, dest, *, allow_legacy=False):
    """Verify and safely extract a bounded ZIP into a new destination."""
    archive = Path(archive)
    expected = _manifest(manifest)
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > MAX_BYTES:
        raise SnapshotError("Invalid archive or archive exceeds size limit")
    if _digest(archive) != expected["archive_sha256"]:
        raise SnapshotError("Archive checksum mismatch")
    destination = _destination(dest, archive)
    try:
        with zipfile.ZipFile(archive) as bundle:
            entries = bundle.infolist()
            if len(entries) > MAX_FILES or sum(entry.file_size for entry in entries) > MAX_BYTES:
                raise SnapshotError("Archive exceeds file count or size limit")
            paths, archived_files = _Paths(), set()
            for entry in entries:
                if entry.orig_filename != entry.filename:
                    raise SnapshotError("Archive entry contains a truncated or invalid path")
                name = entry.filename[:-1] if entry.is_dir() else entry.filename
                paths.add(name, entry.is_dir())
                mode = stat.S_IFMT(entry.external_attr >> 16)
                expected_modes = {0, stat.S_IFDIR} if entry.is_dir() else {0, stat.S_IFREG}
                if mode not in expected_modes or entry.flag_bits & 1:
                    raise SnapshotError("Archive links, special files and encrypted entries are forbidden")
                if not entry.is_dir():
                    archived_files.add(name)
            if archived_files != set(expected["files"]):
                raise SnapshotError("Archive file set does not match the manifest")
            with tempfile.TemporaryDirectory(prefix=".pages-extract-", dir=destination.parent) as temporary:
                stage = Path(temporary) / "site"
                stage.mkdir()
                total = 0
                for entry in entries:
                    target = stage / _path(entry.filename[:-1] if entry.is_dir() else entry.filename)
                    if entry.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    digest, size = hashlib.sha256(), 0
                    with bundle.open(entry) as source, target.open("xb") as output:
                        while block := source.read(CHUNK_SIZE):
                            size += len(block)
                            total += len(block)
                            if size > entry.file_size or total > MAX_BYTES:
                                raise SnapshotError("Archive expanded beyond its declared size or limit")
                            digest.update(block)
                            output.write(block)
                    if size != entry.file_size or digest.hexdigest() != expected["files"][entry.filename]:
                        raise SnapshotError("Extracted file checksum or size mismatch")
                state = validate(stage, allow_legacy=allow_legacy)
                if state["snapshot_id"] != expected["snapshot_id"]:
                    raise SnapshotError("Snapshot identity does not match its manifest")
                stage.rename(destination)
        return state
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise SnapshotError("Invalid or unsupported ZIP archive") from exc
