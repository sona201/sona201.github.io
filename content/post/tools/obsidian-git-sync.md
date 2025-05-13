---
title: 'Obsidian-sync-v2'
description: "新版本的同步方式"
date: '2024-07-13T16:33:55+08:00'
lastmod: '2024-07-13T16:33:55+08:00'
categories: ["tools"]
slug: 'obsidian-tool-v2'
draft: true
tags: ["obsidian", "tool", "product", "生产力", "git-plug"]
---


## 前言

最近看到别人提到的笔记软件，还是想到obsidian，这个软件还是挺舒服的，主要是本地化，不需要提太多。可以参考上次文章 https://sona201.github.io/posts/obsidian-tool-v1/

之前在推上看到有人说到obsidian的方式，有人写了一个插件，github同步，之前也没有别特在意，简单的看了下，没有跑通。

https://forum.obsidian.md/t/obsidian-git-sync-on-your-ios-without-any-extra-app/60639

https://forum.obsidian.md/t/the-easiest-way-to-setup-obsidian-git-to-backup-notes/51429
没有找到对应的插件plug，这个挺头疼的。方案跟说的有点不一样，确实通过这个方式是最理想的解决方案。在我看来堪比官方的。

最近跑通了，在手上也是一样，那样手机上的搜索也能解决了，之前手机上要使用ish方式，还特别麻烦。


## 正文
obsidian 插件地址: obsidian://show-plugin?id=obsidian-git

插件github仓库: https://github.com/Vinzent03/obsidian-git

```
Create a repository or fork the md repo in github
Download Git
Create a personal access token from githubcreate-pat-github.png
Install the Obsidian Git community plugin
Create a folder to store the repository. (e.g. remote-blog/). Set scopes to repo & expiration to no expiration
Run the command (CMD/Ctrl + P): Clone an existing remote repo clone-repo-git-plugin.png
Paste the URL of the forked repository in the following format
https://<PERSONAL_ACCESS_TOKEN>@github.com/<USERNAME>/<REPO>.git
For example it might look like this:

https://ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX@github.com/ithinkwong/linked-blog-starter-md.git
Then type in the folder you created in step 5 (e.g. remote-blog/)
Restart Obsidian
Make edits to your notes
Publish your notes run the command “Obsidian Git: Create backup” by opening the command palette (CMD/Ctrl + P)
```

1. 先创建git仓库
2. 本地安装git命令行
3. 然后github上创建token，需要对应的权限路径( profile -> develop settings -> tokens)
[tokens](https://github.com/settings/tokens)
Generate new token -> Generate new token(classtic)
选则 admin:ssh_signing_key [Full control of public user SSH signing keys]
过期时间自行设置，我设置的是永不过期
4. 需要克隆地址，然后写自己的repo，回车，然后写自己的目录名，再次回车就能自动克隆git仓库。
也是因为自己命名目录名，导致obsidian的文档会都一层，不过那样比第一种方式好，因为不需要配置 `.gitignore` 文件了。也不会导致各个客户端的配置不一致无法同步

手机上也式样的操作，不过可能新手会遇到没有git的问题，可以按照第一篇文章里说的ish方式安装下，其余的流程都是一样的。

手机下载后，默认创建一个vault，不然不能进入软件。安装git插件（需要手机上有git功能，可以使用ish方法来解决），然后按照流程新建一个目录文件夹。搜索 clone ,输入地址。
看到提示初始化消失后，打开左侧目录，文件应该都在了
