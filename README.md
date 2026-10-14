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

仍使用两个仓库：`blogs` 保存公开稿和构建工具，`sona201/sona201.github.io` 的 `master` 保存生成的网站。Obsidian 主库不进入 CI。`PERSONAL_TOKEN` 沿用现有配置，需要具有目标 Pages 仓库的 Contents 写权限。

发布分为两个独立工作流：

```text
main push / PR / 手动运行
  → Blog checks：测试、公开稿审计、映射校验、Hugo 构建、站内链接检查
  → 保存绑定源码 SHA 和运行次数的静态产物
  → Blog publish：重新核对 GitHub 状态、校验产物、串行发布
  → 核对线上版本标记、页面和资源内容
  → 正式站验证失败时恢复前一版，再验证恢复结果
```

Hugo 版本固定在 `.hugo-version`，本地也使用相同版本。Actions 固定到已核对版本的完整 commit SHA。构建会运行 `tests/` 和文章 demo 的测试，拒绝无发布映射的文章、私人标记、缺失本地资源和失效站内页面链接。不会访问外部链接来决定构建是否通过。

每份产物包含 `build-info.json` 和 `site-manifest.json`，后者记录全部静态文件的 SHA-256。标记中的 `run_id` 使用 `运行ID-尝试次数`，重跑不会把旧产物误认成新部署。构建产物保留 30 天。发布日志摘要记录源码 SHA、目标仓库的前后提交及线上验证结果，不能只凭 Actions 上传成功判断上线成功。

## PR 预览

1. 从本仓库分支创建面向 `main` 的 PR。`Blog checks` 自动构建，可以下载静态产物。
2. 需要在线预览时，为 PR 添加名称为 `preview` 的标签。标签事件会重新触发构建；通过后由可信发布器发布到 `https://sona201.github.io/previews/pr-<PR编号>/`。
3. 在对应 `Blog publish` 运行的 Summary 中打开预览链接。新提交会更新同一地址；源码 SHA 已过期的构建不会覆盖新版本。
4. 关闭 PR 或移除 `preview` 标签，会删除该 PR 的线上预览。合并后正式站仍走自己的完整发布流程。

fork PR 只生成可下载产物，不使用部署凭据、不公开发布预览。给同仓库 PR 加 `preview` 标签表示允许把其构建结果公开在博客域名下；子目录不构成浏览器同源隔离，应只给信任的改动加标签。拥有仓库写权限的人仍属于可信维护者，这套设计不试图防御维护者主动修改工作流取得仓库 Secret。

预览关闭评论和 Google Analytics，并设置 `noindex, nofollow`。构建脚本仅重定位已存在的站内 URL 属性和搜索索引链接，保证图片、样式、脚本、搜索结果和下载文件使用预览前缀；不会改写正文中的代码示例。

`Blog publish` 的代码始终来自 `main`。它不执行 PR 源码、PR 工作流脚本或下载产物中的程序；通过 GitHub API 重查运行 ID、运行次数、工作流、PR 来源、标签与当前 head，然后验证产物身份和逐文件校验和。生产、预览、清理及回滚共用发布队列，正在发布或验证的任务不会被新提交取消。

## 发布验证与回滚

正式发布会删除已撤下的旧页面，同时保留其他 PR 的 `previews/` 目录。预览只修改自己的子目录。部署使用普通快进 push，目标仓库有外部并发修改时会停止，不执行 force push。

线上检查先要求 `build-info.json` 与本次构建一致，再比较首页、搜索页与索引、RSS、sitemap、404 页面、全部 CSS/JS、全部下载文件以及搜索索引中最新三篇文章的内容哈希。最多检查 30 轮，轮间隔 10 秒，并设置 300 秒总预算；工作流额外给该步骤 6 分钟上限，为恢复保留时间。它是明确范围的内容验收，不是浏览器交互或全站外链测试。

正式站验证失败会尝试自动恢复部署前的静态文件，新增一个恢复提交，并保留当前预览。只有远端仍指向本次部署时才允许自动恢复，避免撤销别人的后续发布。即使恢复成功，失败部署的工作流仍标红，并记录恢复版本和验证结果。首次迁移前的旧站没有版本标记，恢复这类历史版本时核对首页的完整内容哈希。

手动回滚：

1. 在一次已验证成功的 `Blog publish` Summary 中找到 `published_commit`，或在 Pages 仓库历史中选择已知可用版本。这里填写的是 **Pages 仓库提交**，不是 `blogs` 的源码提交。
2. 打开本仓库 Actions → **Blog rollback** → **Run workflow**，分支选择 `main`。
3. 将完整 40 位提交 SHA 填入 `deployment_commit`。
4. 查看恢复提交与线上验证结果。回滚不会重新编译旧源码，也不会改变 `blogs/main`；后续新的 `main` 发布仍会更新网站。

手动回滚目标必须已经存在于 Pages 的 `master` 历史中。恢复失败或网络持续异常时，根据 Summary 和日志人工处理，工作流不会无限重试。若运行器在远端 push 成功后异常退出，也需要从 Pages 历史识别实际状态后使用手动回滚。

## 本地检查

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s examples/magpie-agent-loop-demo -v
python3 scripts/sync_obsidian_blog.py --audit-public
python3 scripts/check_public_manifest.py
hugo --cleanDestinationDir
python3 scripts/site_checks.py check --site public --base-url https://sona201.github.io/
```

`publish_site.py` 的测试使用临时本地 Git 仓库，验证撤稿、预览、并发冲突与追加提交回滚，不访问真实远端。PR 的在线预览和正式站验收由 GitHub Actions 执行。

工作流并发队列使用 GitHub 当前支持的 `queue: max`。固定版 actionlint 1.7.12 尚未识别该属性，CI 只忽略这一个精确诊断，其余工作流语法错误仍会阻止构建。

参考：[GitHub workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)、[GitHub 并发队列](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)。
