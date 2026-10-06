---
title: "oh-my-zsh 在 Git 仓库中卡顿的处理"
date: "2024-01-08T00:13:00+08:00"
lastmod: "2024-01-08T00:13:00+08:00"
categories: ["tools"]
slug: "oh-my-zsh-git-slowness"
draft: false
---

## oh-my-zsh扫描git仓库卡慢的解决方法

oh-my-zsh在git目录下执行命令会卡顿明显，简单的cd和ls都会，原因是插件会读取git的配置信息，如果项目目录下有太多的文件，卡顿会非常明显。

可以使用以下命令禁止zsh自动获取git信息，解决卡顿问题：

1、设置 oh-my-zsh 不读取文件变化信息

```bash
git config --add oh-my-zsh.hide-dirty 1
```

2、设置 oh-my-zsh 不读取任何 git 信息

```bash
git config --add oh-my-zsh.hide-status 1
```

3、全局设置 oh-my-zsh 不读取文件变化信息

```bash
git config --global oh-my-zsh.hide-dirty 1
```

4、全局设置 oh-my-zsh 不读取任何 git 信息

```bash
git config --global oh-my-zsh.hide-status 1
```

如果想恢复，设置成0就好