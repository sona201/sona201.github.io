---
title: "Git 本地与全局配置笔记"
date: "2024-02-21T10:13:35+08:00"
lastmod: "2024-02-21T10:13:35+08:00"
categories: ["tools"]
slug: "git-dotfiles-setup"
draft: false
---


### 配置用户名，颜色
```
git config --global user.name "you_name"  # 设置全局用户名
git config --global user.email "user@example.com"  # 设置全局邮箱
git config --global color.ui true  # 设置全局颜色显示
```

git 相关配置
https://zhuanlan.zhihu.com/p/133706032

### 配置全局
```bash
# git config --global alias.confg 'config --global'  # 目前看似乎没有生效
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.ci commit
git config --global alias.br branch
git config --global alias.unstage 'reset HEAD'
git config --global alias.last 'log -1'
git config --global alias.lg "log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit"
git config --global core.quotepath false  # vscode git status/commit 乱码
# 全局忽略 .DS_Store 文件
# specify a global exclusion list
git config --global core.excludesfile ~/.gitignore
# adding .DS_Store to that list
echo .DS_Store >> ~/.gitignore
```

### 配置针对当前仓库
```bash
git config alias.st status
git config alias.co checkout
```

### 生成ssh-key generate
```bash
ssh-keygen -t rsa -C 'company name'
```

### 本地配置
```
git config --local user.name "cxx"
git config --local user.email "sxx"
```
