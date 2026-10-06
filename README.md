# Ricardo 博客

站点：[sona201.github.io](https://sona201.github.io)

笔记主库的本地路径通过配置指定。在 Obsidian 中打开主库，从 `笔记首页.md` 查看全部笔记、主题目录、公开稿和私人草稿。旧 `noteDoc` 已导入主库的 `归档/noteDoc`，原目录保留。

本仓库只保存网站稿件、主题和构建工具。私人笔记与草稿保存在 Obsidian 主库；完整迁移记录也保存在主库的 `管理/迁移记录`。

## 从笔记同步公开稿

首次使用时，在本目录配置一次主库路径，将下面的路径替换为实际目录：

```sh
python3 scripts/sync_obsidian_blog.py --set-vault /path/to/vault
```

路径保存在本仓库的 `.obsidian-vault.json`，该文件已被 Git 忽略。移动笔记库后重新运行这条配置命令。也可以使用环境变量 `OBSIDIAN_VAULT`，或通过 `--vault` 临时指定；优先级为 `--vault`、环境变量、本地配置。

日常编辑主库 `博客` 目录中的主稿，然后在本目录执行：

```sh
python3 scripts/sync_obsidian_blog.py --check
python3 scripts/sync_obsidian_blog.py --apply
python3 scripts/sync_obsidian_blog.py --audit-public
hugo server --bind 127.0.0.1
```

打开 [本地预览](http://127.0.0.1:1313/)。正式构建使用 `hugo --cleanDestinationDir`。

只有 `migration/published-manifest.json` 明确列出的 `博客/*.md` 稿件会同步；私人标记和草稿会阻止同步。图片只能来自主库的 `附件/博客/images`，只复制被公开稿引用的图片。新增文章需要先审阅正文及图片，设 `draft: false`，再添加一条发布映射：

```json
{"source": "博客/python/example.md", "target": "content/post/python/example.md"}
```

发布清单是唯一的导出入口；把私人笔记改成 `draft: false` 不会自动发布。同步会更新清单中的博客稿件，修改正文前请先确认编辑的是 Obsidian 主稿。

撤下文章时，把主稿移到 Obsidian 的 `私人笔记`，移除发布映射，并删除本仓库的对应文章，再重新构建发布。删除文件不会清除已有 Git 提交中的旧内容。

## 仓库可见性与部署

当前工作流在 `blogs` 中构建 Hugo，将 `public` 推送到独立的公开仓库 `sona201/sona201.github.io` 的 `master` 分支。`blogs` 可以改为私有，仍通过这个公开仓库提供博客页面。需要保持 GitHub Actions 可运行，且 `PERSONAL_TOKEN` 对目标仓库仍有写入权限。

Obsidian 主库含个人笔记和未发布原稿，应使用私有仓库。推送 `blogs` 会触发部署；仅在本地同步和预览不会发布。
