# Ricardo 博客

站点：[sona201.github.io](https://sona201.github.io)

笔记主库的本地路径通过配置指定。在 Obsidian 中打开主库，从 `笔记首页.md` 查看全部笔记、主题目录、公开稿和私人草稿。旧 `noteDoc` 已导入主库的 `归档/noteDoc`，原目录保留。

本仓库只保存网站稿件、主题和构建工具。私人笔记与草稿保存在 Obsidian 主库；完整迁移记录也保存在主库的 `管理/迁移记录`。

文章的写作和润色约定见 [AGENTS.md](AGENTS.md)。

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

`--audit-public` 检查公开标记和资源路径，不判断公司隐私。发布前还需审阅命令、日志和截图中的凭据、业务名称、内部地址及域名；技术示例应使用示例名称和文档地址。撤下敏感图片时，同时移除主稿引用和 `static/images` 中的网站副本，否则图片直链仍会发布。私人附件无需一并删除。

撤下文章时，把主稿移到 Obsidian 的 `私人笔记`，移除发布映射，并删除本仓库的对应文章，再重新构建发布。删除文件不会清除已有 Git 提交中的旧内容。

隐私脱敏也不会删除旧 Git 历史或 Release 快照；已经公开的真实凭据应更换。完成脱敏后，只使用脱敏后的快照回滚，避免把已移除的信息重新发布。

## 仓库与部署

`sona201/sona201.github.io` 的 `main` 保存公开稿、主题和构建工具，同时运行 GitHub Pages 官方产物部署。网站地址仍为 `https://sona201.github.io/`。迁移前的 `master` 静态历史保留供恢复查询，新的部署不再向它提交生成文件。旧 `blogs` 仓库停止发布；Obsidian 主库不进入 CI。

发布使用工作流自动生成的 `GITHUB_TOKEN`，不再依赖跨仓库 `PERSONAL_TOKEN`。检查工作流只有 `contents: read`；可信发布工作流具有管理快照所需的 Contents 写权限，以及 Pages 部署、OIDC、读取构建和 PR 的权限。

```text
main push / PR / 手动运行
  → Blog checks：测试、公开稿审计、映射校验、Hugo 构建、站内链接检查
  → 保存绑定源码 SHA 和运行次数的静态产物
  → Blog publish：重查发布权限，将变更合并进当前已验证的完整站点
  → 保存 Release 快照，登记待完成的发布事务
  → upload-pages-artifact → deploy-pages
  → 验证整站版本标记、正式站和全部预览的内容
  → 成功后更新当前快照；失败时尝试恢复发布前的完整快照
```

`Blog publish` 与 `Blog rollback` 共用 `pages-transaction.yml` 中的发布事务。生产、预览、清理及回滚共用串行队列；读基线、合并、部署、验证和恢复都在同一队列任务内，正在部署的任务不会被新提交取消。

Hugo 版本固定在 `.hugo-version`，本地也使用相同版本。Actions 固定到已核对版本的完整 commit SHA。构建运行 `tests/` 和文章 demo 的测试，拒绝无发布映射的文章、私人标记、缺失本地资源和失效站内页面链接。外部链接是否可用不影响构建结果。

每份构建包含 `build-info.json` 和 `site-manifest.json`，记录源码 SHA、运行身份和静态文件 SHA-256。`run_id` 使用 `运行ID-尝试次数`，重跑不会与旧构建混淆。可下载的 Actions 构建产物保留 30 天。

完整站点快照另存为 `pages-snapshot-*` GitHub Release，包含归档、全站文件清单和校验和，不依赖 Actions 产物的过期时间。Release 不会由本流程自动清理。固定的 `pages-state` Release 保存当前已验证快照及待完成事务；它与 GitHub 界面的 Latest Release 排序无关。站点的 `deployment-info.json` 标识完整快照，所以仅更新预览时也能核对本次整站部署是否生效。不要删除当前快照、待恢复的快照或仍需回滚的历史 Release。

### 发布开关

正式发布只在 `sona201/sona201.github.io` 仓库、仓库变量 `PAGES_DEPLOY_ENABLED` 为字符串 `true` 时运行。变量缺失或为其他值时仍可执行构建检查，但不会部署。

首次切换前，保持发布开关关闭，运行一次 **Blog Pages bootstrap**，将已经核验的当前 `master` 完整提交 SHA 填入 `legacy_commit`。它会检查 `master` 未变、导出静态文件、验证线上基线并保存首份 Release 快照及状态指针，不部署网站。状态指针已存在时拒绝再次初始化。

仓库 Settings → Pages → Source 应设为 **GitHub Actions**，默认分支为 `main`；`github-pages` environment 仅允许 `main` 部署。更换发布方式前先备份配置和已验证站点，停止旧发布与回滚工作流并等在途任务结束，再启用新入口。切换失败时，先停止新部署，再恢复原 Pages 分支发布配置并核验旧站，避免两套发布器同时工作。

## PR 预览

1. 从本仓库分支创建面向 `main` 的 PR。`Blog checks` 自动构建，可以下载静态产物。
2. 需要在线预览时，为 PR 添加名称为 `preview` 的标签。标签事件重新触发构建；通过后由可信发布器发布到 `https://sona201.github.io/previews/pr-<PR编号>/`。
3. 在对应 `Blog publish` 运行的 Summary 中打开预览链接。新提交会更新同一地址；源码 SHA 已过期的构建不会覆盖新版本。
4. 关闭 PR 或移除 `preview` 标签，会删除该 PR 的线上预览。合并后的正式站走自己的完整发布流程。

每次 Pages 部署替换整个站点。发布器会从已验证快照取出正式站和所有预览，再只替换本次需要变更的部分；正式站发布和手动回滚保留当前预览，预览更新不会覆盖正式站或其他 PR，预览清理不会复活历史预览。

fork PR 只生成可下载产物，不使用部署凭据、不公开发布预览。给同仓库 PR 加 `preview` 标签表示允许把构建结果公开在博客域名下；子目录不构成浏览器同源隔离，应只给信任的改动加标签。预览关闭后，先前的公开版本仍可能保存在历史 Release 中。拥有仓库写权限的人仍属于可信维护者，这套设计不试图防御维护者主动修改工作流。

预览关闭评论和 Google Analytics，并设置 `noindex, nofollow`。构建脚本仅重定位已存在的站内 URL 属性和搜索索引链接，保证图片、样式、脚本、搜索结果和下载文件使用预览前缀；不会改写正文中的代码示例。

`Blog publish` 只运行 `main` 上的可信脚本，不执行 PR 源码、PR 工作流脚本或下载产物中的程序。发布前通过 GitHub API 重查运行 ID、运行次数、工作流、PR 来源、标签与当前 head，再验证构建身份、归档路径和逐文件校验和；上传候选产物后、开始部署前再次核对授权。

## 发布验证与回滚

正式发布会删除已撤下的旧页面。候选完整站点在部署前保存为快照；发布状态先记录待完成事务，线上验收成功后才推进当前已验证快照指针。不能只凭产物上传成功或 Pages action 成功判断整个发布流程已经完成。

线上检查先核对整站 `deployment-info.json`，再检查正式站和各个预览的 `build-info.json` 及代表性资源。内容核验沿用首页、搜索页与索引、RSS、sitemap、404 页面、全部 CSS/JS、全部下载文件以及搜索索引中最新三篇文章的哈希检查。它是明确范围的内容验收，不是浏览器交互或全站外链测试。

生产、预览、清理或手动回滚部署后发生验证失败时，工作流先确认候选后台部署已经结束，再重新上传并部署事务开始前的完整快照，核验恢复结果后才清除待完成事务。即使恢复成功，本次失败发布仍标红。无法确认后台部署是否结束时，会保留事务状态并停止，避免候选部署稍后覆盖恢复版本。

手动回滚：

1. 在一次已验证成功的 `Blog publish` Summary 或 Release 中找到目标 `pages-snapshot-*` 标签。
2. 打开本仓库 Actions → **Blog rollback** → **Run workflow**，分支选择 `main`。
3. 将标签填入 `deployment_commit`。该输入名称为兼容旧流程保留，也接受迁移前 `master` 历史中的完整 40 位网站提交 SHA；不要填源码提交 SHA。
4. 查看新快照与线上验证结果。回滚取历史版本的正式站文件，保留当前全部预览，不重新编译旧源码，也不改动源码 `main`。下一次新的 `main` 发布仍会更新正式站。

如果运行器在部署或更新状态期间异常退出，固定状态 Release 中可能保留待完成事务。新发布会停止，不会默默以旧基线覆盖线上。先确认原运行已结束，再运行 **Blog rollback**，将 `deployment_commit` 填为 `active`，恢复当前记录的已验证快照。恢复器还会核对后台部署状态；无法确认安全恢复或网络持续异常时，根据 Summary 和日志人工处理，不要手工清除 pending 后继续发布。

若事务已经登记，但后台部署尚未创建，部署查询可能返回 404。恢复器会检查原运行对应尝试的完整 job 记录；只有候选部署和恢复部署都明确为 `skipped`，且原运行已结束、没有发生重跑变化，才继续恢复。404 本身不能证明没有在途部署；步骤记录缺失或执行状态不明确时，仍保留 pending，等待人工确认。

首次迁移的基线来自已验证的旧 `master`。对更早、没有版本标记的历史正式站，恢复后核对首页完整内容哈希；现代版本仍使用完整的版本标记和资源内容验收。

## 本地检查

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s examples/magpie-agent-loop-demo -v
python3 scripts/sync_obsidian_blog.py --audit-public
python3 scripts/check_public_manifest.py
hugo --cleanDestinationDir
python3 scripts/site_checks.py check --site public --base-url https://sona201.github.io/
```

快照和事务测试验证撤稿、预览隔离、清理、历史回滚、归档校验和故障恢复。旧 `publish_site.py` 的本地 Git 测试仍保留，以验证复用的文件检查与历史恢复行为；这些测试不访问真实远端。PR 在线预览和正式站验收由 GitHub Actions 执行。

本地切换到新的 checkout 后，重新设置被 Git 忽略的 `.obsidian-vault.json` 主库路径，继续沿用公开清单和同步脚本；不要把私人主库一起迁入 Git。

工作流并发队列使用 GitHub 当前支持的 `queue: max`。固定版 actionlint 1.7.12 尚未识别该属性，CI 只忽略这一个精确诊断，其余工作流语法错误仍会阻止构建。

参考：[GitHub Pages 官方产物部署](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[GitHub workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)、[GitHub 并发队列](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)。
