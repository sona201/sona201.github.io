---
title: "Git 修改提交说明与作者信息"
date: "2024-01-14T17:49:40+08:00"
lastmod: "2024-01-14T17:49:40+08:00"
categories: ["tools"]
slug: "git-change-commit-author"
draft: false
---

# Git 修改已提交的 commit 信息，包括作者、邮箱

## 1. 背景
不同电脑配置了不同的用户名、邮箱，例如：不小心用公司电脑提交了 commit 到个人的github 仓库，想改掉已经提交的 commit 的信息。

## 2. 修改用户名、邮箱

```bash
# 全局修改
git config --global user.name "clin"
git config --global user.email "user@example.com"
# 针对某个仓库修改
git config user.name "clin"
git config user.email "user@example.com"
```

> 这里修改只对后续的提交有效

## 3. 修改 commit 信息，包括作者、邮箱

### 3.1 修改最后一次 commit 的信息
直接使用 amend 进行修正

#### 3.1.1 修改 commit 注释信息

```bash
git commit --amend
git commit --amend --message="modify message" --author="admin <user@example.com>"
```

> 出现修改注释信息的界面，默认是vim编辑模式，merge时会有#开头的注释，那部分可以不用修改，只修改对应无注释的内容。

#### 3.1.2 修改作者、邮箱

```bash
git commit --amend --author="{username} <{email}>"
```

> 例如：git commit --amend --author="clin <user@example.com>"

### 3.2 修改某几次 commit 的信息

#### 3.2.1 使用 log 查看提交记录


```bash
git log -2  # 查看最近两次的提交信息，注：-2 代表最后 2 条记录
git log --author=clin  # 查看作者为 clin 的提交记录
git log --author=user@example.com  # 查看作者(邮箱)为 user@example.com 的提交记录
git log --grep <pattern(commit-message)>  # 查看提交记录包含 xx 的记录，支持正则匹配
git log --oneline -2  # 简短信息 （oneline：一行）
```

#### 3.2.2 rebase 需要修改的 commit

```bash
git rebase -i HEAD~2
# 或者
git rebase -i {commitID}  # 例如 git rebase -i d95ddfb
```

此时会输出
```
pick abc1234 feat: update example widget
pick def5678 feat: add example dashboard

# Rebase dbca477..8bfe4f9 onto dbca477 (2 commands)
#
# Commands:
# p, pick <commit> = use commit
# r, reword <commit> = use commit, but edit the commit message
# e, edit <commit> = use commit, but stop for amending
# s, squash <commit> = use commit, but meld into previous commit
# f, fixup [-C | -c] <commit> = like "squash" but keep only the previous
#                    commit's log message, unless -C is used, in which case
#                    keep only this commit's message; -c is same as -C but
#                    opens the editor
# x, exec <command> = run command (the rest of the line) using shell
# b, break = stop here (continue rebase later with 'git rebase --continue')
# d, drop <commit> = remove commit
# l, label <label> = label current HEAD with a name
# t, reset <label> = reset HEAD to a label
# m, merge [-C <commit> | -c <commit>] <label> [# <oneline>]
# .       create a merge commit using the original merge commit's
"~/File/Project/work/devops-front/.git/rebase-merge/git-rebase-todo" 30L, 1408B
```

> rebase 命令会进入编辑模式，这时可以修改commit信息，rebase 会合并一些分支，具体的暂时不讲述了。 \
> 最上面两行就是对应的 commit 记录，如果需要修改，需要把对应 commit 信息前的 pick 更改为 edit (vim编辑) \
> 执行 rebase 命令后，会出现 reabse 的编辑窗口，窗口底下会有提示怎么操作。\
> 这里把需要修改的 commit 最前面的 pick 改为 edit，可以一条或者多条。

#### 3.2.3 修改 commit 信息

只修改注释信息

```bash
git commit --amend  # 只修改注释信息，输入后，会跳转到编辑页面
git commit --amend --author="clin <user@example.com>" --no-edit  # 只修改作者、邮箱
git commit --amend --author="{username} <{email}>"  # 同时修改注释信息、作者、邮箱，输入后，会跳转到编辑页面
```

修改完成后，继续执行下面命令，表示确认更新
```bash
git rebase --continue
```

> 如果是修改多条的话，重复以上 3.3.2 操作即可。直到出现以下提示，说明全部修改已经完成。

`Successfully rebased and updated refs/heads/master.`

#### 3.2.4 push 仓库更改到远程仓库

强制 push
```bash
git push --force origin master
```

> 注：当仓库是多人操作时，可能会覆盖别人push 的代码，请谨慎操作。

### 3.3 使用脚本自动更改

这个操作原本是属于非常规操作，网上都是提供了一个脚本，确实能执行，但脚本的变量含义没有能解释的

[官方链接 https://git-scm.com/docs/git-filter-branch/zh_HANS-CN](https://git-scm.com/docs/git-filter-branch/zh_HANS-CN)

官方给出的脚本示例

```bash
git filter-branch --env-filter '
  if test "$GIT_AUTHOR_EMAIL" = "root@localhost"
  then
    GIT_AUTHOR_EMAIL=user@example.com
  fi
  if test "$GIT_COMMITTER_EMAIL" = "root@localhost"
  then
    GIT_COMMITTER_EMAIL=user@example.com
  fi
' -- --all
```

网上流传的版本，我执行过了，暂时没遇到问题

两者的区别是指定分支tag，和export命令，其余的都是一样的。

```bash
git filter-branch --env-filter '
WRONG_EMAIL="user@example.com"
NEW_NAME="New Name Value"
NEW_EMAIL="user@example.com"

if [ "$GIT_COMMITTER_EMAIL" = "$WRONG_EMAIL" ]
then
    export GIT_COMMITTER_NAME="$NEW_NAME"
    export GIT_COMMITTER_EMAIL="$NEW_EMAIL"
fi
if [ "$GIT_AUTHOR_EMAIL" = "$WRONG_EMAIL" ]
then
    export GIT_AUTHOR_NAME="$NEW_NAME"
    export GIT_AUTHOR_EMAIL="$NEW_EMAIL"
fi
' --tag-name-filter cat -- --branches --tags
```

[git 工具重写 https://git-scm.com/book/zh/v2/Git-%E5%B7%A5%E5%85%B7-%E9%87%8D%E7%BD%AE%E6%8F%AD%E5%AF%86](https://git-scm.com/book/zh/v2/Git-%E5%B7%A5%E5%85%B7-%E9%87%8D%E7%BD%AE%E6%8F%AD%E5%AF%86)

```bash
git filter-branch --commit-filter '
        if [ "$GIT_AUTHOR_EMAIL" = "schacon@localhost" ];
        then
                GIT_AUTHOR_NAME="Scott Chacon";
                GIT_AUTHOR_EMAIL="user@example.com";
                git commit-tree "$@";
        else
                git commit-tree "$@";
        fi' HEAD
```
