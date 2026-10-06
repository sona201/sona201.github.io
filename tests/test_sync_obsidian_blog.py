import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("sync_obsidian_blog", SCRIPTS / "sync_obsidian_blog.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class PublicExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.vault = self.root / "vault"
        self.blog = self.root / "blog"
        self.vault.mkdir()
        self.blog.mkdir()
        self.manifest = self.blog / "published.json"
        environment = mock.patch.dict(sync.os.environ, {"OBSIDIAN_VAULT": ""})
        environment.start()
        self.addCleanup(environment.stop)

    def put(self, root, relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def mappings(self, entries):
        self.manifest.write_text(json.dumps({"version": 1, "entries": entries}), encoding="utf-8")

    def entry(self, name="sample", folder="博客"):
        return {"source": f"{folder}/python/{name}.md", "target": f"content/post/python/{name}.md"}

    def plan(self):
        return sync.plan_export(self.vault, self.blog, self.manifest)

    def test_only_whitelisted_notes_and_referenced_public_images_are_exported(self):
        entry = self.entry()
        self.mappings([entry])
        self.put(self.vault, entry["source"], '---\ntitle: Public\ndraft: false\nimage: ../../附件/博客/images/cover.png\n---\n![图](../../附件/博客/images/one.png)\n')
        self.put(self.vault, "博客/unlisted.md", "---\ndraft: false\n---\nNot approved\n")
        self.put(self.vault, "私人笔记/passwords.md", "---\nprivate: true\n---\nPrivate note\n")
        self.put(self.vault, "附件/博客/images/cover.png", "cover")
        self.put(self.vault, "附件/博客/images/one.png", "one")
        self.put(self.vault, "附件/博客/images/unreferenced.png", "unreferenced")
        report, notes, images = self.plan()
        self.assertEqual(report["summary"]["articles"], 1)
        self.assertEqual(report["summary"]["new_images"], 2)
        self.assertIn("image: /images/cover.png", notes[0][1].decode())
        self.assertIn("![图](/images/one.png)", notes[0][1].decode())
        self.assertFalse((self.blog / entry["target"]).exists(), "check must never write")
        for target, data in images + notes:
            sync.atomic_write(target, data)
        self.assertTrue((self.blog / "static/images/one.png").is_file())
        self.assertFalse((self.blog / "static/images/unreferenced.png").exists())
        self.assertEqual(sync.audit_public(self.blog)["summary"]["errors"], 0)

    def test_private_publication_flags_are_rejected_before_any_write(self):
        for flag in ("draft: true", "private: true", "publish: false", "published: false"):
            with self.subTest(flag=flag):
                entry = self.entry()
                self.mappings([entry])
                self.put(self.vault, entry["source"], f"---\n{flag}\n---\nSensitive\n")
                with self.assertRaises(ValueError):
                    self.plan()
                self.assertFalse((self.blog / entry["target"]).exists())

    def test_unsupported_metadata_cannot_bypass_publication_flags(self):
        for text in ('{"title":"Private", "draft":true}\nBody', "---\nprivate: !!bool true\n---\nBody", "---\n{private: true, title: Private}\n---\nBody", "---\nparams: {private: true}\n---\nBody"):
            with self.subTest(text=text):
                entry = self.entry()
                self.mappings([entry])
                self.put(self.vault, entry["source"], text)
                with self.assertRaises(ValueError):
                    self.plan()

    def test_quoted_yaml_and_toml_keys_cannot_bypass_private_flags(self):
        for delimiter, field in (("---", "'private': true"), ("---", '"draft": true'), ("---", '"publish": false'), ("+++", '"private" = true'), ("+++", "'published' = false"), ("---", '"pri\\u0076ate": true')):
            with self.subTest(field=field):
                entry = self.entry()
                self.mappings([entry])
                self.put(self.vault, entry["source"], f"{delimiter}\n{field}\n{delimiter}\nPrivate\n")
                with self.assertRaises(ValueError):
                    self.plan()
                self.put(self.blog, entry["target"], f"{delimiter}\n{field}\n{delimiter}\nPrivate\n")
                self.assertEqual(sync.audit_public(self.blog)["summary"]["errors"], 1)

    def test_quoted_public_keys_and_braces_in_descriptions_remain_valid(self):
        text = '---\n"draft": false\n\'private\': false\ndescription: "Object { private: true }"\n---\nPublic\n'
        sync.check_public(text)

    def test_late_private_entry_prevents_all_apply_writes(self):
        first, last = self.entry("first"), self.entry("last")
        self.mappings([first, last])
        self.put(self.vault, first["source"], "---\ndraft: false\n---\n![图](../../附件/博客/images/one.png)\n")
        self.put(self.vault, "附件/博客/images/one.png", "public image")
        self.put(self.vault, last["source"], "---\nprivate: true\n---\nPrivate\n")
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            code = sync.main(["--blog", str(self.blog), "--vault", str(self.vault), "--manifest", str(self.manifest), "--apply"])
        self.assertEqual(code, 1)
        self.assertFalse((self.blog / first["target"]).exists())
        self.assertFalse((self.blog / "static/images/one.png").exists())

    def test_manuscripts_cannot_come_from_private_directories_or_traversal(self):
        for source in ("私人笔记/secret.md", "博客/../secret.md", "/博客/sample.md"):
            with self.subTest(source=source):
                self.mappings([{"source": source, "target": "content/post/sample.md"}])
                with self.assertRaises(ValueError):
                    self.plan()

    def test_a_public_note_cannot_export_an_attachment_from_other_notes(self):
        entry = self.entry()
        self.mappings([entry])
        self.put(self.vault, entry["source"], "---\ndraft: false\n---\n![私图](../../附件/私人.png)\n")
        self.put(self.vault, "附件/私人.png", "private image")
        with self.assertRaisesRegex(ValueError, "public attachment"):
            self.plan()

    def test_image_filename_case_is_checked_in_vault_and_blog(self):
        entry = self.entry()
        self.mappings([entry])
        self.put(self.vault, entry["source"], "---\ndraft: false\n---\n![图](../../附件/博客/images/One.png)\n")
        self.put(self.vault, "附件/博客/images/one.png", "image")
        with self.assertRaisesRegex(ValueError, "case"):
            self.plan()
        self.put(self.blog, entry["target"], "---\ndraft: false\n---\n![图](/images/One.png)\n")
        self.put(self.blog, "static/images/one.png", "image")
        self.assertEqual(sync.audit_public(self.blog)["summary"]["errors"], 1)

    def test_conflicting_images_and_manifest_outputs_are_rejected(self):
        entry = self.entry()
        self.mappings([entry])
        self.put(self.vault, entry["source"], "---\ndraft: false\n---\n![图](../../附件/博客/images/one.png)\n")
        self.put(self.vault, "附件/博客/images/one.png", "new")
        self.put(self.blog, "static/images/one.png", "old")
        with self.assertRaisesRegex(ValueError, "different content"):
            self.plan()
        self.mappings([entry, entry])
        self.put(self.vault, entry["source"], "---\ndraft: false\n---\nPublic\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.plan()

    def test_symlink_manuscripts_and_images_are_rejected(self):
        entry = self.entry()
        self.mappings([entry])
        outside = self.put(self.root, "outside.md", "---\ndraft: false\n---\nOutside\n")
        source = self.vault / entry["source"]
        source.parent.mkdir(parents=True)
        source.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            self.plan()
        source.unlink()
        self.put(self.vault, entry["source"], "---\ndraft: false\n---\n![图](../../附件/博客/images/one.png)\n")
        image = self.vault / "附件/博客/images/one.png"
        image.parent.mkdir(parents=True)
        image.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            self.plan()

    def test_html_wiki_and_external_images_keep_the_expected_syntax(self):
        entry = self.entry()
        self.mappings([entry])
        self.put(self.vault, entry["source"], '---\ndraft: false\n---\n<img width="100" src="../../附件/博客/images/one.png" alt="图">\n![[../../附件/博客/images/one.png|别名]]\n![外部](https://example.com/image.png)\n<img src="https://example.com/other.png" alt="外图 &amp; 标题">\n')
        self.put(self.vault, "附件/博客/images/one.png", "image")
        _, notes, _ = self.plan()
        text = notes[0][1].decode()
        self.assertIn('![图](/images/one.png)', text)
        self.assertNotIn("<img", text)
        self.assertIn("![别名](/images/one.png)", text)
        self.assertIn("https://example.com/image.png", text)
        self.assertIn("![外图 & 标题](https://example.com/other.png)", text)

    def test_private_note_links_and_embeds_cannot_leave_the_vault(self):
        for body in ("[[私人笔记/secret]]", "![[私人笔记/secret.md]]", "[笔记](../../私人笔记/secret.md)", "[笔记](../secret.txt#section)", "[笔记][private]\n\n[private]: ../../私人笔记/secret.md"):
            with self.subTest(body=body):
                entry = self.entry()
                self.mappings([entry])
                self.put(self.vault, entry["source"], f"---\ndraft: false\n---\n{body}\n")
                with self.assertRaisesRegex(ValueError, "public blog URLs"):
                    self.plan()

    def test_external_anchor_and_code_example_links_remain_valid(self):
        entry = self.entry()
        self.mappings([entry])
        body = '[公开](https://example.com/public.md)\n[章节](#section)\n[文章](/posts/public/)\n`[[代码示例]]`\n```markdown\n![[私人笔记/example.md]]\n[示例](../example.txt)\n```\n'
        self.put(self.vault, entry["source"], "---\ndraft: false\n---\n" + body)
        _, notes, _ = self.plan()
        self.assertIn(body, notes[0][1].decode())

    def test_public_audit_includes_pages_and_rejects_source_note_links(self):
        self.put(self.blog, "content/page/about/index.md", "---\nprivate: true\n---\nPrivate\n")
        self.put(self.blog, "content/page/links/index.md", "---\ntitle: Links\n---\n[[私人笔记/secret]]\n")
        self.put(self.blog, "content/page/search/index.md", "---\ntitle: Search\n---\n[笔记](../secret.txt)\n")
        self.put(self.blog, "content/post/sample.md", "---\ndraft: false\n---\n[公开](https://example.com/public.md)\n[章节](#section)\n")
        self.put(self.blog, "content/_index.md", "---\nprivate: true\n---\nIndex deliberately outside this audit\n")
        report = sync.audit_public(self.blog)
        self.assertEqual(report["summary"], {"articles": 4, "errors": 3})
        self.assertEqual({r["article"] for r in report["errors"]}, {"content/page/about/index.md", "content/page/links/index.md", "content/page/search/index.md"})

    def test_configuring_once_allows_check_and_apply_without_vault_argument(self):
        entry = self.entry()
        self.mappings([entry])
        self.put(self.vault, entry["source"], "---\ndraft: false\n---\nPublic\n")
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync.main(["--blog", str(self.blog), "--set-vault", str(self.vault)]), 0)
            self.assertEqual(sync.main(["--blog", str(self.blog), "--manifest", str(self.manifest), "--check"]), 0)
        self.assertFalse((self.blog / entry["target"]).exists())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync.main(["--blog", str(self.blog), "--manifest", str(self.manifest), "--apply"]), 0)
        self.assertTrue((self.blog / entry["target"]).is_file())
        config = json.loads((self.blog / sync.VAULT_CONFIG).read_text())
        self.assertEqual(config["vault"], str(self.vault.resolve()))

    def test_explicit_vault_and_environment_override_local_configuration(self):
        other = self.root / "other-vault"
        other.mkdir()
        sync.configure_vault(self.blog, self.vault)
        self.assertEqual(sync.configured_vault(self.blog), self.vault.resolve())
        with mock.patch.dict(sync.os.environ, {"OBSIDIAN_VAULT": str(other)}):
            self.assertEqual(sync.configured_vault(self.blog), other.resolve())
            self.assertEqual(sync.configured_vault(self.blog, self.vault), self.vault.resolve())

    def test_missing_configuration_never_falls_back_to_a_neighboring_vault(self):
        (self.blog.parent / "ObsidianDoc").mkdir()
        with self.assertRaisesRegex(ValueError, "Configure the vault once"):
            sync.configured_vault(self.blog)


if __name__ == "__main__":
    unittest.main()
