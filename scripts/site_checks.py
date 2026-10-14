#!/usr/bin/env python3
"""Offline Hugo checks, immutable build metadata, and bounded deployment probes.

``check`` and ``stamp`` never access the network. ``verify`` first validates the
entire local manifest, then probes the release marker, home/search/RSS/sitemap,
404 page, every CSS/JS file and download, and the three newest search entries.
The remote probe is deliberately a documented sample of HTML pages, not a crawl.
Verification stops at either --attempts (default 30) or the monotonic
--total-timeout budget (default 300 seconds), whichever is reached first.
"""

import argparse
import hashlib
from html import escape, unescape
from html.parser import HTMLParser
import json
from http.client import HTTPException
import math
from pathlib import Path, PurePosixPath
import re
import sys
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET


SCHEMA_VERSION = 1
MARKER = "build-info.json"
MANIFEST = "site-manifest.json"
REQUIRED = ("index.html", "search/index.html", "search/index.json", "index.xml", "sitemap.xml", "404.html")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_SHA = re.compile(r"[0-9a-f]{40}\Z")
ATTRIBUTE = re.compile(r'''(?P<name>[^\s=<>\x27\x22/]+)\s*=\s*(?:"(?P<double>[^"]*)"|'(?P<single>[^']*)'|(?P<bare>[^\s>]+))''')
CSS_URL = re.compile(r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^\s)]+))\s*\)''', re.IGNORECASE)
URL_ATTRIBUTES = ("href", "src", "data-json", "data-index-url", "action")


class CheckError(ValueError):
    """An invalid build or a deployment that does not match the build."""


class DeadlineExceeded(CheckError):
    """The shared verification budget has run out; do not retry."""


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CheckError("duplicate JSON key: " + key)
        result[key] = value
    return result


def json_value(data):
    try:
        return json.loads(data, object_pairs_hook=_no_duplicate_keys)
    except (UnicodeError, ValueError) as exc:
        raise CheckError("invalid JSON: " + str(exc)) from exc


def _decoded_path(path):
    try:
        decoded = unquote(path, errors="strict")
    except UnicodeError as exc:
        raise CheckError("invalid URL encoding") from exc
    if "\\" in decoded or any(ord(char) < 32 or ord(char) == 127 for char in decoded):
        raise CheckError("unsafe URL path")
    return decoded


def _normal_path(path):
    """Normalize URL dot segments, rejecting traversal above the origin root."""
    parts = []
    for part in path.split("/"):
        if part == "..":
            if not parts:
                raise CheckError("path traversal above site root")
            parts.pop()
        elif part and part != ".":
            parts.append(part)
    return "/" + "/".join(parts) + ("/" if parts and path.endswith("/") else "")


def normalize_base_url(value):
    if any(char.isspace() for char in value):
        raise CheckError("base URL must not contain whitespace")
    try:
        parsed = urlsplit(value)
        parsed.port  # Validate malformed/non-numeric ports eagerly.
    except ValueError as exc:
        raise CheckError("invalid base URL") from exc
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise CheckError("base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CheckError("base URL must not include credentials, query or fragment")
    decoded = _decoded_path(parsed.path or "/")
    if any(part in (".", "..") for part in decoded.split("/")):
        raise CheckError("base URL must not contain dot segments")
    path = _normal_path(decoded).rstrip("/") + "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), quote(path, safe="/"), "", ""))


def _origin(parsed):
    return parsed.scheme.lower(), parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def manifest_path(value):
    if not isinstance(value, str) or not value or "\\" in value or any(ord(c) < 32 for c in value):
        raise CheckError("unsafe manifest path: " + repr(value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise CheckError("unsafe manifest path: " + repr(value))
    if any(part.casefold() in (".git", ".github", ".gitmodules", ".gitattributes") for part in path.parts) or path.parts[0].casefold() == "previews":
        raise CheckError("reserved deployment path: " + value)
    return value


def inventory(site):
    site = Path(site)
    if not site.is_dir() or site.is_symlink():
        raise CheckError("site must be a real directory: " + str(site))
    result = {}
    seen = set()
    for path in sorted(site.rglob("*")):
        name = manifest_path(path.relative_to(site).as_posix())
        normalized = unicodedata.normalize("NFC", name).casefold()
        if normalized in seen:
            raise CheckError("case-conflicting path in site: " + name)
        seen.add(normalized)
        if path.is_symlink():
            raise CheckError("symlink is not allowed in site: " + name)
        if path.is_file():
            if not path.resolve().is_relative_to(site.resolve()):
                raise CheckError("file escapes site: " + name)
            result[name] = path
        elif not path.is_dir():
            raise CheckError("special file is not allowed in site: " + name)
    return result


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SiteURLs:
    def __init__(self, base_url):
        self.base_url = normalize_base_url(base_url)
        self.base = urlsplit(self.base_url)
        self.prefix = _decoded_path(self.base.path)

    def url_for(self, name):
        manifest_path(name)
        if name == "index.html":
            name = ""
        elif name.endswith("/index.html"):
            name = name[:-len("index.html")]
        return self.base_url + quote(name, safe="/")

    def relative(self, reference, document="index.html", *, require_local=False):
        """Return an in-scope filesystem path, or None for ignored references."""
        reference = reference.strip()
        if not reference or reference.startswith("#"):
            return None
        try:
            parsed = urlsplit(reference)
            if parsed.scheme and parsed.scheme not in ("http", "https"):
                if require_local:
                    raise CheckError("expected a local HTTP(S) URL")
                return None
            if parsed.netloc:
                absolute = urlsplit(urljoin(self.base_url, reference))
                if _origin(absolute) != _origin(self.base):
                    if require_local:
                        raise CheckError("URL has a different origin")
                    return None
                if absolute.username or absolute.password:
                    raise CheckError("credentials are not allowed in local URLs")
                raw_path = _decoded_path(absolute.path or "/")
            else:
                decoded = _decoded_path(parsed.path)
                source_path = _decoded_path(urlsplit(self.url_for(document)).path)
                if not decoded:
                    raw_path = source_path
                elif decoded.startswith("/"):
                    raw_path = decoded
                else:
                    directory = source_path if source_path.endswith("/") else source_path.rsplit("/", 1)[0] + "/"
                    raw_path = directory + decoded
            path = _normal_path(raw_path)
        except ValueError as exc:
            raise CheckError(str(exc)) from exc
        prefix_without_slash = self.prefix.rstrip("/")
        if path == prefix_without_slash:
            path = self.prefix
        if not path.startswith(self.prefix):
            raise CheckError("local URL escapes base URL path " + self.prefix)
        result = path[len(self.prefix):]
        if result.endswith("/") or not result:
            result += "index.html"
        return manifest_path(result)


def srcset_spans(value):
    """Read srcset URL tokens without treating data-URI commas as candidates."""
    position = 0
    while position < len(value):
        while position < len(value) and (value[position].isspace() or value[position] == ","):
            position += 1
        start = position
        while position < len(value) and not value[position].isspace():
            position += 1
        candidate = value[start:position]
        if not candidate:
            break
        yield start, position - (len(candidate) - len(candidate.rstrip(",")))
        if candidate.endswith(","):
            continue
        parentheses = 0
        while position < len(value):
            char = value[position]
            position += 1
            if char == "(":
                parentheses += 1
            elif char == ")":
                parentheses = max(0, parentheses - 1)
            elif char == "," and not parentheses:
                break


def srcset_urls(value):
    for start, end in srcset_spans(value):
        yield value[start:end]


class HTMLReferences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []
        self.base_references = []

    def handle_starttag(self, tag, attrs):
        for attribute, value in attrs:
            if not value:
                continue
            if tag == "base" and attribute == "href":
                self.base_references.append(value)
            elif attribute in URL_ATTRIBUTES:
                self.references.append((self.getpos()[0], value))
            elif attribute == "srcset":
                self.references.extend((self.getpos()[0], url) for url in srcset_urls(value))


def normalize_preview_links(site, base_url):
    """Rebase existing artifact URLs, never text, JS, external or missing URLs.

    Hugo's canonifyURLs double-prefixes this theme's resource RelPermalinks.
    Build with only --baseURL instead, then adjust root-relative attributes and
    search permalinks. A missing original target is deliberately left for check.
    CSS is not rewritten: check rejects any CSS URL outside the preview prefix.
    """
    files = inventory(site)
    urls = SiteURLs(base_url)
    if urls.prefix == "/":
        return 0
    origin_url = urlunsplit((urls.base.scheme, urls.base.netloc, "/", "", ""))
    root_urls = SiteURLs(origin_url)

    def rebase(reference):
        value = reference.strip()
        try:
            parsed = urlsplit(value)
            if parsed.scheme and parsed.scheme not in ("http", "https"):
                return reference
            if parsed.netloc:
                if parsed.netloc.lower() != urls.base.netloc.lower() or parsed.username or parsed.password:
                    return reference
            elif not value.startswith("/") or value.startswith("//"):
                return reference
            path = _normal_path(_decoded_path(parsed.path or "/"))
            if path.startswith(urls.prefix) or path == urls.prefix.rstrip("/"):
                return reference
            target = root_urls.relative(parsed.path or "/", require_local=True)
            if target not in files and target + "/index.html" not in files:
                return reference
            new_path = urls.base.path.rstrip("/") + (parsed.path or "/")
            return urlunsplit((urls.base.scheme if parsed.netloc else "", urls.base.netloc if parsed.netloc else "", new_path, parsed.query, parsed.fragment))
        except (CheckError, ValueError):
            return reference

    def rebase_srcset(value):
        for start, end in reversed(list(srcset_spans(value))):
            value = value[:start] + rebase(value[start:end]) + value[end:]
        return value

    class Rewriter(HTMLParser):
        def __init__(self, document):
            super().__init__(convert_charrefs=True)
            self.offsets = [0]
            for line in document.splitlines(keepends=True):
                self.offsets.append(self.offsets[-1] + len(line))
            self.replacements = []

        def handle_starttag(self, tag, attrs):
            raw = self.get_starttag_text()
            start = self.offsets[self.getpos()[0] - 1] + self.getpos()[1]
            tag_end = re.match(r"<\s*[^\s/>]+", raw).end()
            for match in ATTRIBUTE.finditer(raw, tag_end):
                attribute = match.group("name").lower()
                if attribute not in URL_ATTRIBUTES + ("srcset",):
                    continue
                group = next(name for name in ("double", "single", "bare") if match.group(name) is not None)
                value = unescape(match.group(group))
                replacement = rebase_srcset(value) if attribute == "srcset" else rebase(value)
                if replacement != value:
                    replacement = escape(replacement, quote=True)
                    # Unquoted attributes need quotes if the normalized value
                    # contains a space. Quoting all rewritten bare values is safe.
                    if group == "bare":
                        replacement = '"' + replacement + '"'
                    self.replacements.append((start + match.start(group), start + match.end(group), replacement))

    updates = {}
    for name, path in files.items():
        if path.suffix.lower() != ".html":
            continue
        document = path.read_text(encoding="utf-8")
        parser = Rewriter(document)
        parser.feed(document)
        if parser.replacements:
            for start, end, value in reversed(parser.replacements):
                document = document[:start] + value + document[end:]
            updates[path] = document
    if "search/index.json" in files:
        entries = search_entries(files)
        changed = False
        for entry in entries:
            replacement = rebase(entry["permalink"])
            if replacement != entry["permalink"]:
                entry["permalink"] = replacement
                changed = True
        if changed:
            updates[files["search/index.json"]] = json.dumps(entries, ensure_ascii=False) + "\n"
    for path, document in updates.items():
        path.write_text(document, encoding="utf-8")
    return len(updates)


def search_entries(files):
    entries = json_value(files["search/index.json"].read_bytes())
    if not isinstance(entries, list) or not entries:
        raise CheckError("search/index.json must be a non-empty array")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("title"), str) or not entry["title"].strip():
            raise CheckError("search entry must have a non-empty title")
        if not isinstance(entry.get("permalink"), str) or not entry["permalink"]:
            raise CheckError("search entry must have a permalink")
        if not isinstance(entry.get("content"), str):
            raise CheckError("search entry must have text content")
    return entries


def check_site(site, base_url):
    files = inventory(site)
    urls = SiteURLs(base_url)
    errors = []
    for name in REQUIRED:
        if name not in files or files[name].stat().st_size == 0:
            errors.append("missing or empty required file: " + name)

    def check_reference(source, reference, *, require_local=False):
        try:
            target = urls.relative(reference, source.split(":", 1)[0], require_local=require_local)
            if target is None:
                if require_local:
                    raise CheckError("expected a page or resource URL")
                return
            if target not in files and target + "/index.html" not in files:
                raise CheckError("missing local target: " + target)
        except CheckError as exc:
            errors.append(f"{source}: {reference!r}: {exc}")

    for name, path in files.items():
        if path.suffix.lower() == ".css":
            try:
                css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
                for match in CSS_URL.finditer(css):
                    reference = next(value for value in match.groups() if value is not None)
                    check_reference(name, reference)
            except UnicodeError as exc:
                errors.append(name + ": cannot parse CSS: " + str(exc))
        if path.suffix.lower() != ".html":
            continue
        parser = HTMLReferences()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
            # Hugo emits no <base>. Refuse ambiguous base overrides rather than
            # validating links against a different base from the browser.
            if parser.base_references:
                errors.append(name + ": HTML <base href> is unsupported; emit explicit site URLs")
            for line, reference in sorted(set(parser.references)):
                check_reference(f"{name}:{line}", reference)
        except (UnicodeError, ValueError) as exc:
            errors.append(name + ": cannot parse HTML: " + str(exc))

    if "search/index.json" in files:
        try:
            for entry in search_entries(files):
                check_reference("search/index.json", entry["permalink"], require_local=True)
        except CheckError as exc:
            errors.append(str(exc))

    for name in ("index.xml", "sitemap.xml"):
        if name not in files:
            continue
        try:
            root = ET.fromstring(files[name].read_bytes())
            if name == "index.xml":
                if root.tag != "rss" or root.find("channel") is None or not root.findall("channel/item"):
                    raise CheckError("RSS must contain a channel and at least one item")
                references = [node.text for node in root.findall("channel/link") + root.findall("channel/item/link")]
            else:
                if root.tag.split("}")[-1] not in ("urlset", "sitemapindex"):
                    raise CheckError("invalid sitemap root element")
                references = [node.text for node in root.iter() if node.tag.split("}")[-1] == "loc"]
                if not references:
                    raise CheckError("sitemap must contain at least one location")
            for reference in references:
                if not reference:
                    raise CheckError("empty XML location")
                check_reference(name, reference, require_local=True)
        except (ET.ParseError, CheckError) as exc:
            errors.append(name + ": " + str(exc))

    if errors:
        raise CheckError(f"offline site check failed ({len(errors)} issues):\n" + "\n".join(errors))
    return files


def validate_marker(marker, base_url):
    expected_keys = {"schema_version", "source_sha", "run_id", "kind", "base_url"}
    if not isinstance(marker, dict) or set(marker) != expected_keys or type(marker.get("schema_version")) is not int or marker["schema_version"] != SCHEMA_VERSION:
        raise CheckError("invalid build-info schema")
    if not isinstance(marker["source_sha"], str) or not SOURCE_SHA.fullmatch(marker["source_sha"]):
        raise CheckError("source SHA must be the full 40-character lowercase Git SHA")
    if not isinstance(marker["run_id"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", marker["run_id"]):
        raise CheckError("run ID must be a non-empty simple identifier")
    if marker["kind"] not in ("production", "preview"):
        raise CheckError("invalid deployment kind")
    if marker["base_url"] != normalize_base_url(base_url):
        raise CheckError("build-info base URL does not match requested URL")
    return marker


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def stamp_site(site, base_url, source_sha, run_id, kind):
    marker = validate_marker({"schema_version": SCHEMA_VERSION, "source_sha": source_sha,
                              "run_id": run_id, "kind": kind, "base_url": normalize_base_url(base_url)}, base_url)
    site = Path(site)
    if kind == "preview":
        changed = normalize_preview_links(site, base_url)
        print(f"Normalized preview URL attributes/search permalinks in {changed} files; body text and scripts unchanged.")
    files = check_site(site, base_url)
    (site / ".nojekyll").write_bytes(b"")
    files[".nojekyll"] = site / ".nojekyll"
    write_json(site / MARKER, marker)
    files[MARKER] = site / MARKER
    hashes = {name: sha256(path) for name, path in sorted(files.items()) if name != MANIFEST}
    write_json(site / MANIFEST, {"schema_version": SCHEMA_VERSION, "files": hashes})
    return marker, hashes


def validate_manifest(site, base_url):
    files = inventory(site)
    if MANIFEST not in files or MARKER not in files:
        raise CheckError("site must be stamped before verification")
    manifest = json_value(files[MANIFEST].read_bytes())
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "files"} or type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION or not isinstance(manifest["files"], dict):
        raise CheckError("invalid site-manifest schema")
    hashes = manifest["files"]
    for name, digest in hashes.items():
        manifest_path(name)
        if name == MANIFEST or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise CheckError("invalid manifest entry: " + name)
    expected = set(files) - {MANIFEST}
    if set(hashes) != expected:
        raise CheckError("manifest file set mismatch; missing=" + repr(sorted(expected - set(hashes))) + "; extra=" + repr(sorted(set(hashes) - expected)))
    for name in REQUIRED + (MARKER,):
        if name not in hashes:
            raise CheckError("required file missing from manifest: " + name)
    for name, digest in hashes.items():
        if sha256(files[name]) != digest:
            raise CheckError("manifest hash mismatch: " + name)
    marker = validate_marker(json_value(files[MARKER].read_bytes()), base_url)
    return marker, hashes, files


def verification_sample(files, base_url):
    urls = SiteURLs(base_url)
    names = set(REQUIRED) | {MARKER}
    names.update(name for name in files if name.lower().endswith((".css", ".js")) or name.startswith("downloads/"))
    entries = sorted(search_entries(files), key=lambda item: (str(item.get("date", "")), item["permalink"]), reverse=True)
    for entry in entries[:3]:
        name = urls.relative(entry["permalink"], "search/index.json", require_local=True)
        if name not in files and name + "/index.html" in files:
            name += "/index.html"
        if name not in files:
            raise CheckError("sample article does not exist: " + str(name))
        names.add(name)
    return [MARKER] + sorted(names - {MARKER})


class SameArtifactRedirects(HTTPRedirectHandler):
    """Permit only equivalent URLs for the same file within this deployment."""
    def __init__(self, urls):
        super().__init__()
        self.urls = urls

    def redirect_request(self, request, response, code, message, headers, newurl):
        old_target = self.urls.relative(request.full_url, require_local=True)
        new_target = self.urls.relative(newurl, require_local=True)
        if old_target != new_target:
            raise CheckError("redirect changes deployment artifact: " + newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def fetch_artifact(opener, urls, name, run_id, expected_size, *, timeout=15, remaining=None):
    url = urls.url_for(name) + "?__site_check=" + quote(run_id, safe="")
    request = Request(url, headers={"User-Agent": "blog-release-verifier/1", "Cache-Control": "no-cache", "Accept-Encoding": "identity"})
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        if name != "404.html" or exc.code != 404:
            raise CheckError(f"{name}: HTTP {exc.code}") from exc
        response = exc
    with response:
        status = response.getcode()
        if status != 200 and not (name == "404.html" and status == 404):
            raise CheckError(f"{name}: HTTP {status}")
        actual_target = urls.relative(response.geturl(), require_local=True)
        expected_target = urls.relative(url, require_local=True)
        if actual_target != expected_target:
            raise CheckError(name + ": response redirected to a different artifact")
        # read1 performs at most one underlying read. Check the shared deadline
        # between chunks so a server dripping bytes cannot keep read(n) alive
        # indefinitely. The request's socket timeout bounds stalled reads.
        reader = getattr(response, "read1", response.read)
        chunks = []
        length = 0
        while length < expected_size + 1:
            if remaining is not None:
                remaining()
            chunk = reader(min(65536, expected_size + 1 - length))
            if remaining is not None:
                remaining()
            if not chunk:
                break
            chunks.append(chunk)
            length += len(chunk)
        body = b"".join(chunks)
    if len(body) != expected_size:
        raise CheckError(name + ": response size does not match build")
    return body


def verify_site(site, base_url, attempts=30, interval=10, *, total_timeout=300,
                opener=None, sleep=time.sleep, clock=None):
    if attempts < 1 or not math.isfinite(interval) or interval < 0:
        raise CheckError("attempts must be positive and interval must be finite and non-negative")
    if not math.isfinite(total_timeout) or total_timeout <= 0:
        raise CheckError("total timeout must be finite and positive")
    clock = clock or time.monotonic
    deadline = clock() + total_timeout

    def remaining():
        available = deadline - clock()
        if available <= 0:
            raise DeadlineExceeded(f"verification deadline exceeded ({total_timeout:g}-second total budget)")
        return available

    marker, hashes, files = validate_manifest(site, base_url)
    names = verification_sample(files, base_url)
    remaining()
    urls = SiteURLs(base_url)
    if opener is None:
        opener = build_opener(SameArtifactRedirects(urls))
    last_error = None
    print(f"Verifying {len(names)} remote artifacts within {total_timeout:g}s: marker, home/search/RSS/sitemap/404, all CSS/JS/downloads, newest 3 articles.")
    for attempt in range(1, attempts + 1):
        remaining()
        try:
            for name in names:
                body = fetch_artifact(opener, urls, name, marker["run_id"], files[name].stat().st_size,
                                      timeout=min(15, remaining()), remaining=remaining)
                if name == MARKER and json_value(body) != marker:
                    raise CheckError("remote build-info identity does not match expected release")
                if hashlib.sha256(body).hexdigest() != hashes[name]:
                    raise CheckError(name + ": remote SHA256 does not match build")
            remaining()
            print(f"Verified {marker['kind']} release {marker['source_sha']} (run {marker['run_id']}).")
            return names
        except DeadlineExceeded:
            raise
        except (CheckError, URLError, OSError, HTTPException) as exc:
            last_error = str(exc)
            print(f"Verification attempt {attempt}/{attempts} failed: {last_error}", file=sys.stderr)
            if attempt < attempts:
                sleep(min(interval, remaining()))
                remaining()
    raise CheckError(f"deployment did not match after {attempts} attempts: {last_error}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "stamp", "verify"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--site", type=Path, required=True)
        subparser.add_argument("--base-url", required=True)
        if command == "stamp":
            subparser.add_argument("--source-sha", required=True)
            subparser.add_argument("--run-id", required=True)
            subparser.add_argument("--kind", choices=("production", "preview"), required=True)
        if command == "verify":
            subparser.add_argument("--attempts", type=int, default=30, help="maximum verification rounds (default: 30)")
            subparser.add_argument("--interval", type=float, default=10, help="seconds between rounds, capped by remaining budget (default: 10)")
            subparser.add_argument("--total-timeout", type=float, default=300, help="total monotonic time budget in seconds, including retries (default: 300)")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            files = check_site(args.site, args.base_url)
            print(f"Offline site check passed ({len(files)} files).")
        elif args.command == "stamp":
            marker, hashes = stamp_site(args.site, args.base_url, args.source_sha, args.run_id, args.kind)
            print(f"Stamped {len(hashes)} files for {marker['kind']} release {marker['source_sha']}.")
        else:
            verify_site(args.site, args.base_url, args.attempts, args.interval, total_timeout=args.total_timeout)
    except (CheckError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
