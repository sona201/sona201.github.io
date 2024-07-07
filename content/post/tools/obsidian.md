---
title: 'Obsidian-tool'
description: "笔记工具obsidian"
date: '2024-07-07T23:31:32+08:00'
lastmod: '2024-07-07T23:31:32+08:00'
categories: ["tools"]
slug: 'obsidian-tool'
draft: false
tags: ["obsidian", "ish", "ios", "sync", "手机"]
---

[原文链接](https://hankmo.com/posts/artifact/ios-sync-obsidian/)

## 前言

用了不少笔记软件，好多都是半途而废，总感觉有各种各样的问题。笔记格式支持问题，云端网络问题(不支持本地)，样式同步问题。
用过有道云笔记，markdown支持一般，后来转成印象笔记，甚至充了会员，但没有特别的改善。印象笔记在体验上并没有提升。使用过语雀，格式样式都挺好，支持的样式也很多，但每次打开都是要从云端拉取，导致打开特别慢，加上语雀的重大事故，无法打开，后来就放弃了。最近用的就是vscode本地文档，直接github同步，确实方便，但vscode没有客户端，没有特意为笔记软件做搜索优化，每次想搜索一个mysql文档，结果跳出n条笔记，完全放弃搜索功能。
最后才是决定使用obsidian，本地客户端，大公司支持，个人免费，还有双链(目前我用的不多，大家都说好)，可以利用github同步，markdown样式格式支持，还有一些高级插件，搜索比较好，还能使用标签特定为笔记做优化，于是就选择了它。它可以直接复制一些网页，粘贴后基本不需要调整格式。

这篇文章也是参考网上的教程，作者写的很详细，但本着自己写一遍才放心的精神，决定摘录一遍，并根据一些自己的需求，加一些自己的操作。

## 正文

对于技术人而言，经常需要记录、整理大量的笔记内容，形成自己的知识库。一款好的笔记软件我认为需要具备以下几个条件：

1. 必须：跨平台，同时支持桌面电脑（Windows，Mac，Linux）和手机（Android，iOS）
2. 必须：支持同步，在多台设备中打开任何一台都能接接着编写笔记
3. 必须：实时存储，就算突然断电、死机也不会丢失已写笔记内容
4. 必须：支持代码高亮，更便于友好地阅读代码
5. 必须：支持 Markdown 格式，快速编写文档必备格式，谁用谁知道
6. 必须：支持多重备份，最好是本地一份、远端一份，首选支持`git`同步的
7. 可选：支持双向链接，这样笔记与笔记之间就可以形成关联关系，慢慢积累后就形成了自己的知识库
8. 可选：支持笔记导出，比如导出 pdf 等格式，便于分享，如果能一键发布到常见博客如 [hexo](https://hexo.io/zh-cn/index.html)、[wordpress](https://cn.wordpress.org/)、[jekyll](https://www.jekyll.com.cn/) 更好

我用过诸多笔记软件，但都存在或多或少的问题，无法满足上述要求，后来一直使用网易的有道笔记，它支持一键保存笔记，不过编辑器实在难用，markdown的图片要自己搭建图床。

阮一峰推荐的笔记软件是 [github.dev](https://docs.github.com/en/codespaces/the-githubdev-web-based-editor)，可以看看他的[这篇文章](http://www.ruanyifeng.com/blog/2021/08/best-note-taking-software-for-programmers.html)。不过我更喜欢原生的app软件，我选择 [obsidian](https://obsidian.md/)，因为它免费而且支持上述的大部分需求，尤其是第6点，对于不想将笔记存储保存给笔记软件厂商而言非常好，直接使用`git`同步。

现在，我基本上都是用 obsidian 来记笔记和写文章，它支持双向链接，很容易形成知识体系，而且具备丰富的插件支持，具体特性可以自己咨询网络。如果对于格式非常多的文章，我也会使用 [AsciiDoc](https://asciidoctor.org/) 格式来编写，相比于 [Markdown](https://markdown.com.cn/) 它更加强大，但是语法也更复杂。Obsidian 目前并不支持，非常遗憾。

在使用 Obsidian 时，最大的问题就是手机端的同步。我是用 Github 存储笔记，手机端没有很好的同步方案，官方的同步方式无法满足需求，而且需要付费。我的需求是，macOS、windows、iPhone、iPad 四种设备上需要从 github 同步我的笔记，没有安卓端同步的需要，所以我使用 [iSH](https://ish.app/) 这个 app，它开源免费，支持 ios，完美的解决了我的问题。

# 什么是 [iSH](obsidian-ish-tutorial.md)

它是一个在 ios 上模拟 Linux 环境的 app，使用的是 [alpine linux](https://www.alpinelinux.org/)，在你的 iPhone、iPad上都可以运行并创建 Linux Shell 环境。正好我可以使用它来同步 git 仓库到我的 ios 设备上。

# 安装 ish app

从 ios 应用商店下载 iSH Shell，注意看名称和logo：

下载好后打开，你就得到了一个 Linux Shell 环境。整体界面与 Shell 一样，这里重点说一下工具栏：

- Tab：点击后可以自动补全命令
- Ctrl：pc 的 ctrl 健，当你需要执行 `Ctrl + C` 时需要用到
- Esc：pc 的 Esc健
- Arrows：点击后上下左右拖动可以实现 pc 的方向键的功能，常用的是向上拖动调出最新一条历史记录命令

> 提示！ 下边的操作，需要输出一些命令，手机上输入不太方便，记得点击工具栏这个 Tab，可以自动补全。

iSH 中，操作基本上都以 `apk` 命令开头。

首先，输出 `apk update` 然后换行即可更新 package。 然后，输入 `uname -a` 来查看操作系统信息：

```shell
localhost:~# uname -a
Linux localhost 4.20.69-ish SUPER AWESOME May 20 2023 23:41:32 i686 Linux
```

接下来，继续安装 obsidian app。

# 创建 obsidian 仓库

同样地，ios 应用商店下载后打开 obsidian，此时没有任何 vault，首先手动创建一个，比如名称为 notebook（下文中的所有 notebook 都可以改为你自己的仓库名称）。此时，你只是创建了一个空的仓库，我们需要让其与 github 同步。

> PS: 我第一次是单独创建了一个vault，然后在vault下面在拉取了git仓库，目录层级有点多，比较麻烦，这个方案会将git仓库的内容直接放在对应目录下。

# 创建 ssh key 并授权给 github

我的笔记仓库托管在 github，处于安全考虑，github 禁止使用 http 连接，需要改为 ssh。

打开 iSH app，创建 ssh key，需要安装几个软件：

```shell
apk add git
apk add openssh
```

依次执行上边的命令安装 git、openssh，耐心等待安装完成。

然后，执行以下命令生成 ssh key：

```shell
ssh-keygen -t ed25519 -C "<你的邮箱>"
```

接着，拷贝生成的公钥：

```shell
cat ~/.ssh/id_ed25519.pub
```

登录 github，点击用户头像，在 `setting` -> `SSH and GPG keys` -> `New SSH key` 新建一个授权的key并粘贴刚才拷贝的公钥，保存即可。

测试一下在 iSH 中能否正常连接 github：

```shell
localhost:~# ssh -T git@github.com
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

输出上述信息说明 ssh 连接成功。

# 配置 git 环境

上一步安装了 git，现在来配置 git 环境。

打开 iSH，依次执行如下命令：

```shell
git config --global user.name "你的github用户名"
git config --global user.email "你的github邮箱"
```

此外，还需要添加安全目录，否则git可能出错：

```shell
git config --global --add safe.directory /root/obsidian/notebook
```

> PS: 这里不操作的话问题不大，在第一次执行`git pull`的时候，会提醒你，直接复制粘贴更方便

# 同步 github 仓库到 iSH

现在，你可以在 iSH pull github 仓库代码了。

首先，打开 iSH，创建一个 `obsidian` 目录：

```shell
cd ~ && mkdir obsidian
```

然后，挂载 obsidian app 的文件存储目录到刚才创建的 `obsidian` 目录:

```shell
mount -t ios . obsidian
```

这里的命令解释：
- `mount`是挂载命令
- `-t` 指定文件格式`ios`
- `.` 当前目录
- `obsidian`刚刚创建的目录

挂载的命令是在网上找的，至于为啥是`ios`格式，可以通过命令`df -T`来查看

```shell
localhost:~/obsidian/notebook# df -T
Filesystem           Type       1K-blocks      Used Available Use% Mounted on
/private/var/mobile/Containers/Data/Application/826FB5AE-9DE7-4C73-9045-5049E3xxxxx/Documents
                     ios        249880148 227563964  22316184  91% /root/obsidian
/private/var/mobile/Containers/Shared/AppGroup/E90D8F8C-AE29-4A9F-9388-F9EF351xxxxx/roots/default/data
                     fake       249880148 227563964  22316184  91% /
localhost:~/obsidian/notebook# 
```

iSH 会弹出一个窗口，在里边选择 `Obsidian` 文件夹即可，不需要选择 `notebook` 仓库，这样就可以访问多个仓库。

到此，git配置完成，现在可以在 iSH 中拉取git仓库了。

首先，复制 github 仓库的 ssh 地址。

然后，进入 `obsidian/notebook` 文件夹：

```shell
cd obsidian/notebook/
```

删除下边的 `.obsidian` 文件夹，这是 obsidian 为其仓库创建的，这里先删除，保证这个目录是空的。

接着，进入上层目录：

```shell
cd ..
```

克隆仓库：

```shell
git clone 你的仓库ssh地址 notebook
```

表示将 github 仓库下的文件克隆到 notebook 目录。

耐心等待克隆完成，如果失败了重试即可。

> PS: 上面说的，如果不在仓库地址后面加 notebook ，就会在notebook下面新建仓库目录，目录层级会多一层

现在，打开 obsidian app，可以看到数据成功同步了过来。

# 常用操作

现在，你可以在 obsidian app 中记录笔记了，一些日常操作包括：

> 这些操作都需要打开 iSH app，进入 `~/obsidian/notebook` 操作。

1、同步仓库 pc端修改了笔记，ios可以同步仓库：

```shell
git pull origin main
```

2、提交更改 ios上修改了笔记，需要提交到 git 仓库：

```shell
git add .
git commit -m '描述'
git push origin main
```

# 快捷操作

同步数据需要打开iSH app，执行拉代码，可以配置快捷命令。
根据 `linux` 的特性，可以在打开iSH app后，自动执行相关操作，比如直接进入我们的相应的目录，打开软件自动拉取最新数据
linux 下，系统会自动执行家目录下面(直接执行命令`cd`即可到家目录下)的 `.profile` 文件，再配置 `.ashrc` 文件，即可完成需求
直接复制粘贴下面的命令：
```shell
cd
cat > ~/.profile <<EOF
if [ -f ~/.ashrc ]; then
    source ~/.ashrc
fi
EOF
cat > ~/.ashrc <<EOF
cd /root/obsidian/notebook
git pull
alias gl='git pull'
EOF
```

> PS: 简单解释下命令的作用，先cd到家目录下，然后创建`.profile`，内容的作用就是开启时执行`.ashrc`里的命令，`.ashrc`里的命令意思是到`/root/obsidian/notebook`目录下，然后执行`git pull`命令，最后做了一个别名，即在命令行输入`gl`，等同于执行`git pull`命令，因为在手机上操作还是能简化点比较好

# git 配置

当文件名含有中文的时候，git 显示会异常，需要执行下面命令

```shell
git config --global core.quotepath false
```

> PS 不过还是建议尽量使用英文做标题，也可以锻炼英语水平，也能避免很多奇奇怪怪的问题

# 总结

使用 iSH app 可以在 ios 上模拟一个 Linux 环境，并同步 git 仓库，这非常利于 obsidna 仓库的同步。配置 github 的操作稍有些麻烦，不过配置好后就很方便了。如果需要在 iPhone、iPad 上使用 obisidan 阅读、编写笔记，值得一试。
