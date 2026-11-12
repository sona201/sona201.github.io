# Ricardo 博客

站点：[sona201.github.io](https://sona201.github.io/)

这是独立的 Hugo 博客源码仓库，也是 Obsidian 的“博客库”。`content/` 是博客文章的唯一主稿，直接在这里写作并推送本仓库。`ObsidianDoc` 是另一个私有笔记库，只保存私人笔记和草稿，不参与博客部署。

## 日常写作

用 Obsidian 的 **Open folder as vault** 打开本仓库根目录。在 `content/post/` 编辑文章；没有导出、同步、发布映射或跨仓库路径配置。正文使用标准 Markdown，文章属性使用 Hugo front matter。写作约定见 [AGENTS.md](AGENTS.md)。

日常只需：编辑 → Git 提交 → 推送 `main`。GitHub Actions 的 **Build and deploy** 自动构建并更新网站。Obsidian 不会因为保存文件就自动提交 Git，可以继续使用你习惯的 Git 客户端。

新文章可直接创建 Markdown 并填写 front matter，或者安装与 `.hugo-version` 一致的 Hugo extended 后运行：

```sh
hugo new content post/think/my-article/index.md
```

建议新文章采用 Hugo 原生 page bundle：

```text
content/post/think/my-article/
├── index.md
└── photo.jpg
```

正文使用 `![图片说明](photo.jpg)`，Obsidian 与 Hugo 都可以读取相对路径图片。仓库已设置 Obsidian 使用 Markdown 链接、将新附件放在当前笔记旁。旧文章的 `/images/...` 仍由 `static/images/` 提供，保持原网址；这种网站根路径的图片请用 Hugo 本地预览确认，不依赖 Obsidian 内置预览。

`draft: true` 是 Hugo 的未发布草稿；完成后改为 `draft: false`。**本仓库是公开的，即使草稿不出现在网站，提交到 Git 后仍能被读取。** 私人笔记和不宜公开的草稿留在 ObsidianDoc，审阅后再迁入博客库。

图片和下载文件沿用已有隐私检查。人工检查内容后，记录审阅指纹，例如：

```sh
python3 scripts/public_privacy.py review-images --paths content/post/think/my-article/photo.jpg
```

若主题生成了新尺寸图片，构建检查会列出需要审阅的产物路径；检查后使用 `review-images --site public --paths <产物相对路径>` 记录。文本隐私扫描、已撤下内容指纹和图片审阅是本仓库额外的保护检查，不是 Hugo 的必需配置；它们不负责同步文章。

撤稿时删除 `content/` 中对应文章；需要一并撤下的图片也删除。下次构建会替换整个网站。删除文件不会清除 Git 历史中的旧版本。

## 换电脑

```sh
git clone https://github.com/sona201/sona201.github.io.git
cd sona201.github.io
```

用 Obsidian 打开这个目录，配置正常的 Git 推送身份，即可写作和发布。需要私人笔记时另外克隆私有的 ObsidianDoc 并打开为另一个库。两个库互不依赖，不需要 `.obsidian-vault.json`、PAT、Deploy Key 或额外的同步插件。这里的“无需 PAT”指发布流水线；本机 Git 仍需正常认证。

仅编辑和推送文章不需要本地安装 Hugo；需要本地预览时安装 `.hugo-version` 指定的 Hugo extended，然后运行：

```sh
hugo server --buildDrafts --bind 127.0.0.1
```

打开 <http://127.0.0.1:1313/>。

## 标准部署

采用 [Hugo 官方 GitHub Pages 部署流程](https://gohugo.io/host-and-deploy/deploy-to-github-pages/)：

```text
推送 main
  → 检查源码
  → Hugo 构建 public/
  → 检查站内链接、资源和隐私
  → actions/upload-pages-artifact
  → actions/deploy-pages
```

源码、主题与配置保存在本仓库；`public/` 是构建产物，不提交 Git。Pages 的 Source 为 **GitHub Actions**。工作流使用自动生成的 `GITHUB_TOKEN` 和 OIDC，不调用另一个仓库、不使用长期部署 token。Hugo 版本由 `.hugo-version` 固定，Actions 固定版本 SHA；升级时修改对应版本并检查构建即可。

PR 只构建、检查和上传产物，不部署公开预览。`main` 推送或在 `main` 手动运行 **Build and deploy** 才部署。失败时查看对应 Actions 日志；构建失败不会部署。需要撤销改动时用 `git revert <提交>` 并推送，经过当前检查重新构建，而不是恢复旧的完整站点快照。

旧 `blogs` 仓库保持归档。旧跨库同步、发布映射、快照事务、在线 PR 预览和自动恢复流程已经停用，历史说明在 [migration/legacy-publication.md](migration/legacy-publication.md)。历史迁移清单、工具、测试和 Release 保留用于审计，不是日常操作入口，不要重新启用旧发布器。

## 本地检查

```sh
python3 scripts/public_privacy.py check
TZ=UTC hugo --cleanDestinationDir
python3 scripts/site_checks.py check --site public --base-url https://sona201.github.io/
python3 scripts/public_privacy.py check --site public
```

修改检查工具时运行相关测试；历史工具测试可用 `python3 -m unittest discover -s tests -v` 执行。部署完成后，可在网站 `build-info.json` 查看对应源码 SHA；GitHub Actions 提供部署状态和访问链接。
