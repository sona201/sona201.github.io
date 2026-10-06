# 经过审阅的笔记迁移

`migrate_notes.py` 仅执行显式 JSON 清单，**不会自动把源仓库全部公开**。先逐篇确认文章是否适合公开，排除个人资料、内部工作记录、草稿和未获授权转载，然后运行 dry-run，检查报告后 apply。源仓库只读，生成文件保存在博客仓库。

```sh
python3 scripts/migrate_notes.py \
  --source /path/to/noteDoc --source /path/to/ObsidianDoc \
  --blog /path/to/blogs --manifest /path/to/reviewed-manifest.json \
  --dry-run --report /tmp/migration-plan.json

python3 scripts/migrate_notes.py \
  --source /path/to/noteDoc --source /path/to/ObsidianDoc \
  --blog /path/to/blogs --manifest /path/to/reviewed-manifest.json \
  --apply --report /tmp/migration-result.json

python3 scripts/migrate_notes.py --blog /path/to/blogs \
  --audit --report /tmp/image-audit.json

python3 -m unittest discover -s tests -v
```

不指定 `--apply` 时默认 dry-run。dry-run 不创建文章或图片；显式 `--report` 仍会保存报告。`--audit` 只扫描 `content/` 图片及残留 Obsidian 链接，不修改正文。

## 清单格式

```json
{
  "version": 1,
  "entries": [
    {
      "sources": ["noteDoc/linux/example.md"],
      "target": "content/post/Linux/linux-example.md",
      "action": "migrate",
      "title": "Linux 示例",
      "category": ["Linux"],
      "date": "2021-03-04T12:00:00+08:00",
      "source_sha256": "源文件完整内容的 SHA256，可选",
      "reason": "个人原创技术笔记，已经检查公开范围",
      "text_edits": [
        {"start_line": 8, "end_line": 9, "replacement": "公开示例使用 example.com。\n"}
      ]
    },
    {
      "sources": ["ObsidianDoc/already-published.md"],
      "target": "content/post/tools/existing.md",
      "action": "covered",
      "reason": "已有博客内容覆盖"
    },
    {
      "sources": ["noteDoc/private.md"],
      "action": "exclude",
      "reason": "不适合公开"
    }
  ]
}
```

- `sources` 必须为非空数组，每项为允许 `--source` 根目录内的绝对路径，或能在这些根目录唯一解析的相对路径。也支持 `noteDoc/foo.md` 这种带根目录名的路径。仅 `.md` / `.txt` 非隐藏文件可作为文章来源。
- `migrate` 选择 `sources[0]` 正文，其余来源用于重复主题和内部链接映射。`target` 必须为 `content/` 内的 Markdown 路径，现有目标绝不覆盖。请为全站选择唯一且稳定的文件名；默认 `slug` 为目标文件名，也可显式指定 `slug`。
- `covered` / `exclude` 只记录状态，不写内容；`covered` 要求目标已存在。`merge` 标记 `needs_manual_merge`，必须人工合并，不自动覆盖已有文章。
- `covered` 也可指向本批成功规划的新文章；若该目标因为缺图等原因无法生成，会报告 `missing_covered_target`。
- 已有 YAML/TOML Front Matter 的字段保留，缺失的 `title`、`date`、`lastmod`、`categories`、`slug`、`draft` 会补齐。无 Front Matter 时生成这些 Hugo 字段，默认 `draft: false`。清单可提供字符串 `description` 作为摘要；未提供时省略该字段，让 Hugo 自动生成摘要。日期优先保留已有日期，再使用清单 `date`、源文件 Git 首次提交日期、文件 mtime（UTC）。
- `text_edits` 按**原文件** 1-based、包含两端的行号执行，倒序替换，拒绝重叠或越界。`replacement` 保存经过审阅的公共内容，不要把被删除的敏感原文写入清单。`source_sha256` 验证原始文件字节未发生变化；推荐所有带行号编辑的条目均提供它。
- 本地 Markdown 图片、引用式图片、HTML `<img>`、Obsidian 图片嵌入，以及 Front Matter `image` 会迁到 `static/images/`，正文使用 `/images/`。按 SHA256 内容去重，文件名冲突加摘要后缀，绝不覆盖旧图片。为匹配 Hugo 当前渲染设置，HTML `<img>` 会转成 Markdown 图片；尺寸样式不保留。外部图片 URL 保留，不下载。
- 内部 `.md` / `.txt` 链接与 Obsidian 链接按完整清单改为 Hugo `relref`；笔记嵌入转成链接。未列入公开映射的笔记链接转成普通文字并报告，避免公开内部路径或产生无效链接。Obsidian 图片尺寸别名不保留；复杂 Markdown/HTML、不支持的嵌入格式请在迁移后人工检查。
- 缺失图片阻止对应整篇迁移，也不会先复制该篇的部分图片。指向本批被阻止文章的链接会阻止依赖文章，避免生成无效 `relref`。缺失普通内部链接、待人工合并等会返回非零退出码，请阅读报告逐项处理。

报告中的 `summary` 按文章状态计数，`entries` 保留每项审阅原因、图片来源与目标、缺失链接和错误。`target_exists` 表示已经存在且保持原样，便于重复执行；要合并差异请改清单为 `merge` 后人工处理。

## 当前笔记主库与博客同步

原始迁移清单与完整审计已归档到笔记主库的 `管理/迁移记录`。这些记录包含未公开笔记的信息，保存在私人笔记库。

首次使用时，在博客仓库配置一次笔记主库路径：

```sh
python3 scripts/sync_obsidian_blog.py --set-vault /path/to/vault
```

实际路径只保存在被 Git 忽略的 `.obsidian-vault.json`，不会写入公开清单或 README。主库移动后重新配置。可选环境变量 `OBSIDIAN_VAULT` 和命令行 `--vault` 均可覆盖配置，优先级为 `--vault`、`OBSIDIAN_VAULT`、本地配置。工具不会默认寻找相邻目录。

日常编辑主库的 `博客` 目录，随后更新公开稿：

```sh
python3 scripts/sync_obsidian_blog.py --check
python3 scripts/sync_obsidian_blog.py --apply
python3 scripts/sync_obsidian_blog.py --audit-public
```

不指定模式时默认检查。`--check` 检查所有映射和附件后给出计划，`--apply` 在整批规划成功后更新公开稿，`--audit-public` 只检查博客现有文件，无需访问笔记库。`--report /tmp/public-sync.json` 可保存检查结果。

`migration/published-manifest.json` 只记录已审阅的公开稿映射：

```json
{
  "version": 1,
  "entries": [
    {"source": "博客/python/example.md", "target": "content/post/python/example.md"}
  ]
}
```

来源只能位于主库 `博客` 目录，目标必须位于 `content/post`。工具不扫描全部笔记；`draft: true`、`private: true`、`publish: false` 会阻止同步。只复制稿件引用的 `附件/博客/images` 图片，其他笔记附件不会进入博客。图片缺失、大小写不匹配、同名内容冲突会阻止同步；更新已有图片需单独审阅。

私人笔记链接和嵌入应在公开稿中改为公开博客 URL，再执行同步。草稿放在主库的 `私人笔记`，不加入发布清单。要撤稿，移除映射并删除博客文件，再用 `hugo --cleanDestinationDir` 构建，避免保留旧 HTML。

`migrate_notes.py` 保留用于显式清单的一次性导入；它不覆盖已有博客稿。后续新增公开稿和更新正文使用上述同步工具。
