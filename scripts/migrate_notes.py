#!/usr/bin/env python3
"""Migrate explicitly reviewed notes into a Hugo blog, using only the stdlib.

No source files are changed.  A manifest is required for migrations; the default
mode only plans changes.  Run --audit to inspect existing blog image references.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
from urllib.parse import quote, unquote, urlsplit


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".ico"}
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
WIKI = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")
MD_LINK = re.compile(r"(!?)\[([^\]\n]*)\]\(")
REFERENCE_IMAGE = re.compile(r"!\[([^\]\n]*)\](?:\[([^\]\n]*)\])?")
REFERENCE_DEFINITION = re.compile(r"^ {0,3}\[([^\]\n]+)\]:[ \t]*(.+)$", re.M)
HTML_IMAGE = re.compile(r"<img\b[^>]*\bsrc\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))[^>]*>", re.I)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def front_matter_end(text: str) -> int:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() not in ("---", "+++"):
        return 0
    delimiter = lines[0].strip()
    offset = len(lines[0])
    for line in lines[1:]:
        offset += len(line)
        if line.strip() == delimiter:
            return offset
    raise ValueError("Unclosed front matter")


def visible_markdown(text: str, include_front_matter: bool = False) -> str:
    """Mask code while preserving offsets for safe, exact replacements."""
    spans = []
    header_end = front_matter_end(text)
    if header_end and not include_front_matter:
        spans.append((0, header_end))
    offset = 0
    fence_char, fence_length, fence_start = None, 0, 0
    for line in text.splitlines(keepends=True):
        marker = FENCE.match(line)
        if fence_char:
            if marker and marker[1][0] == fence_char and len(marker[1]) >= fence_length and not line[marker.end():].strip():
                spans.append((fence_start, offset + len(line)))
                fence_char = None
        elif marker:
            fence_char, fence_length, fence_start = marker[1][0], len(marker[1]), offset
        elif line.startswith("    ") or line.startswith("\t"):
            spans.append((offset, offset + len(line)))
        offset += len(line)
    if fence_char:
        spans.append((fence_start, len(text)))
    chars = list(text)
    for start, end in spans:
        chars[start:end] = ["\n" if c == "\n" else " " for c in text[start:end]]
    masked = "".join(chars)
    # Inline code can have any matching number of backticks.
    for match in re.finditer(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", masked, re.S):
        chars[match.start():match.end()] = ["\n" if c == "\n" else " " for c in match[0]]
    return "".join(chars)


def destination_span(value: str, start: int = 0) -> tuple[int, int]:
    """Find the destination, excluding optional Markdown title or angle brackets."""
    left = len(value) - len(value.lstrip())
    if value[left:left + 1] == "<":
        end = value.find(">", left + 1)
        if end >= 0:
            return start + left + 1, start + end
    right = len(value.rstrip())
    title = re.search(r"\s+(?:\"[^\"]*\"|'[^']*'|\([^()]*\))\s*$", value[left:right])
    if title:
        right = left + title.start()
    return start + left, start + right


def references(text: str) -> list[dict]:
    """Return local/external image and link spans from rendered Markdown."""
    visible = visible_markdown(text)
    found = []
    for match in MD_LINK.finditer(visible):
        depth, cursor = 1, match.end()
        while cursor < len(visible) and depth:
            c = visible[cursor]
            if c == "\\":
                cursor += 2
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            cursor += 1
        if depth:
            continue
        left, right = destination_span(text[match.end():cursor - 1], match.end())
        found.append({"start": left, "end": right, "full_start": match.start(), "full_end": cursor, "label": match[2], "url": text[left:right], "kind": "image" if match[1] else "link"})
    labels = {}
    for match in REFERENCE_IMAGE.finditer(visible):
        if visible[match.start():match.start() + 3] == "![[":
            continue
        # Ignore inline images; their bracket part also matches this expression.
        if visible[match.end():match.end() + 1] == "(":
            continue
        label = (match[2] if match[2] is not None else match[1]) or match[1]
        labels.setdefault(" ".join(label.lower().split()), []).append(match)
    definitions = {}
    for match in REFERENCE_DEFINITION.finditer(visible):
        label = " ".join(match[1].lower().split())
        definitions[label] = match
        if label in labels:
            left, right = destination_span(text[match.start(2):match.end(2)], match.start(2))
            found.append({"start": left, "end": right, "url": text[left:right], "kind": "image"})
    for label, matches in labels.items():
        if label not in definitions:
            for match in matches:
                found.append({"start": match.start(), "end": match.end(), "url": label, "kind": "missing_reference"})
    for match in HTML_IMAGE.finditer(visible):
        group = next(i for i in (1, 2, 3) if match[i] is not None)
        alt = re.search(r"\balt\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", match[0], re.I)
        found.append({"start": match.start(), "end": match.end(), "url": html.unescape(text[match.start(group):match.end(group)]), "alias": html.unescape((alt[1] or alt[2]) if alt else ""), "kind": "html_image"})
    for match in WIKI.finditer(visible):
        target, _, alias = match[2].partition("|")
        path = target.split("#", 1)[0]
        kind = "wiki_image" if match[1] and Path(path).suffix.lower() in IMAGE_SUFFIXES else "wiki_link"
        found.append({"start": match.start(), "end": match.end(), "url": target, "alias": alias, "embed": bool(match[1]), "kind": kind})
    # Cover image scalar in common YAML/TOML Hugo front matter.
    header_end = front_matter_end(text)
    if header_end:
        for match in re.finditer(r"^image[ \t]*[:=][ \t]*(.*?)[ \t]*$", text[:header_end], re.M):
            value = match[1].strip()
            if not value or value in ('""', "''", "null", "~"):
                continue
            left, right = match.start(1), match.end(1)
            if value[0:1] in ("\"", "'") and value[-1:] == value[0]:
                left += 1
                right -= 1
            found.append({"start": left, "end": right, "url": text[left:right], "kind": "image"})
    return sorted(found, key=lambda item: item["start"])


def is_external(url: str) -> bool:
    return bool(EXTERNAL.match(url)) and not url.lower().startswith("file:")


def local_path(url: str) -> str:
    value = html.unescape(url.strip())
    value = re.sub(r"\\([\\ ()])", r"\1", value)
    # Decode once only; a literal % in the filename is valid.
    return unquote(urlsplit(value).path)


class Resolver:
    def __init__(self, roots: list[Path], blog: Path):
        self.roots = roots
        self.blog = blog
        self.by_name = defaultdict(list)
        self.notes_by_name = defaultdict(list)
        for root in roots:
            for path in sorted(root.rglob("*")):
                if not path.is_file() or any(part.startswith(".") for part in path.relative_to(root).parts):
                    continue
                if not within(path, root):
                    continue
                if path.suffix.lower() in IMAGE_SUFFIXES:
                    self.by_name[path.name.casefold()].append(path.resolve())
                elif path.suffix.lower() in (".md", ".txt"):
                    self.notes_by_name[path.name.casefold()].append(path.resolve())

    def source(self, value: str) -> Path:
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            matches = [candidate.resolve()] if candidate.is_file() and any(within(candidate, r) for r in self.roots) else []
        else:
            matches = []
            for root in self.roots:
                for relative in (candidate, Path(*candidate.parts[1:]) if candidate.parts and candidate.parts[0] == root.name else candidate):
                    path = (root / relative).resolve()
                    if within(path, root) and path.is_file() and path not in matches:
                        matches.append(path)
        matches = [p for p in matches if p.suffix.lower() in (".md", ".txt") and any(within(p, root) and not any(part.startswith(".") for part in p.relative_to(root).parts) for root in self.roots)]
        if len(matches) != 1:
            raise ValueError(f"Source must resolve uniquely inside --source roots: {value} ({len(matches)} matches)")
        return matches[0]

    def local(self, url: str, source: Path, image: bool = True) -> tuple[Path | None, str | None]:
        name = local_path(url)
        if not name:
            return None, "empty_path"
        path = Path(name)
        candidates = []
        if name.startswith("/"):
            candidates.append(self.blog / "static" / name.lstrip("/"))
            if path.is_absolute():
                candidates.append(path)
            candidates.extend(root / name.lstrip("/") for root in self.roots)
        else:
            candidates.append(source.parent / path)
            candidates.extend(root / path for root in self.roots)
        if not image and not path.suffix:
            candidates += [p.with_suffix(".md") for p in candidates]
            candidates += [p.with_suffix(".txt") for p in candidates if not p.suffix]
        for candidate in candidates:
            suffixes = IMAGE_SUFFIXES if image else {".md", ".txt"}
            candidate = candidate.resolve()
            if candidate.suffix.lower() in suffixes and candidate.is_file() and any(within(candidate, r) and not any(part.startswith(".") for part in candidate.relative_to(r).parts) for r in self.roots + [self.blog]):
                return candidate.resolve(), None
        index = self.by_name if image else self.notes_by_name
        names = [path.name] if path.suffix or image else [path.name + ".md", path.name + ".txt"]
        matches = list(dict.fromkeys(p for basename in names for p in index.get(basename.casefold(), [])))
        # Duplicate mirrored assets are safe when their bytes agree.
        if image and len(matches) > 1 and len({sha256(p) for p in matches}) == 1:
            matches = matches[:1]
        if len(matches) == 1:
            return matches[0], None
        return None, "ambiguous" if matches else "not_found"


class ImageStore:
    def __init__(self, blog: Path):
        self.folder = blog / "static" / "images"
        if not within(self.folder, blog):
            raise ValueError("static/images must resolve inside --blog")
        self.by_hash = {}
        self.planned = {}
        if self.folder.exists():
            for path in sorted(self.folder.rglob("*")):
                if path.is_file():
                    self.by_hash.setdefault(sha256(path), path)

    def plan(self, source: Path) -> tuple[str, Path, bool]:
        digest = sha256(source)
        if digest in self.by_hash:
            target = self.by_hash[digest]
            return "/images/" + quote(target.relative_to(self.folder).as_posix(), safe="/"), target, False
        stem = unicodedata.normalize("NFC", source.stem)
        stem = re.sub(r"[^\w.-]+", "-", stem, flags=re.U).strip("-._") or "image"
        stem = stem[:100]
        suffix = source.suffix.lower()
        target = self.folder / f"{stem}{suffix}"
        if target.exists() or target in self.planned:
            target = self.folder / f"{stem}-{digest[:12]}{suffix}"
        # Never rely on a short digest alone to decide that an existing file matches.
        index = 1
        while target.exists() or target in self.planned:
            target = self.folder / f"{stem}-{digest[:12]}-{index}{suffix}"
            index += 1
        self.by_hash[digest] = target
        self.planned[target] = source
        return "/images/" + quote(target.name), target, True

    def apply(self, destinations: set[Path]) -> int:
        copied = 0
        for target in sorted(destinations):
            if target not in self.planned:
                continue
            source = self.planned[target]
            if target.is_file() and sha256(target) == sha256(source):
                self.planned.pop(target)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation protects an asset that appeared after planning.
            with target.open("xb") as handle:
                handle.write(source.read_bytes())
            self.planned.pop(target)
            copied += 1
        return copied


def source_date(source: Path, explicit: str | None = None) -> str:
    if explicit:
        datetime.fromisoformat(explicit.replace("Z", "+00:00"))
        return explicit
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--reverse", "--format=%aI", "--", source.name],
            cwd=source.parent, capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        pass
    # Explicit UTC avoids depending on the execution host's locale/time zone.
    return datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def add_front_matter(text: str, source: Path, entry: dict) -> str:
    end = front_matter_end(text)
    slug = entry.get("slug") or Path(entry["target"]).stem
    title = entry.get("title") or source.stem
    categories = entry.get("category", entry.get("categories", []))
    if isinstance(categories, str):
        categories = [categories]
    if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
        raise ValueError("category must be a string or list of strings")
    if end:
        header = text[:end]
        delimiter = text.splitlines()[0].strip()
        separator = " = " if delimiter == "+++" else ": "
        existing_date = re.search(r"^date\s*[:=]\s*(.+)$", header, re.M)
        date_value = existing_date[1] if existing_date else json.dumps(source_date(source, entry.get("date")))
        values = {
            "title": json.dumps(title, ensure_ascii=False),
            "date": date_value, "lastmod": date_value,
            "categories": json.dumps(categories, ensure_ascii=False),
            "slug": json.dumps(slug, ensure_ascii=False), "draft": "false",
        }
        if "description" in entry:
            if not isinstance(entry["description"], str):
                raise ValueError("description must be a string")
            values["description"] = json.dumps(entry["description"], ensure_ascii=False)
        additions = [key + separator + value for key, value in values.items()
                     if not re.search(r"^" + key + r"\s*[:=]", header, re.M)]
        if not additions:
            return text
        # Insert before existing TOML tables, so fields stay at the top level.
        opening_end = text.index("\n") + 1
        return text[:opening_end] + "\n".join(additions) + "\n" + text[opening_end:]
    date = source_date(source, entry.get("date"))
    header = ["---", "title: " + json.dumps(title, ensure_ascii=False)]
    if "description" in entry:
        if not isinstance(entry["description"], str):
            raise ValueError("description must be a string")
        header.append("description: " + json.dumps(entry["description"], ensure_ascii=False))
    return "\n".join(header + [
        "date: " + json.dumps(date), "lastmod: " + json.dumps(date),
        "categories: " + json.dumps(categories, ensure_ascii=False), "slug: " + json.dumps(slug, ensure_ascii=False),
        "draft: false", "---", "", text,
    ])


def edit_source(text: str, entry: dict) -> str:
    """Apply reviewed line edits against the original, before any Markdown rewrite."""
    lines = text.splitlines(keepends=True)
    edits = entry.get("text_edits", [])
    if not isinstance(edits, list):
        raise ValueError("text_edits must be an array")
    ranges = []
    for edit in edits:
        start, end, replacement = edit.get("start_line"), edit.get("end_line"), edit.get("replacement")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int) or not isinstance(replacement, str):
            raise ValueError("text_edits require integer start_line/end_line and string replacement")
        if start < 1 or end < start or end > len(lines):
            raise ValueError(f"text_edits line range out of bounds: {start}..{end}")
        ranges.append((start, end, replacement))
    previous_end = 0
    for start, end, _ in sorted(ranges):
        if start <= previous_end:
            raise ValueError("text_edits ranges overlap")
        previous_end = end
    for start, end, replacement in sorted(ranges, reverse=True):
        if replacement and end < len(lines) and not replacement.endswith("\n"):
            replacement += "\n"
        lines[start - 1:end] = [replacement]
    return "".join(lines)


def blog_target(blog: Path, entry: dict) -> Path:
    target = entry.get("target")
    if not isinstance(target, str) or not target or Path(target).is_absolute():
        raise ValueError("target must be a blog-relative path")
    path = (blog / target).resolve()
    if not within(path, blog / "content") or path.suffix.lower() != ".md":
        raise ValueError("target must be a .md file inside content/")
    return path


def relref(blog: Path, target: Path, fragment: str = "") -> str:
    relative = target.relative_to(blog / "content").as_posix()
    if fragment:
        # Obsidian heading links generally match Hugo's heading anchor convention.
        anchor = re.sub(r"[^\w\s-]", "", fragment.lower(), flags=re.U).strip()
        relative += "#" + re.sub(r"\s+", "-", anchor)
    return '{{< relref ' + json.dumps(relative, ensure_ascii=False) + ' >}}'


def transform(text: str, source: Path, resolver: Resolver, store: ImageStore, links: dict[Path, Path]) -> tuple[str, list, list, list, set]:
    replacements, images, missing_images, missing_links, destinations = [], [], [], [], set()
    for ref in references(text):
        url, kind = ref["url"], ref["kind"]
        if kind == "missing_reference":
            missing_images.append({"reference": url, "reason": "undefined_reference_label"})
            continue
        if is_external(url):
            if kind == "html_image":
                alt = ref.get("alias", "").replace("[", "\\[").replace("]", "\\]")
                replacements.append((ref["start"], ref["end"], f"![{alt}]({url})"))
            continue
        if kind in ("image", "wiki_image", "html_image"):
            local, error = resolver.local(url, source)
            if not local:
                missing_images.append({"reference": url, "reason": error})
                continue
            rewritten, target, new = store.plan(local)
            destinations.add(target)
            images.append({"reference": url, "source": str(local), "target": str(target), "new": new})
            if kind in ("wiki_image", "html_image"):
                alias = ref.get("alias", "")
                alt = "" if alias.isdigit() or re.fullmatch(r"\d+x\d+", alias) else alias or local.stem
                alt = alt.replace("[", "\\[").replace("]", "\\]")
                rewritten = f"![{alt}]({rewritten})"
            replacements.append((ref["start"], ref["end"], rewritten))
            continue
        if kind == "link" and (not local_path(url) or Path(local_path(url)).suffix.lower() not in (".md", ".txt")):
            continue
        if kind == "wiki_link" and not local_path(url) and url.startswith("#"):
            note, error = source, None
        else:
            note, error = resolver.local(url, source, image=False)
        if not note or note not in links:
            missing_links.append({"reference": url, "reason": error or "not_in_public_manifest"})
            if kind == "wiki_link":
                label = ref.get("alias") or local_path(url) or url.lstrip("#")
                replacements.append((ref["start"], ref["end"], label))
            else:
                # Strip a reviewed-out note's URL rather than publish a broken/private path.
                replacements.append((ref["full_start"], ref["full_end"], ref["label"]))
            continue
        fragment = unquote(urlsplit(url).fragment)
        rewritten = relref(resolver.blog, links[note], fragment)
        if kind == "wiki_link":
            label = ref.get("alias") or local_path(url) or fragment
            # Note transclusions become links: publishing unreviewed note bodies is avoided.
            label = label.replace("[", "\\[").replace("]", "\\]")
            rewritten = f"[{label}]({rewritten})"
        replacements.append((ref["start"], ref["end"], rewritten))
    for start, end, value in sorted(replacements, reverse=True):
        text = text[:start] + value + text[end:]
    return text, images, missing_images, missing_links, destinations


def migrate(manifest: dict, roots: list[Path], blog: Path, apply: bool) -> dict:
    roots = [root.resolve() for root in roots]
    blog = blog.resolve()
    if manifest.get("version") != 1 or not isinstance(manifest.get("entries"), list):
        raise ValueError("Manifest requires version: 1 and an entries array")
    resolver, store = Resolver(roots, blog), ImageStore(blog)
    entries, links, seen_targets = manifest["entries"], {}, set()
    # Resolve the complete allowlist before changing anything.
    prepared = []
    for entry in entries:
        action = entry.get("action")
        if action not in ("migrate", "merge", "covered", "exclude"):
            raise ValueError(f"Unknown action: {action}")
        values = entry.get("sources")
        if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
            raise ValueError("Every entry requires a non-empty sources array")
        sources = [resolver.source(value) for value in values]
        target = blog_target(blog, entry) if entry.get("target") else None
        if action in ("migrate", "merge", "covered") and target is None:
            raise ValueError(f"{action} entry requires target")
        if action == "migrate":
            if target in seen_targets:
                raise ValueError(f"Duplicate migrate target: {target}")
            seen_targets.add(target)
        if target and action != "exclude":
            for source in sources:
                if source in links and links[source] != target:
                    raise ValueError(f"Source maps to multiple targets: {source}")
                links[source] = target
        prepared.append((entry, sources, target))
    report = {"version": 1, "mode": "apply" if apply else "dry-run", "blog": str(blog), "entries": [], "images_copied": 0}
    plans = []
    for entry, sources, target in prepared:
        item = {"sources": [str(p) for p in sources], "target": str(target) if target else None, "action": entry["action"], "reason": entry.get("reason", "")}
        report["entries"].append(item)
        if entry["action"] != "migrate":
            item["status"] = "needs_manual_merge" if entry["action"] == "merge" else entry["action"]
            continue
        if target.exists():
            item["status"] = "target_exists"
            continue
        source = sources[0]
        try:
            expected = entry.get("source_sha256")
            if expected and (not isinstance(expected, str) or sha256(source) != expected.lower()):
                raise ValueError("source_sha256 does not match sources[0]; review the changed source")
            original = source.read_text(encoding="utf-8-sig")
            original = edit_source(original, entry)
            rendered, images, missing_images, missing_links, destinations = transform(original, source, resolver, store, links)
            item.update(images=images, missing_images=missing_images, missing_links=missing_links)
            if missing_images:
                item["status"] = "blocked_missing_images"
                continue
            rendered = add_front_matter(rendered, source, entry)
            item["status"] = "planned"
            plans.append((item, target, rendered, destinations))
        except (OSError, UnicodeError, ValueError) as exc:
            item.update(status="error", error=str(exc))
    # Invalid covered links must never produce a relref that Hugo cannot resolve.
    while True:
        valid_targets = {target for item, target, _, _ in plans if item["status"] == "planned"} | {target for _, _, target in prepared if target and target.is_file()}
        changed = False
        for item, target, rendered, destinations in plans:
            if item["status"] != "planned":
                continue
            unavailable = [path for path in re.findall(r'\{\{< relref "([^"\n]+)" >\}\}', rendered) if (blog / "content" / path.split("#", 1)[0]).resolve() not in valid_targets]
            if unavailable:
                item.update(status="blocked_missing_links", unavailable_targets=unavailable)
                changed = True
        if not changed:
            break
    if apply:
        for item, target, rendered, destinations in plans:
            if item["status"] != "planned":
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Create the article only after all required images exist.
            try:
                report["images_copied"] += store.apply(destinations)
                with target.open("x", encoding="utf-8", newline="") as handle:
                    handle.write(rendered)
                item["status"] = "migrated"
            except OSError as exc:
                item.update(status="error", error=str(exc))
    # A mirrored source may be covered by an article created in this batch.
    # Validate after dependency planning, and after writes when applying.
    available = {target for _, _, target in prepared if target and target.is_file()}
    if not apply:
        available |= {target for item, target, _, _ in plans if item["status"] == "planned"}
    for item, (entry, _, target) in zip(report["entries"], prepared):
        if entry["action"] == "covered" and target not in available:
            item["status"] = "missing_covered_target"
    report["summary"] = dict(Counter(item["status"] for item in report["entries"]))
    report["missing_images"] = sum(len(i.get("missing_images", [])) for i in report["entries"])
    report["missing_links"] = sum(len(i.get("missing_links", [])) for i in report["entries"])
    return report


def audit(blog: Path) -> dict:
    blog = blog.resolve()
    report = {"version": 1, "mode": "audit", "blog": str(blog), "articles_scanned": 0, "missing_images": [], "obsidian_links": []}
    for article in sorted((blog / "content").rglob("*.md")):
        report["articles_scanned"] += 1
        try:
            refs = references(article.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, ValueError) as exc:
            report["missing_images"].append({"article": str(article), "reason": str(exc)})
            continue
        for ref in refs:
            if ref["kind"] == "wiki_link":
                report["obsidian_links"].append({"article": str(article), "reference": ref["url"]})
            elif ref["kind"] in ("image", "wiki_image", "html_image", "missing_reference") and not is_external(ref["url"]):
                name = local_path(ref["url"])
                candidates = [blog / "static" / name.lstrip("/")] if name.startswith("/") else [article.parent / name, blog / "static" / name, blog / "assets" / name]
                if ref["kind"] == "missing_reference" or not any(p.is_file() and within(p, blog) for p in candidates):
                    report["missing_images"].append({"article": str(article), "reference": ref["url"], "reason": "undefined_reference_label" if ref["kind"] == "missing_reference" else "not_found"})
    report["summary"] = {"missing_images": len(report["missing_images"]), "obsidian_links": len(report["obsidian_links"])}
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", default=[], help="Allowed source root; repeat for multiple repositories")
    parser.add_argument("--blog", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, help="Reviewed JSON manifest, version 1")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only (default)")
    mode.add_argument("--apply", action="store_true", help="Create reviewed new articles and referenced images")
    parser.add_argument("--audit", action="store_true", help="Inspect existing blog image references without writing content")
    parser.add_argument("--report", type=Path, help="Write JSON report (even in dry-run)")
    args = parser.parse_args(argv)
    blog = args.blog.expanduser().resolve()
    if args.audit and (args.manifest or args.apply):
        parser.error("--audit cannot be combined with --manifest or --apply")
    if not args.audit and (not args.manifest or not args.source):
        parser.error("migration requires --manifest and at least one --source")
    roots = [Path(root).expanduser().resolve() for root in args.source]
    if any(not root.is_dir() for root in roots):
        parser.error("every --source must be an existing directory")
    if any(within(blog, root) for root in roots):
        parser.error("--blog must not be inside a --source repository")
    if args.report and any(within(args.report.expanduser().resolve(), root) for root in roots):
        parser.error("--report must not write inside a --source repository")
    try:
        report = audit(blog) if args.audit else migrate(json.loads(args.manifest.read_text(encoding="utf-8")), roots, blog, args.apply)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"Migration error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        output = args.report.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    if args.audit:
        return 1 if report["missing_images"] or report["obsidian_links"] else 0
    failures = {"error", "blocked_missing_images", "blocked_missing_links", "missing_covered_target", "needs_manual_merge"}
    return 1 if any(item["status"] in failures for item in report["entries"]) or report["missing_links"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
