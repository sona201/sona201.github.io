---
title: "Git 全局忽略 .DS_Store"
date: "2024-05-21T10:56:36+08:00"
lastmod: "2024-05-21T10:56:36+08:00"
categories: ["tools"]
slug: "git-ignore-ds-store"
draft: false
---

# git 仓库有 .DS_Store 文件排除

```bash
# remove any existing files from the repo, skipping over ones not in repo
find . -name .DS_Store -print0 | xargs -0 git rm --ignore-unmatch
# specify a global exclusion list
git config --global core.excludesfile ~/.gitignore
# adding .DS_Store to that list
echo .DS_Store >> ~/.gitignore
```