---
title: "GitHub Actions 使用 Fine-grained PAT 跨仓库部署 Hugo"
description: "记录 GitHub Actions 从 Hugo 源码仓库向 GitHub Pages 仓库发布时，创建 Fine-grained Personal Access Token、最小权限配置和 Actions Secret 的完整过程。"
date: "2026-10-03T21:15:00+08:00"
lastmod: "2026-10-03T21:15:00+08:00"
categories: ["GitHub"]
tags: ["GitHub Actions", "Fine-grained PAT", "Hugo", "GitHub Pages", "Token"]
image:
---

博客使用两个 GitHub 仓库：

```text
sona201/blogs
    ↓ Hugo build
    ↓ GitHub Actions
sona201/sona201.github.io
    ↓
GitHub Pages
```

其中 `blogs` 保存 Hugo 源码，`sona201.github.io` 保存 Hugo 生成的静态页面。

原来的 GitHub Actions 一直使用 `PERSONAL_TOKEN` 将 `public/` push 到另一个仓库。很久没有更新博客后再次发布，Actions 在 Deploy 阶段失败：

```text
remote: Invalid username or token.
Password authentication is not supported for Git operations.

fatal: Authentication failed for
'https://github.com/sona201/sona201.github.io.git/'
```

Hugo 的 Build Web 是成功的，因此问题不是文章或 Hugo 构建，而是跨仓库 push 使用的旧 Personal Access Token 已失效。

这篇记录如何创建一个权限尽可能小的 Fine-grained Personal Access Token，并更新 GitHub Actions Secret。

## 一、为什么需要额外 Token

GitHub Actions 会自动提供 `GITHUB_TOKEN`，但它主要针对当前 workflow 所在仓库。

当前 workflow 位于：

```text
sona201/blogs
```

而构建结果需要 push 到：

```text
sona201/sona201.github.io
```

这是跨仓库写入，因此这里继续使用一个只允许写目标仓库的 Fine-grained PAT。

目标是让 token 只具备：

```text
sona201/sona201.github.io
        ↓
Contents: Read and write
```

不授予整个账号所有仓库的写权限。

## 二、创建 Fine-grained Personal Access Token

进入 GitHub 个人设置：

```text
GitHub
→ Settings
→ Developer settings
→ Personal access tokens
→ Fine-grained tokens
→ Generate new token
```

Token name 可以填写：

```text
blogs-deploy
```

Description 可以填写：

```text
Deploy Hugo build output from sona201/blogs to sona201/sona201.github.io
```

Expiration 根据自己的维护习惯设置。例如设置一年有效期：

```text
2027/10/03
```

需要注意：Fine-grained PAT 到期后不会自动生成新的 token，也不会自动更新 GitHub Actions Secret。到期后需要重新创建并替换 Secret。

## 三、限制 Repository access

Repository access 选择：

```text
Only select repositories
```

然后只选择：

```text
sona201/sona201.github.io
```

不要选择 `All repositories`。

这样即使这个 token 泄漏，它也不能修改账号下其他仓库。

## 四、配置最小 Repository permissions

这里最容易选错。

最开始容易误选：

```text
Actions: Read and write
```

但部署动作本质上是：

```bash
git push origin master
```

需要修改的是仓库内容，而不是管理 GitHub Actions。

因此删除 Actions / Workflows 等无关权限，然后：

```text
Add permissions
→ Contents
→ Read and write
```

最终权限应该只有：

```text
Repository access
└── sona201/sona201.github.io

Repository permissions
├── Contents
│   └── Read and write
│
└── Metadata
    └── Read-only
```

其中 Metadata Read-only 是 GitHub 要求的基础权限。

不需要：

- Actions: Read and write
- Workflows: Read and write
- Issues
- Pull requests
- Administration

权限越少越好。

## 五、生成 Token

确认配置以后点击：

```text
Generate token
```

GitHub 会生成类似：

```text
github_pat_xxxxxxxxxxxxxxxxx
```

注意：

> Token 属于凭据，不要写进博客、代码、commit、截图或聊天记录中。

生成后的 token 通常只会完整显示一次，立即复制。

## 六、更新 GitHub Actions Secret

进入 Hugo 源码仓库：

```text
sona201/blogs
→ Settings
→ Secrets and variables
→ Actions
```

