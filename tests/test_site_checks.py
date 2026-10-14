"""Offline build integrity and deployment verification boundary tests."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request


SPEC = importlib.util.spec_from_file_location("site_checks", Path(__file__).resolve().parents[1] / "scripts/site_checks.py")
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


class FakeResponse(io.BytesIO):
    def __init__(self, data, url, status=200):
        super().__init__(data)
        self.url = url
        self.status = status

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status


class ArtifactServer:
    """No sockets: return bytes from a build, with per-file response overrides."""
    def __init__(self, site, base_url):
        self.site = site
        self.urls = checks.SiteURLs(base_url)
        self.calls = []
        self.overrides = {}

    def open(self, request, timeout):
        name = self.urls.relative(request.full_url, require_local=True)
        self.calls.append(name)
        value = self.overrides.get(name)
        if callable(value):
            value = value()
        if isinstance(value, Exception):
            raise value
        body = self.site.joinpath(name).read_bytes() if value is None else value
        return FakeResponse(body, request.full_url)


class FakeClock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class SiteChecksTests(unittest.TestCase):
    base = "https://example.test/"

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.site = Path(temporary.name) / "public"
        self.site.mkdir()
        self.write("index.html", '<a href="/search/">Search</a><link href="/css/main.css"><script src="/js/main.js"></script>')
        self.write("search/index.html", '<a href="/">Home</a>')
        self.write("404.html", '<a href="/">Home</a>')
        self.write("css/main.css", "body { color: black; }")
        self.write("js/main.js", "console.log('build');")
        self.write("posts/new/index.html", '<a href="/">Home</a>')
        self.write("search/index.json", json.dumps([{"title": "New", "date": "2026-10-14", "permalink": "/posts/new/", "content": "Body"}]))
        self.write("index.xml", '<rss version="2.0"><channel><link>https://example.test/</link><item><link>https://example.test/posts/new/</link></item></channel></rss>')
        self.write("sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.test/posts/new/</loc></url></urlset>')

    def write(self, name, text):
        path = self.site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def append(self, name, text):
        self.write(name, (self.site / name).read_text() + text)

    def stamp(self):
        return checks.stamp_site(self.site, self.base, "a" * 40, "123-1", "production")

    def verify(self, server, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return checks.verify_site(self.site, self.base, opener=server, **kwargs)

    def test_valid_build_is_checked_without_network(self):
        with patch.object(checks, "build_opener", side_effect=AssertionError("network forbidden")):
            files = checks.check_site(self.site, self.base)
            self.stamp()
        self.assertIn("search/index.json", files)
        marker, hashes, _ = checks.validate_manifest(self.site, self.base)
        self.assertEqual(marker["source_sha"], "a" * 40)
        self.assertIn(checks.MARKER, hashes)
        self.assertNotIn(checks.MANIFEST, hashes)

    def test_unicode_encoding_queries_directory_and_relative_links(self):
        self.write("images/中文 image.png", b"image")
        self.write("posts/旧文/index.html", '<img src="../../images/%E4%B8%AD%E6%96%87%20image.png?v=2#top"><a href="../new?sort=1">New</a>')
        self.append("index.html", '<a href="/posts/%E6%97%A7%E6%96%87/">Old</a><a href="/posts/旧文">Same directory</a>')
        checks.check_site(self.site, self.base)

    def test_all_html_files_and_all_srcset_candidates_are_checked(self):
        self.write("images/one.png", b"one")
        self.write("nested/index.html", '<picture><source srcset="/images/one.png 1x, /images/missing.png 2x"></picture>')
        with self.assertRaisesRegex(checks.CheckError, "images/missing.png"):
            checks.check_site(self.site, self.base)

    def test_search_data_index_url_and_form_action_are_checked(self):
        self.append("search/index.html", '<form action="/missing-search/"><div data-index-url="/missing-index.json"></div></form>')
        with self.assertRaises(checks.CheckError) as error:
            checks.check_site(self.site, self.base)
        self.assertIn("missing-search/index.html", str(error.exception))
        self.assertIn("missing-index.json", str(error.exception))

    def test_external_mailto_fragments_and_data_uris_are_not_fetched(self):
        self.append("index.html", '<a href="https://outside.test/missing">External</a><a href="mailto:x@example.test">Mail</a><a href="#missing-fragment">Anchor</a><img srcset="data:image/png;base64,AAAA 1x, https://outside.test/img.png 2x">')
        with patch.object(checks, "build_opener", side_effect=AssertionError("network forbidden")):
            checks.check_site(self.site, self.base)

    def test_missing_link_is_not_silently_treated_as_404_page(self):
        self.append("index.html", '<a href="/does-not-exist/">Broken</a>')
        with self.assertRaisesRegex(checks.CheckError, "missing local target: does-not-exist/index.html"):
            checks.check_site(self.site, self.base)

    def test_encoded_and_relative_path_traversal_are_rejected(self):
        for value in ("../index.html", "/%2e%2e/index.html", "/%2e%2e%2findex.html", "/images/%5c../index.html"):
            with self.subTest(value=value), self.assertRaises(checks.CheckError):
                checks.SiteURLs(self.base).relative(value)

    def test_preview_cannot_link_to_production_root(self):
        urls = checks.SiteURLs("https://example.test/previews/pr-42/")
        self.assertEqual(urls.relative("/previews/pr-42/posts/new/"), "posts/new/index.html")
        for value in ("/posts/new/", "../../posts/new/", "https://example.test/previews/pr-43/index.html"):
            with self.subTest(value=value), self.assertRaisesRegex(checks.CheckError, "escapes base"):
                urls.relative(value)

    def test_empty_or_invalid_search_index_is_rejected(self):
        for data in ("[]", "{}", '[{"title":"new"}]', "not json"):
            with self.subTest(data=data):
                self.write("search/index.json", data)
                with self.assertRaises(checks.CheckError):
                    checks.check_site(self.site, self.base)

    def test_search_and_sitemap_links_must_remain_local_and_exist(self):
        self.write("search/index.json", json.dumps([{"title": "New", "content": "Body", "permalink": "https://source-domain.test/posts/new/"}]))
        with self.assertRaisesRegex(checks.CheckError, "different origin"):
            checks.check_site(self.site, self.base)

    def test_rss_sitemap_and_404_are_required(self):
        for name in ("index.xml", "sitemap.xml", "404.html"):
            with self.subTest(name=name):
                path = self.site / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(checks.CheckError, "missing or empty required"):
                    checks.check_site(self.site, self.base)
                path.write_bytes(original)
        self.write("index.xml", "<rss><channel/></rss>")
        with self.assertRaisesRegex(checks.CheckError, "at least one item"):
            checks.check_site(self.site, self.base)

    def test_symlink_and_reserved_deployment_directories_are_rejected(self):
        link = self.site / "leak"
        link.symlink_to(self.site / "index.html")
        with self.assertRaisesRegex(checks.CheckError, "symlink"):
            checks.inventory(self.site)
        link.unlink()
        for name in (".git/config", "previews/pr-42/index.html"):
            with self.subTest(name=name):
                path = self.write(name, "reserved")
                with self.assertRaisesRegex(checks.CheckError, "reserved"):
                    checks.inventory(self.site)
                path.unlink()
                path.parent.rmdir()
                if name.startswith("previews/"):
                    (self.site / "previews").rmdir()

    def test_stamp_refuses_invalid_sha_without_writing_metadata(self):
        with self.assertRaisesRegex(checks.CheckError, "full 40-character"):
            checks.stamp_site(self.site, self.base, "abc123", "123", "production")
        self.assertFalse((self.site / checks.MARKER).exists())

    def preview_fixture(self):
        base = self.base + "previews/pr-42/"
        self.write("index.xml", '<rss version="2.0"><channel><link>' + base + '</link><item><link>' + base + 'posts/new/</link></item></channel></rss>')
        self.write("sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + base + 'posts/new/</loc></url></urlset>')
        return base

    def test_preview_stamp_rebases_existing_urls_but_not_examples_or_external_links(self):
        base = self.preview_fixture()
        self.write("images/photo.png", b"photo")
        self.append("index.html", '''
<a href="https://example.test/posts/new/?q=1&amp;x=2#part">Absolute production</a>
<a href='http://example.test/posts/new/'>Same host HTTP</a>
<img srcset="/images/photo.png 1x, https://example.test/images/photo.png 2x">
<a href="/previews/pr-42/posts/new/">Already prefixed</a>
<a href="https://outside.test/posts/new/">Outside</a>
<form action="/search/"><div data-index-url="https://example.test/search/index.json"></div></form>
<code>&lt;a href="/posts/new/"&gt; /images/photo.png</code>
<script>const example = '<a href="/posts/new/">';</script>
''')
        self.append("search/index.html", '<a href=/posts/new/>Bare</a>')
        with contextlib.redirect_stdout(io.StringIO()):
            checks.stamp_site(self.site, base, "a" * 40, "123-1", "preview")
        html = (self.site / "index.html").read_text()
        self.assertIn('href="https://example.test/previews/pr-42/posts/new/?q=1&amp;x=2#part"', html)
        self.assertIn("href='https://example.test/previews/pr-42/posts/new/'", html)
        self.assertIn('srcset="/previews/pr-42/images/photo.png 1x, https://example.test/previews/pr-42/images/photo.png 2x"', html)
        self.assertIn('href="https://outside.test/posts/new/"', html)
        self.assertIn('action="/previews/pr-42/search/"', html)
        self.assertIn('data-index-url="https://example.test/previews/pr-42/search/index.json"', html)
        self.assertIn('<code>&lt;a href="/posts/new/"&gt; /images/photo.png</code>', html)
        self.assertIn('const example = \'<a href="/posts/new/">\';', html)
        self.assertNotIn("previews/pr-42/previews/pr-42", html)
        self.assertEqual(json.loads((self.site / "search/index.json").read_text())[0]["permalink"], "/previews/pr-42/posts/new/")
        self.assertIn('href="/previews/pr-42/posts/new/"', (self.site / "search/index.html").read_text())
        marker, hashes, _ = checks.validate_manifest(self.site, base)
        self.assertEqual(marker["kind"], "preview")
        self.assertIn(".nojekyll", hashes)

    def test_production_stamp_does_not_rewrite_urls(self):
        self.append("index.html", '<a href="https://example.test/posts/new/">Absolute</a><form action="/search/" data-index-url="/search/index.json"></form>')
        before = (self.site / "index.html").read_bytes()
        self.stamp()
        self.assertEqual((self.site / "index.html").read_bytes(), before)

    def test_preview_rewriter_is_idempotent_and_preserves_missing_links_for_failure(self):
        base = self.preview_fixture()
        checks.normalize_preview_links(self.site, base)
        before = {name: path.read_bytes() for name, path in checks.inventory(self.site).items()}
        self.assertEqual(checks.normalize_preview_links(self.site, base), 0)
        self.assertEqual({name: path.read_bytes() for name, path in checks.inventory(self.site).items()}, before)
        self.append("index.html", '<a href="https://example.test/does-not-exist/">Broken</a>')
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checks.CheckError, "escapes base"):
            checks.stamp_site(self.site, base, "a" * 40, "123-1", "preview")
        self.assertFalse((self.site / checks.MARKER).exists())

    def test_preview_css_root_urls_are_reported_not_silently_rewritten(self):
        base = self.preview_fixture()
        self.write("images/photo.png", b"photo")
        self.append("css/main.css", 'body { background: url("/images/photo.png"); }')
        before = (self.site / "css/main.css").read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(checks.CheckError, "css/main.css"):
            checks.stamp_site(self.site, base, "a" * 40, "123-1", "preview")
        self.assertEqual((self.site / "css/main.css").read_bytes(), before)

    def test_modified_local_file_fails_before_any_network_request(self):
        self.stamp()
        self.write("js/main.js", "modified")
        server = ArtifactServer(self.site, self.base)
        with self.assertRaisesRegex(checks.CheckError, "manifest hash mismatch"):
            self.verify(server, attempts=1)
        self.assertEqual(server.calls, [])

    def test_manifest_cannot_omit_or_add_file_or_escape_directory(self):
        self.stamp()
        path = self.site / checks.MANIFEST
        original = json.loads(path.read_text())
        for name in ("../secret", "/absolute", "x/../index.html", "x//index.html", "previews/x"):
            with self.subTest(name=name):
                value = json.loads(json.dumps(original))
                value["files"][name] = "0" * 64
                checks.write_json(path, value)
                with self.assertRaises(checks.CheckError):
                    checks.validate_manifest(self.site, self.base)
        checks.write_json(path, original)
        self.write("unmanifested.txt", "extra")
        with self.assertRaisesRegex(checks.CheckError, "file set mismatch"):
            checks.validate_manifest(self.site, self.base)

    def test_duplicate_json_keys_and_self_manifest_are_rejected(self):
        self.stamp()
        self.write(checks.MANIFEST, '{"schema_version":1,"schema_version":1,"files":{}}')
        with self.assertRaisesRegex(checks.CheckError, "duplicate"):
            checks.validate_manifest(self.site, self.base)
        self.stamp()
        path = self.site / checks.MANIFEST
        value = json.loads(path.read_text())
        value["files"][checks.MANIFEST] = "0" * 64
        checks.write_json(path, value)
        with self.assertRaisesRegex(checks.CheckError, "invalid manifest entry"):
            checks.validate_manifest(self.site, self.base)

    def test_verify_hashes_resources_downloads_and_newest_three_articles(self):
        entries = []
        for number in range(5):
            self.write(f"posts/{number}/index.html", f"<p>Article {number}</p>")
            entries.append({"title": str(number), "content": "body", "date": f"2026-10-{number + 1:02}", "permalink": f"/posts/{number}/"})
        self.write("search/index.json", json.dumps(entries))
        self.write("downloads/demo.zip", b"download")
        self.write("js/unreferenced.js", "still checked")
        self.stamp()
        server = ArtifactServer(self.site, self.base)
        names = self.verify(server, attempts=1)
        self.assertEqual(server.calls[0], checks.MARKER)
        self.assertIn("downloads/demo.zip", names)
        self.assertIn("js/unreferenced.js", names)
        self.assertIn("posts/4/index.html", names)
        self.assertIn("posts/2/index.html", names)
        self.assertNotIn("posts/1/index.html", names)

    def test_stale_release_marker_is_retried_and_then_fails(self):
        self.stamp()
        server = ArtifactServer(self.site, self.base)
        server.overrides[checks.MARKER] = (self.site / checks.MARKER).read_bytes().replace(b"a" * 40, b"b" * 40)
        sleeps = []
        with self.assertRaisesRegex(checks.CheckError, "after 3 attempts.*identity"):
            self.verify(server, attempts=3, interval=2, sleep=sleeps.append)
        self.assertEqual(server.calls, [checks.MARKER] * 3)
        self.assertEqual(sleeps, [2, 2])

    def test_transient_network_failure_recovers_with_bounded_retry(self):
        self.stamp()
        server = ArtifactServer(self.site, self.base)
        sequence = iter([URLError("not deployed yet"), (self.site / checks.MARKER).read_bytes()])
        server.overrides[checks.MARKER] = lambda: next(sequence)
        sleeps = []
        self.verify(server, attempts=2, interval=0, sleep=sleeps.append)
        self.assertEqual(sleeps, [0])

    def test_total_budget_bounds_all_samples_not_just_retry_count(self):
        self.stamp()
        clock = FakeClock()
        timeouts = []
        class SlowServer(ArtifactServer):
            def open(inner, request, timeout):
                timeouts.append(timeout)
                clock.advance(min(6, timeout))
                return super().open(request, timeout)
        server = SlowServer(self.site, self.base)
        with self.assertRaisesRegex(checks.CheckError, "deadline exceeded.*10-second"):
            self.verify(server, attempts=30, total_timeout=10, clock=clock)
        self.assertEqual(timeouts, [10, 4])
        self.assertEqual(len(server.calls), 2)
        self.assertEqual(clock.now, 10)

    def test_retry_sleep_is_capped_at_remaining_total_budget(self):
        self.stamp()
        clock = FakeClock()
        server = ArtifactServer(self.site, self.base)
        sleeps = []
        def unavailable():
            clock.advance(3)
            return URLError("not ready")
        def sleep(seconds):
            sleeps.append(seconds)
            clock.advance(seconds)
        server.overrides[checks.MARKER] = unavailable
        with self.assertRaisesRegex(checks.CheckError, "deadline exceeded"):
            self.verify(server, attempts=30, interval=10, total_timeout=5, clock=clock, sleep=sleep)
        self.assertEqual(sleeps, [2])
        self.assertEqual(server.calls, [checks.MARKER])

    def test_total_budget_includes_local_manifest_validation(self):
        self.stamp()
        clock = FakeClock()
        server = ArtifactServer(self.site, self.base)
        original = checks.validate_manifest
        def slow_validation(*args):
            result = original(*args)
            clock.advance(3)
            return result
        with patch.object(checks, "validate_manifest", side_effect=slow_validation):
            with self.assertRaisesRegex(checks.CheckError, "deadline exceeded"):
                self.verify(server, total_timeout=2, clock=clock)
        self.assertEqual(server.calls, [])

    def test_slow_stream_checks_deadline_between_reads(self):
        self.stamp()
        clock = FakeClock()
        responses = []
        class DrippingResponse(FakeResponse):
            def read1(inner, size):
                clock.advance(1)
                return super().read1(1)
        class DrippingServer:
            def open(inner, request, timeout):
                response = DrippingResponse((self.site / checks.MARKER).read_bytes(), request.full_url)
                responses.append(response)
                return response
        with self.assertRaisesRegex(checks.CheckError, "deadline exceeded"):
            self.verify(DrippingServer(), total_timeout=2.5, clock=clock)
        self.assertEqual(len(responses), 1)
        self.assertTrue(responses[0].closed)
        self.assertEqual(clock.now, 3)

    def test_non_positive_or_non_finite_total_budget_is_rejected(self):
        self.stamp()
        for budget in (0, -1, float("inf"), float("nan")):
            with self.subTest(budget=budget):
                server = ArtifactServer(self.site, self.base)
                with self.assertRaisesRegex(checks.CheckError, "total timeout"):
                    self.verify(server, total_timeout=budget)
                self.assertEqual(server.calls, [])

    def test_cli_exposes_total_timeout_with_default_and_override(self):
        with patch.object(checks, "verify_site") as verify:
            self.assertEqual(checks.main(["verify", "--site", str(self.site), "--base-url", self.base]), 0)
            self.assertEqual(verify.call_args.kwargs["total_timeout"], 300)
            self.assertEqual(checks.main(["verify", "--site", str(self.site), "--base-url", self.base, "--total-timeout", "45"]), 0)
            self.assertEqual(verify.call_args.kwargs["total_timeout"], 45)

    def test_wrong_resource_content_fails_even_with_http_200(self):
        self.stamp()
        server = ArtifactServer(self.site, self.base)
        server.overrides["js/main.js"] = b"x" * (self.site / "js/main.js").stat().st_size
        with self.assertRaisesRegex(checks.CheckError, "remote SHA256"):
            self.verify(server, attempts=1)

    def test_external_or_cross_preview_redirect_is_not_followed(self):
        urls = checks.SiteURLs("https://example.test/previews/pr-42/")
        handler = checks.SameArtifactRedirects(urls)
        request = Request(urls.url_for(checks.MARKER))
        for destination in ("https://source-domain.test/build-info.json", "https://example.test/build-info.json", "https://example.test/previews/pr-43/build-info.json"):
            with self.subTest(destination=destination), self.assertRaises(checks.CheckError):
                handler.redirect_request(request, None, 302, "Found", {}, destination)

    def test_equivalent_directory_redirect_is_allowed(self):
        handler = checks.SameArtifactRedirects(checks.SiteURLs(self.base))
        request = Request(self.base + "posts/new/index.html")
        redirect = handler.redirect_request(request, None, 301, "Moved", {}, self.base + "posts/new/")
        self.assertEqual(redirect.full_url, self.base + "posts/new/")

    def test_response_url_is_checked_even_if_transport_skips_handler(self):
        self.stamp()
        class WrongOrigin:
            def open(inner, request, timeout):
                return FakeResponse((self.site / checks.MARKER).read_bytes(), "https://source-domain.test/build-info.json")
        with self.assertRaisesRegex(checks.CheckError, "different origin"):
            self.verify(WrongOrigin(), attempts=1)

    def test_404_document_body_is_verified_even_when_server_returns_404(self):
        self.stamp()
        server = ArtifactServer(self.site, self.base)
        body = (self.site / "404.html").read_bytes()
        server.overrides["404.html"] = lambda: HTTPError(self.base + "404.html", 404, "Not Found", {}, io.BytesIO(body))
        self.verify(server, attempts=1)


if __name__ == "__main__":
    unittest.main()
