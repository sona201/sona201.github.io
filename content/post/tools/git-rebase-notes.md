---
title: "Git rebase 与冲突处理记录"
date: "2023-01-14T21:45:16+08:00"
lastmod: "2023-01-14T21:45:16+08:00"
categories: ["tools"]
slug: "git-rebase-notes"
draft: false
---

## git rebase

[medium参考](https://medium.com/@ddwen/thoroughly-understand-git-rebase-2a7c40a5dfd6)\
[掘金参考](https://juejin.cn/post/6844903895160881166)

> 简单理解，git rebase 会省去一些不必要的记录，让整个log更好看

最实在就是，当你从master checkout 一个分支进行feature功能开发，别人开发的功能完成了。你需要合并别人的代码，然后继续开发

这个时候使用git merge会记录别的数据，如果是用git rebase会更好些

1. 当前分支为`clin`, 远程分支别人更新过后

```bash
git rebase origin/release # 合并远程 origin/release 分支
git rebase master # 合并本地master分支
```

2. 查看`clin`的`git log`发现
```
commit 512d838187acdcb33338fa6960a5cb1f8dc0644f (HEAD -> clin)
Author: clin <user@example.com>
Date:   Sat Jan 14 16:35:03 2023 +0800

    rm cdn picture icon

commit 880816383efc00551ffbf4aa30d217ab1aba3e56 (origin/release)
Author: nickname <user@example.com>
Date:   Sat Jan 14 08:36:15 2023 +0000

    删除msg

commit cd32eff64d2a60cfdda784de472d415d97c55191 (origin/master, release, master)
Merge: 6e2e9cc c77e957
Author: nickname <user@example.com>
Date:   Fri Jan 13 02:06:55 2023 +0000
```

3. 查看`origin/release`的`git log`
```
commit 880816383efc00551ffbf4aa30d217ab1aba3e56 (HEAD -> release, origin/release)
Author: nickname <user@example.com>
Date:   Sat Jan 14 08:36:15 2023 +0000

    删除msg

commit cd32eff64d2a60cfdda784de472d415d97c55191 (origin/master, master)
Merge: 6e2e9cc c77e957
Author: nickname <user@example.com>
Date:   Fri Jan 13 02:06:55 2023 +0000
```

对比`log`日志，明显会让强迫症舒服

## git pull自动rebase

### 冲突

有时候git pull 自动变成 git rebase
git pull 是一个组合命令，等于 git fetch + git merge。
目前不是很清楚为什么会出现rebase，但猜测应该是pull自动执行的
git pull --rebase origin master
```
Auto-merging src/App.vue
CONFLICT (content): Merge conflict in src/App.vue
error: could not apply 953b627... active
hint: Resolve all conflicts manually, mark them as resolved with
hint: "git add/rm <conflicted_files>", then run "git rebase --continue".
hint: You can instead skip this commit: run "git rebase --skip".
hint: To abort and get back to the state before "git rebase", run "git rebase --abort".
Could not apply 953b627... active
```

拉取远程分支1 `git pull origin test:test`
拉取远程分支2 `git checkout -b test <name of remote>/test`

遇到这种情况的处理方式
- 处理冲突，然后执行 `git rebase --continue` 
- 放弃更新，回到之前的版本`git rebase --abort`
- 跳过代码冲突，以远程分支为主，忽略本地代码`git rebase --skip`

#### git rebase --skip
```
commit faf2313d3ae7ca5af1f6011d73fc32db99bb81a9 (HEAD -> release, origin/release)
Author: nickname <user@example.com>
Date:   Sat Jan 14 13:41:57 2023 +0000

    Update App.vue origin release

commit 880816383efc00551ffbf4aa30d217ab1aba3e56
Author: nickname <user@example.com>
Date:   Sat Jan 14 08:36:15 2023 +0000

    删除msg

commit cd32eff64d2a60cfdda784de472d415d97c55191 (origin/test, origin/master, test, master)
Merge: 6e2e9cc c77e957
```