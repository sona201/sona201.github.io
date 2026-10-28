"""Privacy gates reject credentials and unreviewed assets without printing values."""
import contextlib
import html
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import public_privacy as privacy


def empty_policy():
    return {"schema_version": 1, "reviewed_assets": {}, "reviewed_site_images": {},
            "blocked_files": [], "blocked_text_lines": []}


class TextPrivacyTests(unittest.TestCase):
    def assert_rule(self, text, rule, name="content/post/example.md"):
        findings = privacy.scan_text(text, name, set())
        self.assertIn(rule, {finding["rule"] for finding in findings})
        self.assertNotIn(text, json.dumps(findings))

    def test_recognizes_provider_keys_and_private_key_headers(self):
        cases = [
            ("ghp_" + "A" * 30, "github-token"),
            ("github_pat_" + "b" * 40, "github-token"),
            ("sk-proj-" + "A1b2" * 10, "provider-api-key"),
            ("sk-ant-api03-" + "C3d4" * 10, "provider-api-key"),
            ("AKIA" + "A" * 16, "aws-access-key"),
            ("AIza" + "a" * 35, "google-api-key"),
            ("-" * 5 + "BEGIN OPENSSH PRIVATE KEY" + "-" * 5, "private-key"),
        ]
        for value, rule in cases:
            with self.subTest(rule=rule):
                self.assert_rule(value, rule)

    def test_mysql_password_forms_and_urls_are_caught(self):
        value = "S3nsitive" + "Value7"
        for command in ("mysql -u app -p" + value, "mysqldump --password=" + value,
                        "mysql --password " + value, "mysql -p'" + value + "'"):
            with self.subTest(command=command.split()[0]):
                self.assert_rule(command, "mysql-inline-password")
        self.assert_rule("mysql://app:" + value + "@db.example/test", "url-password")

    def test_secret_fields_include_yaml_json_toml_and_plain_env(self):
        value = "S3nsitive" + "Value7"
        for field in ("password", "client_secret", "api_key", "access_token", "MYSQL_PWD"):
            for separator in (": ", " = "):
                for quoted in (value, '"' + value + '"', "'" + value + "'"):
                    with self.subTest(field=field, quoted=quoted.startswith('"')):
                        self.assert_rule(field + separator + quoted, "literal-secret-field")
        self.assert_rule(json.dumps({"client_secret": value}), "literal-secret-field")
        self.assert_rule("CREATE USER 'app' IDENTIFIED" + " BY '" + value + "';", "sql-literal-password")

    def test_placeholders_variables_and_interactive_mysql_are_allowed(self):
        values = ["<new-password>", "${API_KEY}", "${{ secrets.API_KEY }}", "example-password",
                  "test-secret", "dummy-token", "your_password", "REDACTED", "********", ""]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(privacy.scan_text(json.dumps({"password": value}), "example.json", set()), [])
        for command in ("mysql" + " -h 192.0.2.1 -u app -p example_db", "mysql" + " -p\"$MYSQL_PASSWORD\"",
                        "mysql" + " --password=${MYSQL_PASSWORD}", "password = os.environ['DB_PASSWORD']"):
            self.assertEqual(privacy.scan_text(command, "example.md", set()), [])

    def test_standard_nss_database_and_code_variable_references_are_allowed(self):
        for line in ("passwd: files sss", "access_key_secret=access_key_secret",
                     "accessKeySecret: credentials.AccessKeySecret,", "amqp://guest:guest@localhost:5672//"):
            self.assertEqual(privacy.scan_text(line, "example.md", set()), [])
        self.assert_rule("amqp://guest:" + "guest@broker.example:5672//", "url-password")

    def test_slug_containing_sk_is_not_misclassified(self):
        self.assertEqual(privacy.scan_text("slug: flask-wsgi-socket-learning-notes", "example.md", set()), [])

    def test_html_highlighting_and_json_search_index_cannot_hide_credentials(self):
        sample = "S3nsitive" + "Value7"
        fragment = '<pre><span>mysql</span> <span>-p</span><span>' + sample + '</span></pre>'
        self.assert_rule(fragment, "mysql-inline-password", "index.html")
        self.assert_rule(json.dumps({"content": fragment}), "mysql-inline-password", "index.json")
        self.assert_rule("<description>" + html.escape(fragment) + "</description>", "mysql-inline-password", "index.xml")

    def test_withdrawn_line_fingerprint_ignores_indentation(self):
        line = "An internal sample identifier appears in this sentence."
        blocked = {privacy.digest(privacy.normalize_line(line).encode())}
        findings = privacy.scan_text("  " + line + "   ", "example.md", blocked)
        self.assertEqual(findings[0]["rule"], "previously-withdrawn-text")
        self.assertNotIn(line, json.dumps(findings))


class AssetPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "static/images").mkdir(parents=True)
        (self.root / "migration").mkdir()
        self.policy = empty_policy()

    def put(self, name, data=b"synthetic image bytes"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_unreferenced_image_requires_review_and_changed_bytes_invalidate_it(self):
        path = self.put("static/images/unlinked.png")
        result = privacy.check(self.root, self.policy)
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"][0]["rule"], "unreviewed-public-asset")
        privacy.review_assets(self.root, self.policy, ["static/images/unlinked.png"])
        self.assertTrue(privacy.check(self.root, self.policy)["ok"])
        path.write_bytes(b"changed image bytes")
        self.assertFalse(privacy.check(self.root, self.policy)["ok"])

    def test_renaming_binary_to_text_extension_does_not_bypass_inventory(self):
        self.put("static/leaked.txt", b"\x89PNG\r\n\x1a\nsynthetic pixels")
        self.assertEqual(privacy.check(self.root, self.policy)["findings"][0]["rule"], "unreviewed-public-asset")

    def test_review_is_explicit_and_does_not_approve_other_images(self):
        self.put("static/images/a.png")
        self.put("static/images/b.png", b"another image")
        privacy.review_assets(self.root, self.policy, ["static/images/a.png"])
        findings = privacy.check(self.root, self.policy)["findings"]
        self.assertEqual([f["path"] for f in findings], ["static/images/b.png"])

    def test_withdrawn_bytes_are_rejected_even_after_renaming(self):
        path = self.put("static/images/renamed.png")
        self.policy["blocked_files"] = [privacy.digest(path.read_bytes())]
        with self.assertRaises(privacy.PrivacyError):
            privacy.review_assets(self.root, self.policy, ["static/images/renamed.png"])
        self.assertIn("previously-withdrawn-file", {f["rule"] for f in privacy.check(self.root, self.policy)["findings"]})

    def test_site_and_valid_preview_prefixes_use_the_source_asset_inventory(self):
        self.put("static/images/a.png")
        privacy.review_assets(self.root, self.policy, ["static/images/a.png"])
        site = self.root / "output"
        for name in ("images/a.png", "previews/pr-7/images/a.png"):
            self.put("output/" + name)
        self.assertTrue(privacy.check(self.root, self.policy, site=site)["ok"])
        self.put("output/previews/pr-invalid/images/a.png")
        self.assertFalse(privacy.check(self.root, self.policy, site=site)["ok"])

    def test_transformed_image_requires_its_own_exact_review(self):
        self.put("output/avatar_hu123.png", b"transformed bytes")
        site = self.root / "output"
        self.assertFalse(privacy.check(self.root, self.policy, site=site)["ok"])
        privacy.review_assets(self.root, self.policy, ["avatar_hu123.png"], site=site)
        self.assertTrue(privacy.check(self.root, self.policy, site=site)["ok"])

    def test_marker_metadata_is_not_a_secret(self):
        self.put("output/build-info.json", json.dumps({"source_sha": "a" * 40, "run_id": "123-1", "kind": "production"}).encode())
        self.put("output/deployment-info.json", json.dumps({"schema_version": 1, "snapshot_id": "pages-snapshot-123-1"}).encode())
        self.assertTrue(privacy.check(self.root, self.policy, site=self.root / "output")["ok"])

    def test_symlinks_and_path_traversal_cannot_be_approved(self):
        target = self.put("private.png")
        (self.root / "static/images/link.png").symlink_to(target)
        self.assertEqual(privacy.check(self.root, self.policy)["findings"][0]["rule"], "public-symlink")
        for name in ("static/images/link.png", "../private.png", "/private.png"):
            with self.subTest(name=name), self.assertRaises(privacy.PrivacyError):
                privacy.review_assets(self.root, self.policy, [name])

    def test_git_inventory_checks_tracked_dotfiles_but_not_ignored_local_config(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.put(".gitignore", b".env\n.obsidian-vault.json\n")
        sample = ("password" + "=S3nsitive" + "Value7").encode()
        self.put(".obsidian-vault.json", sample)
        self.put(".env", sample)
        self.assertTrue(privacy.check(self.root, self.policy)["ok"])
        subprocess.run(["git", "-C", str(self.root), "add", "-f", ".env"], check=True)
        findings = privacy.check(self.root, self.policy)["findings"]
        self.assertEqual([f["path"] for f in findings], [".env"])

    def test_archive_contents_are_scanned_after_binary_approval(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("settings.txt", "password" + "=S3nsitive" + "Value7")
        self.put("static/downloads/sample.zip", buffer.getvalue())
        privacy.review_assets(self.root, self.policy, ["static/downloads/sample.zip"])
        findings = privacy.check(self.root, self.policy)["findings"]
        self.assertIn("literal-secret-field", {f["rule"] for f in findings})
        self.assertTrue(any("!settings.txt" in f["path"] for f in findings))

    def test_cli_check_returns_nonzero_without_echoing_sensitive_values(self):
        value = "S3nsitive" + "Value7"
        self.put("content/post/example.md", ("password" + ": " + value).encode())
        path = self.root / "migration/public-privacy-policy.json"
        privacy.save_policy(path, self.policy)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = privacy.main(["check", "--root", str(self.root)])
        self.assertEqual(code, 1)
        self.assertNotIn(value, stream.getvalue())
        self.assertEqual(json.loads(stream.getvalue())["findings"][0]["path"], "content/post/example.md")

    def test_failed_explicit_review_does_not_partially_save_policy(self):
        self.put("static/images/a.png")
        path = self.root / "migration/public-privacy-policy.json"
        privacy.save_policy(path, self.policy)
        before = path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            code = privacy.main(["review-images", "--root", str(self.root), "--paths", "static/images/a.png", "static/images/missing.png"])
        self.assertEqual(code, 1)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
