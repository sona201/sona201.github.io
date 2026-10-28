#!/usr/bin/env python3
"""Fail closed on unreviewed public assets and high-confidence credential patterns.

This complements human review; it does not determine whether prose is confidential.
Diagnostics never include matched text. The public policy stores digests, not secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


SOURCE_DIRS = ("content", "static", "assets", "layouts", "scripts", "examples", "tests", ".github", "migration")
IGNORED_DIRS = {".git", "__pycache__", ".runs", ".pytest_cache", "node_modules"}
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp", ".tif", ".tiff"}
BINARY_ASSETS = IMAGES | {".zip", ".pdf", ".gz", ".tgz", ".tar", ".mp3", ".mp4", ".wav", ".woff", ".woff2", ".ttf", ".otf"}
MAX_TEXT = 16 * 1024 * 1024
MAX_ARCHIVE = 256 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}")
KEY_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    "github-token": re.compile(r"(?<![\w-])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})(?![\w-])"),
    "provider-api-key": re.compile(r"(?<![\w-])sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{24,}(?![\w-])"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
}
SECRET_KEY = r"(?:password|passwd|mysql_pwd|secret|client_secret|api[_-]?key|access[_-]?token|refresh[_-]?token|access[_-]?key[_-]?secret|secret[_-]?access[_-]?key)"
QUOTED_SECRET = re.compile(r"(?i)(?<![\w-])[\"']?" + SECRET_KEY + r"[\"']?\s*[:=]\s*([\"'])([^\n]*?)\1")
PLAIN_SECRET = re.compile(r"(?im)^\s*(?:-\s*)?" + SECRET_KEY + r"\s*[:=]\s*([^\s\"'#[{][^\n]*)$")
MYSQL_PASSWORD = re.compile(r"(?i)\bmysql(?:dump)?(?=[ \t]+-)[^\n;|&`]*?(?:\s--password(?:=|[ \t]+)|\s-p)([^\s;|&`]+)")
URL_PASSWORD = re.compile(r"(?i)\b(?:https?|mysql|postgres(?:ql)?|redis|amqps?)://[^\s/@:]+:([^\s/@]+)@")
BEARER = re.compile(r"(?i)\b(?:authorization[\"']?\s*[:=]\s*[\"']?|curl[^\n]*-H\s*[\"']?authorization:\s*)Bearer\s+([A-Za-z0-9._~+/-]{16,}=*)")
SQL_PASSWORD = re.compile(r"(?i)(?:\bIDENTIFIED\s+BY\s+|\bPASSWORD\(\s*)[\"']([^\"'\n]+)[\"']")


class PrivacyError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_line(value: str) -> str:
    return " ".join(html.unescape(value).split())


def safe_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or "\\" in value or path.is_absolute() or any(p in {"", ".", ".."} for p in value.split("/")):
        raise PrivacyError("Invalid policy path")
    return path.as_posix()


def load_policy(path: Path) -> dict:
    value = json.loads(path.read_text())
    if value.get("schema_version") != 1:
        raise PrivacyError("Unsupported privacy policy")
    for key in ("reviewed_assets", "reviewed_site_images"):
        if not isinstance(value.get(key), dict):
            raise PrivacyError("Missing reviewed asset inventory")
        for name, fingerprint in value[key].items():
            safe_path(name)
            if not isinstance(fingerprint, str) or not SHA256.fullmatch(fingerprint):
                raise PrivacyError("Invalid reviewed asset digest")
    for key in ("blocked_files", "blocked_text_lines"):
        if not isinstance(value.get(key), list) or any(not isinstance(v, str) or not SHA256.fullmatch(v) for v in value[key]):
            raise PrivacyError("Invalid blocked content fingerprints")
    return value


def placeholder(value: str) -> bool:
    value = html.unescape(value).strip().strip("\"'").strip()
    lower = value.lower()
    if not value or value.startswith(("$", "{{", "${", "<", "%")):
        return True
    if lower in {"none", "null", "true", "false", "password", "passwd", "secret", "token", "username", "changeme", "change_me", "redacted", "your-password", "your_password"}:
        return True
    if re.fullmatch(r"[xX*•._-]+", value):
        return True
    return bool(re.fullmatch(r"(?i)(?:example|dummy|test|fake|placeholder|replace[-_]?me|your)[-_][A-Za-z0-9_-]+", value))


class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "pre", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "pre", "div", "li", "tr"}:
            self.parts.append("\n")


def text_views(text: str, suffix: str):
    yield text
    if suffix in {".html", ".xml"}:
        parser = VisibleHTML()
        parser.feed(html.unescape(text) if suffix == ".xml" else text)
        yield "".join(parser.parts)
    elif suffix == ".json":
        try:
            value = json.loads(text)
        except ValueError:
            return
        def strings(item):
            if isinstance(item, str):
                yield item
            elif isinstance(item, dict):
                for nested in item.values():
                    yield from strings(nested)
            elif isinstance(item, list):
                for nested in item:
                    yield from strings(nested)
        for value in strings(value):
            yield value
            if "<" in value:
                parser = VisibleHTML()
                parser.feed(value)
                yield "".join(parser.parts)


def scan_text(text: str, name: str, blocked_lines: set[str]) -> list[dict]:
    findings = set()
    for view_number, view in enumerate(text_views(text, Path(name).suffix.lower())):
        # Extracted HTML/JSON line numbers are logical lines, not original source offsets.
        for line_number, line in enumerate(view.splitlines(), 1):
            rules = set()
            if digest(normalize_line(line).encode()) in blocked_lines:
                rules.add("previously-withdrawn-text")
            for rule, pattern in KEY_PATTERNS.items():
                if pattern.search(line):
                    rules.add(rule)
            for match in QUOTED_SECRET.finditer(line):
                if not placeholder(match[2]):
                    rules.add("literal-secret-field")
            match = PLAIN_SECRET.match(line)
            if match:
                candidate = match[1].split(" #", 1)[0].strip()
                # Bare code expressions are not literal YAML/INI credentials.
                same_identifier = re.match(r"\s*([\w-]+)\s*[:=]", line)
                variable = (same_identifier and candidate == same_identifier[1]) or re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+[,]?", candidate)
                nss_database = re.fullmatch(r"\s*passwd:\s+(?:(?:files|sss|compat|ldap|nis|systemd)\s*)+", line)
                if not variable and not nss_database and not any(token in candidate for token in ("(", ")", "[", "]", " + ", " or ")) and not placeholder(candidate):
                    rules.add("literal-secret-field")
            for rule, pattern in (("mysql-inline-password", MYSQL_PASSWORD), ("sql-literal-password", SQL_PASSWORD), ("url-password", URL_PASSWORD), ("literal-bearer", BEARER)):
                if rule == "mysql-inline-password" and Path(name).suffix.lower() == ".json" and view_number == 0:
                    continue  # JSON string boundaries and escapes are handled by decoded views.
                for match in pattern.finditer(line):
                    if rule == "url-password" and re.search(r"(?i)://guest:guest@(?:localhost|127\.0\.0\.1)(?=[:/]|$)", line[match.start():]):
                        continue  # Documented loopback-only RabbitMQ default account example.
                    if not placeholder(match[1]):
                        rules.add(rule)
            for rule in rules:
                findings.add((rule, line_number, "source" if view_number == 0 else "decoded"))
    return [{"path": name, "rule": rule, "line": line, "view": view} for rule, line, view in sorted(findings)]


def site_path(name: str) -> str:
    return re.sub(r"^previews/pr-[1-9][0-9]*/", "", safe_path(name), count=1)


def asset_allowed(name: str, fingerprint: str, policy: dict, *, site: bool) -> bool:
    if not site:
        return policy["reviewed_assets"].get(name) == fingerprint
    name = site_path(name)
    if policy["reviewed_assets"].get("static/" + name) == fingerprint:
        return True
    return policy["reviewed_site_images"].get(name) == fingerprint


def scan_bytes(data: bytes, name: str, policy: dict, *, site=False, in_archive=False, depth=0) -> list[dict]:
    findings = []
    fingerprint = digest(data)
    if fingerprint in policy["blocked_files"]:
        findings.append({"path": name, "rule": "previously-withdrawn-file", "line": 1})
    suffix = Path(name).suffix.lower()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        text = None
    if suffix in BINARY_ASSETS or text is None:
        allowed = asset_allowed(name, fingerprint, policy, site=site) if not in_archive else fingerprint in set(policy["reviewed_assets"].values())
        if not allowed:
            findings.append({"path": name, "rule": "unreviewed-public-asset", "line": 1})
    if suffix == ".zip":
        if depth >= 2 or len(data) > MAX_ARCHIVE:
            return findings + [{"path": name, "rule": "archive-limit", "line": 1}]
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = archive.infolist()
                if len(members) > 5000 or sum(m.file_size for m in members) > MAX_ARCHIVE:
                    raise PrivacyError("Archive exceeds inspection limit")
                for member in members:
                    if member.is_dir():
                        continue
                    safe_path(member.filename)
                    if member.flag_bits & 1 or stat.S_ISLNK(member.external_attr >> 16):
                        raise PrivacyError("Uninspectable archive entry")
                    findings.extend(scan_bytes(archive.read(member), name + "!" + member.filename, policy, in_archive=True, depth=depth + 1))
        except (PrivacyError, ValueError, OSError, zipfile.BadZipFile, RuntimeError):
            findings.append({"path": name, "rule": "uninspectable-archive", "line": 1})
        return findings
    if text is None:
        return findings
    if len(data) > MAX_TEXT:
        findings.append({"path": name, "rule": "text-inspection-limit", "line": 1})
        return findings
    findings.extend(scan_text(text, name, set(policy["blocked_text_lines"])))
    return findings


def source_files(root: Path):
    if (root / ".git").exists():
        # Includes staged/tracked dotfiles and new nonignored paths, while excluding
        # local vault configuration and build output which are not being published.
        result = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        if result.returncode:
            raise PrivacyError("Cannot enumerate public repository files")
        for raw in result.stdout.split(b"\0"):
            if not raw:
                continue
            name = safe_path(raw.decode("utf-8"))
            path = root / name
            if path.is_file() or path.is_symlink():
                yield path
        return
    for directory in SOURCE_DIRS:
        base = root / directory
        if not base.exists():
            continue
        if base.is_symlink():
            yield base
            continue
        for path in base.rglob("*"):
            if not any(part in IGNORED_DIRS for part in path.relative_to(root).parts) and (path.is_file() or path.is_symlink()):
                yield path
    for path in root.iterdir():
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in {".md", ".yaml", ".yml", ".toml", ".json"}:
            yield path


def check(root: Path, policy: dict, *, site: Path | None = None) -> dict:
    scanroot = site or root
    if not scanroot.is_dir() or scanroot.is_symlink():
        raise PrivacyError("Scan directory must exist and must not be a symlink")
    paths = (p for p in scanroot.rglob("*") if p.is_file() or p.is_symlink()) if site else source_files(root)
    findings, checked = [], 0
    for path in sorted(set(paths)):
        name = path.relative_to(scanroot).as_posix()
        checked += 1
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != scanroot and scanroot in p.parents):
            findings.append({"path": name, "rule": "public-symlink", "line": 1})
            continue
        if path.stat().st_size > MAX_ARCHIVE:
            findings.append({"path": name, "rule": "file-inspection-limit", "line": 1})
            continue
        findings.extend(scan_bytes(path.read_bytes(), name, policy, site=site is not None))
    return {"ok": not findings, "checked_files": checked, "findings": findings}


def review_assets(root: Path, policy: dict, names: list[str], *, site: Path | None = None) -> dict:
    scanroot = site or root
    updates = {}
    for value in names:
        name = safe_path(value)
        path = scanroot / name
        if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents if p != scanroot and scanroot in p.parents):
            raise PrivacyError("Reviewed asset must be a regular local file")
        if path.suffix.lower() not in (IMAGES if site else BINARY_ASSETS):
            raise PrivacyError("Only public images or binary downloads may be reviewed")
        if not site and not name.startswith(("static/", "assets/", "content/", "themes/")):
            raise PrivacyError("Asset is outside the public asset roots")
        fingerprint = digest(path.read_bytes())
        if fingerprint in policy["blocked_files"]:
            raise PrivacyError("A withdrawn asset cannot be approved again")
        updates[site_path(name) if site else name] = fingerprint
    key = "reviewed_site_images" if site else "reviewed_assets"
    policy[key].update(updates)
    policy[key] = dict(sorted(policy[key].items()))
    return {"reviewed": len(updates), "inventory": key}


def save_policy(path: Path, policy: dict):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as stream:
        temporary = Path(stream.name)
        json.dump(policy, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "review-images"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--site", type=Path)
    parser.add_argument("--paths", nargs="+", help="Exact paths explicitly reviewed by a person; no wildcards")
    args = parser.parse_args(argv)
    root = args.root.absolute()
    policy_path = args.policy or root / "migration/public-privacy-policy.json"
    try:
        policy = load_policy(policy_path)
        if args.command == "review-images":
            if not args.paths:
                raise PrivacyError("Review requires an explicit path list")
            result = review_assets(root, policy, args.paths, site=args.site)
            save_policy(policy_path, policy)
        else:
            if args.paths:
                raise PrivacyError("Check always inspects the full public tree")
            result = check(root, policy, site=args.site)
        print(json.dumps(result, ensure_ascii=False))
        return int(not result.get("ok", True))
    except (PrivacyError, OSError, ValueError):
        # Exception strings may contain paths, decoded input or credential text.
        print(json.dumps({"ok": False, "findings": [{"path": ".", "rule": "privacy-check-configuration", "line": 1}]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
