"""Regression checks for destructive/bulk migration boundaries."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_notes.py"
SPEC = importlib.util.spec_from_file_location("migrate_notes", SCRIPT)
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "notes"
        self.blog = self.root / "blog"
        self.source.mkdir()
        self.blog.mkdir()

    def write(self, root, name, text):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def entry(self, name="note.md", target="content/post/test/note.md", **options):
        return {"sources": [name], "target": target, "action": "migrate", "title": "测试", "category": "test", "date": "2020-01-02T00:00:00+08:00", **options}

    def run_manifest(self, entries, apply=False):
        return migration.migrate({"version": 1, "entries": entries}, [self.source], self.blog, apply)

    def test_dry_run_has_no_source_or_blog_changes(self):
        note = self.write(self.source, "note.md", "正文 ![图](photo.png)\n")
        self.write(self.source, "photo.png", "image-bytes")
        before = {p.relative_to(self.source): p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        report = self.run_manifest([self.entry()])
        self.assertEqual(report["summary"], {"planned": 1})
        self.assertEqual(list(self.blog.iterdir()), [])
        self.assertEqual(before, {p.relative_to(self.source): p.read_bytes() for p in self.source.rglob("*") if p.is_file()})
        self.assertEqual(note.read_text(), "正文 ![图](photo.png)\n")

    def test_duplicate_image_content_shared_across_articles(self):
        self.write(self.source, "one.md", "![](a/pic.png)")
        self.write(self.source, "two.md", "![](b/different-name.png)")
        self.write(self.source, "a/pic.png", "same")
        self.write(self.source, "b/different-name.png", "same")
        report = self.run_manifest([self.entry("one.md", "content/post/one.md"), self.entry("two.md", "content/post/two.md")], True)
        self.assertEqual(report["summary"], {"migrated": 2})
        self.assertEqual(report["images_copied"], 1)
        self.assertEqual(len(list((self.blog / "static/images").iterdir())), 1)
        self.assertIn("/images/pic.png", (self.blog / "content/post/two.md").read_text())

    def test_same_basename_different_content_never_overwrites(self):
        self.write(self.source, "note.md", "![](a/pic.png)\n![](b/pic.png)\n")
        self.write(self.source, "a/pic.png", "one")
        self.write(self.source, "b/pic.png", "two")
        self.write(self.blog, "static/images/pic.png", "existing")
        report = self.run_manifest([self.entry()], True)
        self.assertEqual(report["images_copied"], 2)
        self.assertEqual((self.blog / "static/images/pic.png").read_text(), "existing")
        images = list((self.blog / "static/images").glob("pic-*.png"))
        self.assertEqual({p.read_text() for p in images}, {"one", "two"})

    def test_unicode_spaces_parentheses_and_reference_image(self):
        self.write(self.source, "note.md", '![图](<图片/截图 (完成).png> "title")\n![重复][shot]\n[shot]: 图片/截图%20(完成).png "caption"\n')
        self.write(self.source, "图片/截图 (完成).png", "same")
        report = self.run_manifest([self.entry()], True)
        article = (self.blog / "content/post/test/note.md").read_text()
        self.assertEqual(report["images_copied"], 1)
        self.assertNotIn("图片/", article)
        self.assertIn('"title"', article)
        self.assertIn('"caption"', article)
        self.assertEqual(migration.audit(self.blog)["summary"]["missing_images"], 0)

    def test_wiki_and_html_images_convert_without_code_rewrite(self):
        original = '![[photo.png|300]]\n<img src="photo.png" alt="说明" width="300">\n<img src="https://example.com/a.png" alt="远程">\n`![](missing.png)`\n```markdown\n![](missing.png)\n```\n~~~\n![[missing.png]]\n~~~\n    ![](missing.png)\n'
        self.write(self.source, "note.md", original)
        self.write(self.source, "photo.png", "bytes")
        report = self.run_manifest([self.entry()], True)
        self.assertEqual(report["missing_images"], 0)
        article = (self.blog / "content/post/test/note.md").read_text()
        self.assertIn("![](/images/photo.png)", article)
        self.assertIn("![说明](/images/photo.png)", article)
        self.assertIn("![远程](https://example.com/a.png)", article)
        self.assertIn("`![](missing.png)`", article)
        self.assertIn("```markdown\n![](missing.png)\n```", article)
        self.assertIn("~~~\n![[missing.png]]\n~~~", article)
        self.assertIn("    ![](missing.png)", article)

    def test_missing_image_blocks_entire_article_without_copying_found_asset(self):
        self.write(self.source, "note.md", "![](good.png)\n![](missing.png)\n")
        self.write(self.source, "good.png", "good")
        report = self.run_manifest([self.entry()], True)
        self.assertEqual(report["summary"], {"blocked_missing_images": 1})
        self.assertEqual(list(self.blog.iterdir()), [])

    def test_existing_article_never_overwritten(self):
        self.write(self.source, "note.md", "new")
        target = self.write(self.blog, "content/post/test/note.md", "existing")
        report = self.run_manifest([self.entry()], True)
        self.assertEqual(report["summary"], {"target_exists": 1})
        self.assertEqual(target.read_text(), "existing")

    def test_front_matter_preserved_and_empty_cover_image_ignored(self):
        original = '---\ntitle: Original\ndate: 2018-01-01\ndraft: true\nimage: \ncategories: [original]\n---\n\n正文\n'
        self.write(self.source, "note.md", original)
        report = self.run_manifest([self.entry()], True)
        self.assertEqual(report["summary"], {"migrated": 1})
        article = (self.blog / "content/post/test/note.md").read_text()
        self.assertIn("title: Original", article)
        self.assertIn("date: 2018-01-01", article)
        self.assertIn("draft: true", article)
        self.assertIn('slug: "note"', article)
        self.assertEqual(migration.audit(self.blog)["summary"]["missing_images"], 0)

    def test_description_is_omitted_unless_explicitly_provided(self):
        source = self.write(self.source, "note.md", "正文摘要\n")
        default = migration.add_front_matter(source.read_text(), source, self.entry())
        self.assertNotIn("description:", default)
        explicit = migration.add_front_matter(source.read_text(), source, self.entry(description='手写摘要，含 "引号"。'))
        self.assertIn('description: "手写摘要，含 \\"引号\\"。"', explicit)

    def test_partial_front_matter_gains_hugo_fields_without_losing_tags(self):
        source = self.write(self.source, "note.md", "---\ntitle: Original\ntags: [python]\n---\n\n正文\n")
        rendered = migration.add_front_matter(source.read_text(), source, self.entry(date="2020-01-02T03:04:05+08:00"))
        self.assertIn("title: Original", rendered)
        self.assertIn("tags: [python]", rendered)
        self.assertIn('date: "2020-01-02T03:04:05+08:00"', rendered)
        self.assertIn('lastmod: "2020-01-02T03:04:05+08:00"', rendered)
        self.assertIn("categories:", rendered)
        self.assertIn("draft: false", rendered)
        self.assertTrue(rendered.endswith("\n正文\n"))

    def test_source_sha_and_reviewed_line_edits(self):
        source = self.write(self.source, "note.md", "# title\nprivate material\n![](missing.png)\nlast line\n")
        original = source.read_bytes()
        entry = self.entry(source_sha256=hashlib.sha256(original).hexdigest(), text_edits=[{"start_line": 2, "end_line": 3, "replacement": "Public example."}])
        report = self.run_manifest([entry], True)
        article = (self.blog / "content/post/test/note.md").read_text()
        self.assertEqual(report["summary"], {"migrated": 1})
        self.assertNotIn("private material", article)
        self.assertIn("Public example.\nlast line", article)
        self.assertEqual(source.read_bytes(), original)

    def test_sha_mismatch_and_invalid_edits_write_nothing(self):
        self.write(self.source, "note.md", "1\n2\n3\n")
        entry = self.entry(source_sha256="0" * 64)
        self.assertEqual(self.run_manifest([entry], True)["summary"], {"error": 1})
        for edits in ([{"start_line": 1, "end_line": 2, "replacement": "a"}, {"start_line": 2, "end_line": 3, "replacement": "b"}], [{"start_line": 4, "end_line": 4, "replacement": "a"}]):
            entry = self.entry(text_edits=edits)
            self.assertEqual(self.run_manifest([entry], True)["summary"], {"error": 1})
        self.assertEqual(list(self.blog.iterdir()), [])

    def test_private_and_unknown_note_links_become_text(self):
        self.write(self.source, "note.md", '[[private|私密]]\n[秘密](private.md "caption")\n[[missing]]\n')
        self.write(self.source, "private.md", "private")
        report = self.run_manifest([self.entry(), {"sources": ["private.md"], "action": "exclude", "reason": "private"}], True)
        self.assertEqual(report["missing_links"], 3)
        article = (self.blog / "content/post/test/note.md").read_text()
        self.assertIn("私密\n秘密\nmissing\n", article)
        self.assertNotIn("private.md", article)
        self.assertNotIn("caption", article)

    def test_public_note_links_use_manifest_relref(self):
        self.write(self.source, "note.md", "[[two#Heading|下一篇]]\n[two](two.md)\n[[#Local Heading]]\n")
        self.write(self.source, "two.md", "## Heading\n")
        report = self.run_manifest([self.entry(), self.entry("two.md", "content/post/two.md")], True)
        self.assertEqual(report["summary"], {"migrated": 2})
        article = (self.blog / "content/post/test/note.md").read_text()
        self.assertIn('[下一篇]({{< relref "post/two.md#heading" >}})', article)
        self.assertIn('[Local Heading]({{< relref "post/test/note.md#local-heading" >}})', article)

    def test_dependency_on_blocked_article_propagates(self):
        self.write(self.source, "one.md", "[[two]]")
        self.write(self.source, "two.md", "[[three]]")
        self.write(self.source, "three.md", "![](missing.png)")
        entries = [self.entry(name + ".md", "content/post/" + name + ".md") for name in ("one", "two", "three")]
        report = self.run_manifest(entries, True)
        self.assertEqual(report["summary"], {"blocked_missing_links": 2, "blocked_missing_images": 1})
        self.assertEqual(list(self.blog.iterdir()), [])

    def test_covered_source_can_depend_on_article_created_in_same_batch(self):
        self.write(self.source, "note.md", "public note")
        self.write(self.source, "mirror.md", "mirrored note")
        target = "content/post/test/note.md"
        entries = [self.entry("mirror.md", target, action="covered"), self.entry()]
        self.assertEqual(self.run_manifest(entries, False)["summary"], {"covered": 1, "planned": 1})
        self.assertEqual(list(self.blog.iterdir()), [])
        self.assertEqual(self.run_manifest(entries, True)["summary"], {"covered": 1, "migrated": 1})

        self.write(self.source, "blocked.md", "![](missing.png)")
        blocked = "content/post/test/blocked.md"
        entries = [self.entry("mirror.md", blocked, action="covered"), self.entry("blocked.md", blocked)]
        self.assertEqual(self.run_manifest(entries, True)["summary"], {"missing_covered_target": 1, "blocked_missing_images": 1})
        self.assertFalse((self.blog / blocked).exists())

    def test_hidden_configuration_and_non_image_assets_are_rejected(self):
        self.write(self.source, "note.md", "![](.secret/key.png)\n![](configuration.json)\n")
        self.write(self.source, ".secret/key.png", "secret")
        self.write(self.source, "configuration.json", "secret")
        report = self.run_manifest([self.entry()], True)
        self.assertEqual(report["missing_images"], 2)
        self.assertEqual(list(self.blog.iterdir()), [])

    def test_targets_outside_content_rejected_before_any_write(self):
        self.write(self.source, "note.md", "note")
        with self.assertRaises(ValueError):
            self.run_manifest([self.entry(target="../outside.md")], True)
        self.assertEqual(list(self.blog.iterdir()), [])

    def test_cli_report_and_missing_status(self):
        self.write(self.source, "note.md", "![](missing.png)")
        manifest = self.write(self.root, "manifest.json", json.dumps({"version": 1, "entries": [self.entry()]}))
        report_file = self.root / "report.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = migration.main(["--source", str(self.source), "--blog", str(self.blog), "--manifest", str(manifest), "--report", str(report_file)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(report_file.read_text())["missing_images"], 1)
        self.assertEqual(list(self.blog.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
