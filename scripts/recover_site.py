#!/usr/bin/env python3
"""Restore a failed production deployment, then verify the restored bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from types import SimpleNamespace
import urllib.request

import publish_site
import site_checks

BASE_URL = "https://sona201.github.io/"


def verify_legacy(site, attempts=30, interval=10, *, fetch=None, sleep=time.sleep, clock=time.monotonic):
    """Only the first migration can lack a version marker: compare exact homepage."""
    expected = hashlib.sha256((site / "index.html").read_bytes()).hexdigest()
    def download():
        request = urllib.request.Request(BASE_URL + "?rollback-check=" + expected,
                                         headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.geturl().split("?", 1)[0] != BASE_URL:
                raise ValueError("Unexpected website redirect")
            return response.read(8 * 1024 * 1024)
    fetch = fetch or download
    deadline = clock() + 300
    for attempt in range(attempts):
        if clock() >= deadline:
            break
        try:
            if hashlib.sha256(fetch()).hexdigest() == expected:
                return {"verification": "success", "scope": "legacy homepage SHA-256"}
        except (OSError, ValueError):
            pass
        if attempt + 1 < attempts:
            sleep(min(interval, max(0, deadline - clock())))
    raise ValueError("The legacy homepage did not return to its expected content")


def verify_current(repo):
    with tempfile.TemporaryDirectory(prefix="blog-recovery-check-") as temporary:
        site = Path(temporary)
        for name, path in publish_site.files_under(repo, repository=True).items():
            if name.split("/", 1)[0] == "previews":
                continue
            destination = site / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        if (site / "build-info.json").exists():
            site_checks.verify_site(site, BASE_URL, attempts=30, interval=10)
            return {"verification": "success", "scope": "release marker and manifest sample"}
        return verify_legacy(site)


def recover(repo, deployment, output, *, restore=publish_site.rollback, verify=verify_current):
    if not deployment.get("ok") or deployment.get("action") != "deploy" or deployment.get("kind") != "production":
        raise ValueError("Recovery needs a successful production push record")
    result = restore(SimpleNamespace(repo_dir=repo, commit=deployment["previous_commit"],
                                      expected_head=deployment["published_commit"], base_url=BASE_URL))
    result["verification"] = "pending"
    output.write_text(json.dumps(result, indent=2) + "\n")
    try:
        result.update(verify(repo))
    except Exception:
        result["verification"] = "failure"
        output.write_text(json.dumps(result, indent=2) + "\n")
        raise
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--deployment", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        result = verify_current(args.repo_dir.resolve())
    else:
        if not args.deployment or not args.output:
            parser.error("--deployment and --output are required for recovery")
        result = recover(args.repo_dir.resolve(), json.loads(args.deployment.read_text()), args.output)
    print(json.dumps(result, indent=2))