找到：

```text
PERSONAL_TOKEN
```

点击 Update。

将刚才生成的 `github_pat_...` 粘贴到 Value：

```text
PERSONAL_TOKEN
Value: [新的 Fine-grained PAT]
```

点击：

```text
Update secret
```

GitHub 不会再把 Secret 的原值显示出来，这是正常的。

## 七、Workflow 如何使用 Secret

当前 Hugo 部署 workflow 使用 `peaceiris/actions-gh-pages`：

```yaml
- name: Deploy Web
  uses: peaceiris/actions-gh-pages@v4
  with:
    personal_token: ${{ secrets.PERSONAL_TOKEN }}
    external_repository: sona201/sona201.github.io
    publish_branch: master
    publish_dir: ./public
    commit_message: ${{ github.event.head_commit.message || 'manual deploy' }}
```

这里不要直接写：

```yaml
personal_token: github_pat_xxxxx
```

正确方式始终是从 GitHub Actions Secret 读取：

```yaml
personal_token: ${{ secrets.PERSONAL_TOKEN }}
```

## 八、重新运行失败的 Workflow

更新 Secret 后：

```text
blogs
→ Actions
→ deploy hugo
→ 找到失败的运行
→ Re-run jobs
→ Re-run failed jobs
```

正常流程应该变成：

```text
Checkout       ✓
Setup Hugo     ✓
Build Web      ✓
Deploy Web     ✓
```

如果 Build Web 成功但 Deploy Web 仍然出现：

```text
Invalid username or token
Authentication failed
```

优先检查：

1. `PERSONAL_TOKEN` Secret 是否确实更新。
2. Fine-grained PAT 是否选择了正确的 Resource owner。
3. Repository access 是否包含目标仓库。
4. Contents 是否为 Read and write。
5. Token 是否过期或被撤销。
6. Workflow 引用的 Secret 名称是否与 `PERSONAL_TOKEN` 完全一致。

## 九、顺便升级旧 GitHub Actions

这次排查时还发现旧 workflow 使用：

```yaml
actions/checkout@v2
peaceiris/actions-hugo@v2
peaceiris/actions-gh-pages@v3
```

GitHub Runner 已提示旧 Node.js runtime 被弃用。

因此同步更新为：

```yaml
actions/checkout@v7
peaceiris/actions-hugo@v3
peaceiris/actions-gh-pages@v4
```

并增加：

```yaml
permissions:
  contents: read

concurrency:
  group: deploy-hugo
  cancel-in-progress: true
```

Hugo 本身暂时仍保持原来的 `0.101.0`，避免同时升级 Hugo 和主题导致额外兼容问题。先恢复部署链路，再单独处理 Hugo/主题升级。

## 十、PAT 方案的缺点

这个方案虽然简单，但有一个长期维护问题：

```text
Fine-grained PAT
      ↓
到期
      ↓
GitHub Actions 部署失败
      ↓
重新生成 PAT
      ↓
更新 PERSONAL_TOKEN
```

GitHub 不会自动轮换这个 PAT。

如果以后不想维护 PAT，可以考虑：

- 使用 Deploy Key，让源码仓库固定向 Pages 仓库发布。
- 调整为单仓库 Hugo + GitHub Pages 官方 Actions 部署。
- 重新设计发布流程，避免 workflow 跨仓库 push。

目前对于已有的：

```text
blogs → sona201.github.io
```

双仓库结构，Fine-grained PAT 的优点是迁移成本低，并且可以把写权限严格限制在 `sona201.github.io` 一个仓库。

## 总结

这次实际配置最终为：

```text
Token:
blogs-deploy

Resource owner:
sona201

Repository access:
Only select repositories
└── sona201/sona201.github.io

Repository permissions:
├── Contents: Read and write
└── Metadata: Read-only
```

然后保存到：

```text
sona201/blogs
→ Settings
→ Secrets and variables
→ Actions
→ PERSONAL_TOKEN
```

GitHub Actions 再通过：

```yaml
personal_token: ${{ secrets.PERSONAL_TOKEN }}
```

完成 Hugo 构建产物向 `sona201.github.io` 的跨仓库发布。

这套权限已经足够完成部署，没有必要为了方便给 token 整个账号或所有仓库的写权限。
