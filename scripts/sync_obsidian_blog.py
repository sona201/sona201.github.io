#!/usr/bin/env python3
"""Export only reviewed public Obsidian manuscripts to Hugo (stdlib only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import unicodedata
from urllib.parse import quote

import migrate_notes as markdown


PUBLIC_NOTES = "博客"
PUBLIC_IMAGES = Path("附件/博客/images")
VAULT_CONFIG = ".obsidian-vault.json"
IMAGE_KINDS = {"image", "html_image", "wiki_image"}


def normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def safe_relative(value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Invalid relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("Absolute paths and path traversal are forbidden")
    return Path(*path.parts)


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def exact_path(root: Path, relative: Path, must_exist: bool = True) -> Path:
    """Check actual filename case even on case-insensitive filesystems."""
    current = root
    for part in relative.parts:
        if current.exists():
            children = list(current.iterdir())
            matches = [p for p in children if normalized(p.name) == normalized(part)]
            if matches:
                current = matches[0]
            else:
                if any(normalized(p.name).casefold() == normalized(part).casefold() for p in children):
                    raise ValueError("Filename case does not match")
                current = current / part
        else:
            current = current / part
        if current.is_symlink():
            raise ValueError("Symlinks are forbidden in export paths")
    if not inside(current, root):
        raise ValueError("Path escapes its allowed directory")
    if must_exist and not current.is_file():
        raise ValueError("Required file does not exist")
    if not must_exist and current.exists() and not current.is_file():
        raise ValueError("Output path is not a regular file")
    return current


def check_public(text: str) -> None:
    if text.lstrip().startswith("{"):
        # Hugo also accepts JSON metadata, but the Markdown reference parser
        # handles YAML/TOML. Refuse that unsupported format rather than miss flags.
        raise ValueError("Public manuscripts must use YAML or TOML front matter")
    end = markdown.front_matter_end(text)
    header = text[:end]
    # Inline mapping/table syntax needs a full YAML/TOML parser. Reject it
    # explicitly, instead of silently overlooking a nested publication flag.
    without_strings = re.sub(r'''"(?:\\.|[^"\\])*"|'(?:''|[^'])*'|\#[^\n]*''', "", header)
    if "{" in without_strings or "}" in without_strings:
        raise ValueError("Inline metadata mappings are unsupported; use explicit YAML or TOML fields")
    keys = re.compile(r'''^\s*("(?:\\.|[^"\\])*"|'(?:''|[^'])*'|[A-Za-z_][\w-]*)\s*[:=]\s*([^\n]+)''', re.M)
    for match in keys.finditer(header):
        token = match[1]
        if token.startswith('"'):
            try:
                key = json.loads(token).lower()
            except ValueError:
                raise ValueError("Unsupported quoted metadata key") from None
        elif token.startswith("'"):
            key = token[1:-1].replace("''", "'").lower()
        else:
            key = token.lower()
        if key not in ("draft", "private", "publish", "published"):
            continue
        value = match[2].split("#", 1)[0].strip().strip("\"'").lower()
        if value not in ("true", "yes", "on", "1", "false", "no", "off", "0"):
            raise ValueError("Publication flags must be explicit booleans")
        if key in ("draft", "private") and value in ("true", "yes", "on", "1"):
            raise ValueError("Draft or private notes cannot be exported")
        if key in ("publish", "published") and value in ("false", "no", "off", "0"):
            raise ValueError("Notes marked as unpublished cannot be exported")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_source_links(text: str, references: list[dict]) -> None:
    for ref in references:
        if ref["kind"] == "wiki_link":
            raise ValueError("Note links and note embeds must be replaced with public blog URLs")
        if ref["kind"] == "link" and not markdown.is_external(ref["url"]):
            if Path(markdown.local_path(ref["url"])).suffix.lower() in (".md", ".txt"):
                raise ValueError("Local note links must be replaced with public blog URLs")
    # The shared image parser resolves reference-style images, but ordinary
    # reference-style links still need their visible definitions checked here.
    for match in markdown.REFERENCE_DEFINITION.finditer(markdown.visible_markdown(text)):
        left, right = markdown.destination_span(text[match.start(2):match.end(2)], match.start(2))
        url = text[left:right]
        if not markdown.is_external(url) and Path(markdown.local_path(url)).suffix.lower() in (".md", ".txt"):
            raise ValueError("Local note links must be replaced with public blog URLs")


def vault_image(vault: Path, source: Path, url: str) -> tuple[Path, Path]:
    value = markdown.local_path(url)
    if value.startswith("/images/"):
        relative = PUBLIC_IMAGES / safe_relative(value[len("/images/"):])
    elif value.startswith("/"):
        raise ValueError("Local images must come from the public attachment directory")
    else:
        candidate = source.parent / value
        # Resolve traversal lexically, then check every real component for symlinks.
        candidate = Path(os.path.abspath(candidate))
        try:
            relative = candidate.relative_to(vault)
        except ValueError:
            raise ValueError("Image path escapes the vault") from None
    try:
        image_relative = relative.relative_to(PUBLIC_IMAGES)
    except ValueError:
        raise ValueError("Local images must come from the public attachment directory") from None
    if image_relative.suffix.lower() not in markdown.IMAGE_SUFFIXES:
        raise ValueError("Only image attachments may be exported")
    image = exact_path(vault, relative)
    return image, Path("static/images") / image_relative


def replace_image(text: str, ref: dict, url: str) -> str:
    if ref["kind"] in ("wiki_image", "html_image"):
        alias = " ".join(ref.get("alias", "").splitlines())
        alias = alias.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
        safe_url = url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")
        return f"![{alias}]({safe_url})"
    return url


def plan_export(vault: Path, blog: Path, manifest: Path) -> tuple[dict, list[tuple[Path, bytes]], list[tuple[Path, bytes]]]:
    vault, blog = vault.resolve(), blog.resolve()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError("Expected a version 1 public export manifest")
    notes, images = [], {}
    used_sources, used_targets = set(), set()
    entries = []
    for entry in data["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("Manifest entries must be objects")
        source_relative = safe_relative(entry.get("source"))
        target_relative = safe_relative(entry.get("target"))
        if source_relative.parts[0] != PUBLIC_NOTES or source_relative.suffix.lower() != ".md":
            raise ValueError("Manuscripts must be Markdown files inside the public notes directory")
        if target_relative.parts[:2] != ("content", "post") or target_relative.suffix.lower() != ".md" or target_relative.name == "_index.md":
            raise ValueError("Targets must be articles inside content/post")
        source_key = normalized(source_relative.as_posix()).casefold()
        target_key = normalized(target_relative.as_posix()).casefold()
        if source_key in used_sources or target_key in used_targets:
            raise ValueError("Duplicate or conflicting manuscript mappings")
        used_sources.add(source_key)
        used_targets.add(target_key)
        source = exact_path(vault, source_relative)
        target = exact_path(blog, target_relative, must_exist=False)
        text = source.read_text(encoding="utf-8-sig")
        try:
            check_public(text)
            references = markdown.references(text)
            check_source_links(text, references)
            replacements = []
            for ref in references:
                if ref["kind"] == "missing_reference":
                    raise ValueError("Undefined image reference")
                if ref["kind"] not in IMAGE_KINDS:
                    continue
                if markdown.is_external(ref["url"]):
                    if ref["kind"] in ("html_image", "wiki_image"):
                        replacements.append((ref["start"], ref["end"], replace_image(text, ref, ref["url"])))
                    continue
                image, image_target_relative = vault_image(vault, source, ref["url"])
                image_target = exact_path(blog, image_target_relative, must_exist=False)
                image_data = image.read_bytes()
                if image_target.exists() and digest(image_target.read_bytes()) != digest(image_data):
                    raise ValueError("Existing blog image has different content; review the image update separately")
                image_key = normalized(image_target_relative.as_posix()).casefold()
                if image_key in images and images[image_key][0] != image_target:
                    raise ValueError("Conflicting image output paths")
                images[image_key] = (image_target, image_data)
                url = "/images/" + quote(image_target_relative.relative_to("static/images").as_posix(), safe="/")
                replacements.append((ref["start"], ref["end"], replace_image(text, ref, url)))
            for start, end, value in sorted(replacements, reverse=True):
                text = text[:start] + value + text[end:]
        except ValueError as exc:
            raise ValueError(f"{source_relative.as_posix()}: {exc}") from None
        article_data = text.encode("utf-8")
        changed = not target.exists() or target.read_bytes() != article_data
        notes.append((target, article_data))
        entries.append({"source": source_relative.as_posix(), "target": target_relative.as_posix(), "changed": changed})
    image_writes = [item for item in images.values() if not item[0].exists()]
    report = {"version": 1, "mode": "check", "summary": {"articles": len(notes), "article_changes": sum(e["changed"] for e in entries), "referenced_images": len(images), "new_images": len(image_writes)}, "entries": entries, "images": [p.relative_to(blog).as_posix() for p, _ in images.values()]}
    return report, notes, image_writes


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".sync-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def configured_vault(blog: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    environment = os.environ.get("OBSIDIAN_VAULT", "").strip()
    if environment:
        return Path(environment).expanduser().resolve()
    config = blog.resolve() / VAULT_CONFIG
    if not config.is_file():
        raise ValueError("Configure the vault once with --set-vault /path/to/vault, or use --vault / OBSIDIAN_VAULT")
    data = json.loads(config.read_text(encoding="utf-8"))
    value = data.get("vault") if isinstance(data, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Local vault configuration must contain a nonempty vault path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = blog.resolve() / path
    return path.resolve()


def configure_vault(blog: Path, vault: Path) -> dict:
    blog, vault = blog.resolve(), vault.expanduser().resolve()
    if not vault.is_dir():
        raise ValueError("The configured vault directory does not exist")
    data = json.dumps({"version": 1, "vault": str(vault)}, ensure_ascii=False, indent=2) + "\n"
    atomic_write(blog / VAULT_CONFIG, data.encode("utf-8"))
    return {"version": 1, "mode": "configure", "config": VAULT_CONFIG, "configured": True}


def audit_public(blog: Path) -> dict:
    blog = blog.resolve()
    errors, articles = [], []
    for article in sorted((blog / "content").rglob("*.md")):
        if article.name == "_index.md":
            continue
        relative = article.relative_to(blog)
        articles.append(relative.as_posix())
        try:
            exact_path(blog, relative)
            text = article.read_text(encoding="utf-8-sig")
            check_public(text)
            references = markdown.references(text)
            check_source_links(text, references)
            for ref in references:
                if ref["kind"] == "missing_reference":
                    raise ValueError("Undefined image reference")
                if ref["kind"] not in IMAGE_KINDS or markdown.is_external(ref["url"]):
                    continue
                value = markdown.local_path(ref["url"])
                if value.startswith("/"):
                    image_relative = Path("static") / safe_relative(value.lstrip("/"))
                else:
                    image_path = Path(os.path.abspath(article.parent / value))
                    try:
                        image_relative = image_path.relative_to(blog)
                    except ValueError:
                        raise ValueError("Image path escapes the blog") from None
                exact_path(blog, image_relative)
        except (ValueError, OSError) as exc:
            errors.append({"article": relative.as_posix(), "reason": str(exc)})
    return {"version": 1, "mode": "audit-public", "summary": {"articles": len(articles), "errors": len(errors)}, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blog", type=Path, default=Path("."))
    parser.add_argument("--vault", type=Path, help="Override OBSIDIAN_VAULT and the local vault configuration")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--report", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Plan the reviewed export without writing (default)")
    modes.add_argument("--apply", action="store_true", help="Overwrite reviewed public articles after the complete plan passes")
    modes.add_argument("--audit-public", action="store_true", help="Check blog publication flags and local image paths; no vault needed")
    modes.add_argument("--set-vault", type=Path, help="Save a vault path in the gitignored local configuration")
    args = parser.parse_args(argv)
    try:
        if args.set_vault:
            report = configure_vault(args.blog, args.set_vault)
            code = 0
        elif args.audit_public:
            report = audit_public(args.blog)
            code = int(bool(report["errors"]))
        else:
            vault = configured_vault(args.blog, args.vault)
            manifest = args.manifest or args.blog / "migration/published-manifest.json"
            report, notes, images = plan_export(vault, args.blog, manifest)
            if args.apply:
                for target, data in images + notes:
                    if not target.exists() or target.read_bytes() != data:
                        atomic_write(target, data)
                report["mode"] = "apply"
            code = 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        report = {"version": 1, "mode": "error", "error": str(exc)}
        code = 1
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
