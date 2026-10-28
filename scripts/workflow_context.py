#!/usr/bin/env python3
"""Resolve publication authority from GitHub, never from a build artifact."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import urllib.request
import zipfile

SITE_URL = "https://sona201.github.io/"


def github_get(repo, suffix):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/{suffix}",
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json", "User-Agent": "blog-publisher"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def resolve(event_name, event, repo, get, *, workflow_ref=None):
    skip = {"action": "skip"}
    if event_name == "workflow_dispatch":
        number = event.get("inputs", {}).get("cleanup_pr", "")
        if (workflow_ref != "refs/heads/main" or event.get("ref") not in {"main", "refs/heads/main"}
                or not isinstance(number, str) or not re.fullmatch(r"[1-9][0-9]*", number)):
            return skip
        return preview_cleanup(int(number), repo, get)
    if event_name == "pull_request_target":
        if event.get("action") not in {"closed", "unlabeled", "edited"}:
            return skip
        number = int(event["pull_request"]["number"])
        return preview_cleanup(number, repo, get)
    if event_name != "workflow_run":
        return skip
    run = get(f"actions/runs/{int(event['workflow_run']['id'])}")
    workflow = get("actions/workflows/deploy.yml")
    if (run["workflow_id"] != workflow["id"] or run["status"] != "completed"
            or run["conclusion"] != "success"
            or run.get("head_repository", {}).get("full_name") != repo
            or run["run_attempt"] != event["workflow_run"]["run_attempt"]):
        return skip
    sha = run["head_sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid source commit")
    result = {"source_sha": sha, "run_id": str(run["id"]), "build_id": f"{run['id']}-{run['run_attempt']}",
              "artifact_name": f"blog-site-{run['id']}-{run['run_attempt']}"}
    if run["event"] in {"push", "workflow_dispatch"} and run["head_branch"] == "main":
        if get("branches/main")["commit"]["sha"] != sha:
            return skip
        return {**result, "action": "production", "base_url": SITE_URL}
    if run["event"] != "pull_request" or len(run.get("pull_requests", [])) != 1:
        return skip
    number = int(run["pull_requests"][0]["number"])
    pr = get(f"pulls/{number}")
    if (pr["state"] != "open" or pr["base"]["ref"] != "main"
            or pr["head"]["repo"]["full_name"] != repo or pr["head"]["sha"] != sha
            or "preview" not in [label["name"] for label in pr.get("labels", [])]):
        return skip
    return {**result, "action": "preview", "pr_number": str(number),
            "base_url": f"{SITE_URL}previews/pr-{number}/"}


def preview_cleanup(number, repo, get):
    """Recheck current authority, including previews whose PR left main."""
    pr = get(f"pulls/{int(number)}")
    if pr.get("head", {}).get("repo", {}).get("full_name") != repo:
        return {"action": "skip"}
    state, base, labels = pr.get("state"), pr.get("base", {}).get("ref"), pr.get("labels")
    if (state not in {"open", "closed"} or not isinstance(base, str) or not base
            or not isinstance(labels, list)
            or any(not isinstance(label, dict) or not isinstance(label.get("name"), str) for label in labels)):
        raise ValueError("Incomplete PR state cannot authorize preview cleanup")
    authorized = state == "open" and base == "main" and "preview" in [label["name"] for label in labels]
    return {"action": "skip"} if authorized else {"action": "cleanup", "pr_number": str(int(number))}


def unpack(download, destination):
    """Extract one immutable artifact with bounded size, no links or traversal."""
    archives = list(download.iterdir())
    if len(archives) != 1 or not archives[0].is_file() or archives[0].is_symlink():
        raise ValueError("Expected exactly one downloaded artifact archive")
    if destination.exists():
        raise ValueError("Extraction destination must not exist")
    with zipfile.ZipFile(archives[0]) as bundle:
        entries = bundle.infolist()
        if len(entries) > 20000 or sum(item.file_size for item in entries) > 500 * 1024 * 1024:
            raise ValueError("Artifact exceeds file count or size limit")
        seen = set()
        for item in entries:
            name = item.filename.rstrip("/")
            path = PurePosixPath(name)
            mode = item.external_attr >> 16
            if (not name or "\\" in name or path.is_absolute()
                    or any(part in {"", ".", "..", ".git", ".github"} for part in name.split("/"))
                    or name in seen or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR})
                    or item.flag_bits & 1):
                raise ValueError(f"Unsafe artifact entry: {name!r}")
            seen.add(name)
        destination.mkdir(parents=True)
        for item in entries:
            target = destination / item.filename
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(item) as source, target.open("xb") as output:
                    while block := source.read(1024 * 1024):
                        output.write(block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output", type=Path, required=True)
    recheck = sub.add_parser("recheck")
    recheck.add_argument("--context", type=Path, required=True)
    extract = sub.add_parser("unpack")
    extract.add_argument("--download", type=Path, required=True)
    extract.add_argument("--site", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "unpack":
        unpack(args.download, args.site)
        return
    repo = os.environ["GITHUB_REPOSITORY"]
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    context = resolve(os.environ["GITHUB_EVENT_NAME"], event, repo, lambda path: github_get(repo, path),
                      workflow_ref=os.environ.get("GITHUB_REF"))
    if args.command == "recheck":
        if context != json.loads(args.context.read_text()) or context["action"] == "skip":
            raise SystemExit("Publication is stale, revoked or no longer authorized")
    else:
        args.output.write_text(json.dumps(context, indent=2) + "\n")
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            for key, value in context.items():
                output.write(f"{key}={value}\n")
        print(json.dumps(context, indent=2))


if __name__ == "__main__":
    main()
