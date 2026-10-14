#!/usr/bin/env python3
"""Require every public article to have an explicit Obsidian export mapping."""
import argparse
import json
from pathlib import Path

from sync_obsidian_blog import safe_relative


def check_manifest(root):
    data = json.loads((root / "migration/published-manifest.json").read_text())
    if data.get("version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError("Expected a version 1 publication manifest")
    sources, targets = set(), set()
    for entry in data["entries"]:
        source, target = safe_relative(entry["source"]), safe_relative(entry["target"])
        if source.parts[0] != "博客" or source.suffix != ".md" or target.parts[:2] != ("content", "post") or target.suffix != ".md":
            raise ValueError("Unexpected source or target in the publication manifest")
        if source in sources or target in targets:
            raise ValueError("Duplicate publication mapping")
        sources.add(source)
        targets.add(target)
    articles = {path.relative_to(root) for path in (root / "content/post").rglob("*.md")
                if not path.name.startswith("_index")}
    if articles != targets:
        raise ValueError(f"Unmapped articles: {sorted(map(str, articles - targets))}; missing exports: {sorted(map(str, targets - articles))}")
    print(f"All {len(articles)} articles have unique reviewed export mappings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blog", type=Path, default=Path("."))
    check_manifest(parser.parse_args().blog)
