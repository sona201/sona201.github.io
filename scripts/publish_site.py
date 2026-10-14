#!/usr/bin/env python3
"""Publish verified static files to an already-cloned Pages repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit


class PublishError(ValueError):
    pass


RESERVED = {".git", ".github", ".gitmodules", ".gitattributes"}


def full_sha(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", value):
        raise PublishError("A full 40-character commit SHA is required")
    return value.lower()


def relative_path(value: str, *, allow_previews: bool = False) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or any(ord(c) < 32 for c in value):
        raise PublishError("Invalid artifact path")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or any(p in {"", ".", ".."} for p in parts):
        raise PublishError("Absolute paths and traversal are forbidden")
    if any(p.casefold() in RESERVED for p in parts):
        raise PublishError("Git configuration and workflow paths are forbidden")
    if not allow_previews and parts[0].casefold() == "previews":
        raise PublishError("The previews directory is reserved")
    return Path(*parts)


def directory(value: Path) -> Path:
    if value.is_symlink() or not value.is_dir():
        raise PublishError("A real directory is required; symlinks are forbidden")
    return value.resolve()


def files_under(root: Path, *, repository: bool = False) -> dict[str, Path]:
    files, seen = {}, set()
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        if repository and current_path == root:
            directories[:] = [name for name in directories if name != ".git"]
        for name in directories + names:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            relative_path(relative, allow_previews=repository)
            folded = unicodedata.normalize("NFC", relative).casefold()
            if folded in seen or path.is_symlink():
                raise PublishError("Symlinks and case-conflicting paths are forbidden")
            seen.add(folded)
            if path.is_file():
                files[relative] = path
            elif not path.is_dir():
                raise PublishError("Only regular files and directories are supported")
    return files


def load_json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PublishError("Duplicate JSON keys are forbidden")
            result[key] = value
        return result
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublishError(f"Invalid JSON file: {path.name}") from exc
    if not isinstance(value, dict):
        raise PublishError("JSON metadata must be an object")
    return value


def verify_artifact(site: Path, args) -> tuple[dict, dict[str, Path]]:
    files = files_under(site)
    if "build-info.json" not in files or "site-manifest.json" not in files or "index.html" not in files:
        raise PublishError("Artifact needs index.html, build-info.json and site-manifest.json")
    info, manifest = load_json(files["build-info.json"]), load_json(files["site-manifest.json"])
    if set(info) != {"schema_version", "source_sha", "run_id", "kind", "base_url"} or type(info.get("schema_version")) is not int:
        raise PublishError("Artifact build-info must contain exactly the five supported identity fields")
    expected = {"schema_version": 1, "source_sha": full_sha(args.source_sha),
                "run_id": str(args.run_id), "kind": args.kind}
    if any(info.get(key) != value for key, value in expected.items()):
        raise PublishError("Artifact build identity does not match the requested deployment")
    base = info.get("base_url")
    if not isinstance(base, str):
        raise PublishError("Artifact base_url is missing")
    url = urlsplit(base)
    if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password or url.query or url.fragment or not base.endswith("/"):
        raise PublishError("Invalid artifact base_url")
    if any(part in {".", ".."} for part in unquote(url.path).split("/")):
        raise PublishError("Invalid artifact base_url path")
    if args.base_url and base != args.base_url.rstrip("/") + "/":
        raise PublishError("Artifact base_url does not match the deployment URL")
    if args.kind == "preview" and not url.path.endswith(f"/previews/pr-{args.pr_number}/"):
        raise PublishError("Preview base_url does not match the PR number")
    if args.kind == "production" and "/previews/" in url.path:
        raise PublishError("Production artifacts cannot use a preview URL")
    expected_files = manifest.get("files")
    if type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 1 or not isinstance(expected_files, dict):
        raise PublishError("Invalid site manifest")
    for name, digest in expected_files.items():
        relative_path(name)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PublishError("Invalid manifest checksum")
    if set(expected_files) != set(files) - {"site-manifest.json"}:
        raise PublishError("Manifest must list every artifact file except itself")
    for name, digest in expected_files.items():
        if hashlib.sha256(files[name].read_bytes()).hexdigest() != digest:
            raise PublishError(f"Artifact checksum mismatch: {name}")
    return info, files


def git(repo: Path, *arguments: str, raw: bool = False, check: bool = True):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-C", str(repo), *arguments],
        env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        # Do not echo remote URLs, credentials, or Git's potentially sensitive stderr.
        raise PublishError(f"git {arguments[0]} failed (exit {result.returncode})")
    return result if not check else result.stdout if raw else result.stdout.decode("utf-8").strip()


def prepare_repository(value: Path, expected_head: str | None = None) -> tuple[Path, str]:
    repo = directory(value)
    metadata = repo / ".git"
    if metadata.is_symlink() or not metadata.is_dir():
        raise PublishError("Target must be an independent clone with a local .git directory")
    for current, directories, names in os.walk(metadata, followlinks=False):
        if any((Path(current) / name).is_symlink() for name in directories + names):
            raise PublishError("Symlinks inside .git are forbidden")
    if repo == Path(__file__).resolve().parent.parent:
        raise PublishError("Refusing to publish into the source repository")
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise PublishError("Repository root does not match --repo-dir")
    common = Path(git(repo, "rev-parse", "--git-common-dir"))
    if (repo / common).resolve() != metadata.resolve():
        raise PublishError("Shared Git directories are unsupported")
    files_under(repo, repository=True)
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--ignored"):
        raise PublishError("Target repository must have no local or ignored changes")
    previous = git(repo, "rev-parse", "HEAD")
    if expected_head and previous != full_sha(expected_head):
        raise PublishError("Target HEAD does not match expected-head")
    require_remote_head(repo, previous)
    return repo, previous


def require_remote_head(repo: Path, expected: str) -> None:
    git(repo, "fetch", "--no-tags", "origin", "refs/heads/master:refs/remotes/origin/master")
    if git(repo, "rev-parse", "refs/remotes/origin/master") != expected:
        raise PublishError("Remote master changed; use a fresh checkout before publishing")


def replace_production(repo: Path, files: dict[str, Path]) -> None:
    for child in repo.iterdir():
        if child.name in {".git", "previews"}:
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for name, source in files.items():
        target = repo / relative_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def commit_and_push(repo: Path, previous: str, message: str) -> str:
    git(repo, "add", "--all", "--force", "--", ".")
    if git(repo, "diff", "--cached", "--quiet", check=False).returncode == 0:
        require_remote_head(repo, previous)
        return previous
    git(repo, "-c", "user.name=github-actions[bot]", "-c",
        "user.email=41898282+github-actions[bot]@users.noreply.github.com", "commit", "-m", message)
    published = git(repo, "rev-parse", "HEAD")
    require_remote_head(repo, previous)
    git(repo, "push", "origin", "HEAD:refs/heads/master")  # Ordinary fast-forward only.
    return published


def deploy(args) -> dict:
    if args.kind == "preview" and (not args.pr_number or args.pr_number < 1):
        raise PublishError("Preview deployments require a positive --pr-number")
    if args.kind == "production" and args.pr_number is not None:
        raise PublishError("Production deployments do not accept --pr-number")
    site = directory(args.site)
    info, files = verify_artifact(site, args)
    repo, previous = prepare_repository(args.repo_dir)
    if site == repo or repo in site.parents or site in repo.parents:
        raise PublishError("Artifact and destination directories must not overlap")
    if args.kind == "production":
        replace_production(repo, files)
    else:
        preview = repo / "previews" / f"pr-{args.pr_number}"
        if preview.exists():
            shutil.rmtree(preview)
        preview.mkdir(parents=True)
        for name, source in files.items():
            target = preview / relative_path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    published = commit_and_push(repo, previous, f"Publish {args.kind} {info['source_sha']} (run {info['run_id']})")
    return {"ok": True, "action": "deploy", "schema_version": info["schema_version"],
            "source_sha": info["source_sha"], "run_id": info["run_id"],
            "kind": info["kind"], "base_url": info["base_url"], "pr_number": args.pr_number,
            "previous_commit": previous, "published_commit": published}


def cleanup(args) -> dict:
    if args.pr_number < 1:
        raise PublishError("A positive --pr-number is required")
    repo, previous = prepare_repository(args.repo_dir)
    preview = repo / "previews" / f"pr-{args.pr_number}"
    if preview.exists():
        if not preview.is_dir():
            raise PublishError("Preview path is not a directory")
        shutil.rmtree(preview)
    published = commit_and_push(repo, previous, f"Remove preview for PR #{args.pr_number}")
    return {"ok": True, "action": "cleanup", "pr_number": args.pr_number,
            "previous_commit": previous, "published_commit": published, "source_sha": None}


def rollback(args) -> dict:
    target = full_sha(args.commit)
    repo, previous = prepare_repository(args.repo_dir, args.expected_head)
    if git(repo, "cat-file", "-t", target) != "commit":
        raise PublishError("Rollback target must identify a commit")
    if git(repo, "merge-base", "--is-ancestor", target, "refs/remotes/origin/master", check=False).returncode:
        raise PublishError("Rollback target must be in origin/master history")
    with tempfile.TemporaryDirectory(prefix="pages-rollback-") as temporary:
        source = Path(temporary)
        files = {}
        for entry in git(repo, "ls-tree", "-r", "-z", target, raw=True).split(b"\0"):
            if not entry:
                continue
            metadata, path_bytes = entry.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split()
            name = path_bytes.decode("utf-8")
            path = relative_path(name, allow_previews=True)
            if path.parts[0] == "previews":
                continue
            relative_path(name)
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise PublishError("Rollback history contains non-regular static files")
            output = source / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(git(repo, "cat-file", "blob", object_id, raw=True))
            files[name] = output
        if "index.html" not in files:
            raise PublishError("Rollback target does not contain a production index.html")
        files_under(source)
        info = {}
        if "build-info.json" in files:
            info = load_json(source / "build-info.json")
            identity = argparse.Namespace(
                source_sha=info.get("source_sha", ""), run_id=info.get("run_id", ""),
                kind="production", pr_number=None,
                base_url=getattr(args, "base_url", "https://sona201.github.io/"),
            )
            info, files = verify_artifact(source, identity)
        replace_production(repo, files)
        published = commit_and_push(repo, previous, f"Restore production static files from {target}")
    return {"ok": True, "action": "rollback", "rollback_target": target,
            "previous_commit": previous, "published_commit": published,
            "source_sha": info.get("source_sha")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("deploy", deploy), ("cleanup", cleanup), ("rollback", rollback)):
        command = commands.add_parser(name)
        command.add_argument("--repo-dir", type=Path, required=True)
        command.add_argument("--output", type=Path)
        command.set_defaults(handler=handler)
        if name == "deploy":
            command.add_argument("--site", type=Path, required=True)
            command.add_argument("--kind", choices=("production", "preview"), required=True)
            command.add_argument("--source-sha", required=True)
            command.add_argument("--run-id", required=True)
            command.add_argument("--base-url")
            command.add_argument("--pr-number", type=int)
        elif name == "cleanup":
            command.add_argument("--pr-number", type=int, required=True)
        else:
            command.add_argument("--commit", required=True)
            command.add_argument("--expected-head")
            command.add_argument("--base-url", default="https://sona201.github.io/")
    args = parser.parse_args(argv)
    try:
        if args.output:
            output = args.output.absolute()
            if any(path.is_symlink() for path in (output, *output.parents)):
                raise PublishError("Output path cannot contain symlinks")
            destination = output.resolve()
            protected = [args.repo_dir.resolve()]
            if args.command == "deploy":
                protected.append(args.site.resolve())
            if any(destination == path or path in destination.parents for path in protected):
                raise PublishError("Output must be outside the target repository and artifact")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.exists() and not args.output.is_file():
                raise PublishError("Output must be a regular file")
        result = args.handler(args)
    except (PublishError, OSError, UnicodeError) as exc:
        result = {"ok": False, "action": args.command, "error": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
