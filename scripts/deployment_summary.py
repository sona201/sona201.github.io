#!/usr/bin/env python3
"""Write deployment provenance to a workflow summary without PR comments."""
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--deployment", type=Path, required=True)
parser.add_argument("--recovery", type=Path)
parser.add_argument("--url", default="")
parser.add_argument("--verification", default="")
args = parser.parse_args()
lines = ["## Blog publication", "", f"Online verification: **{args.verification or 'not run'}**"]
if args.url:
    lines += [f"[Open site or PR preview]({args.url})"]
for label, path in (("Deployment", args.deployment), ("Automatic recovery", args.recovery)):
    if path and path.is_file():
        data = json.loads(path.read_text())
        lines += ["", f"### {label}"]
        for key in ("action", "kind", "source_sha", "previous_commit", "published_commit", "rollback_target", "verification"):
            if data.get(key) is not None:
                lines += [f"- {key}: `{data[key]}`"]
        commit = data.get("published_commit")
        if commit:
            lines += [f"[Publication commit](https://github.com/sona201/sona201.github.io/commit/{commit})"]
lines += ["", "Manual rollback: run **Blog rollback** on main, using a full commit SHA from the publication repository."]
text = "\n".join(lines) + "\n"
print(text)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
        stream.write(text)
