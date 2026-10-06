---
title: "macOS Spotlight 索引与键盘长按设置"
date: "2023-02-27T17:00:11+08:00"
lastmod: "2023-02-27T17:00:11+08:00"
categories: ["tools"]
slug: "macos-spotlight-key-repeat"
draft: false
---

[source link](https://electrictoolbox.com/disable-spotlight-indexing-mac-osx/)

How to switch off Spotlight indexing

Open up a Terminal window and copy and paste this:

```bash
sudo mdutil -i off
```
How to subseqently enable Spotlight indexing
If you want to allow Spotlight to index your files again, copy and paste this:

```bash
sudo mdutil -i on
```

It may take some time to index so best to do this when you don’t need to use your Mac for a while.

Why switch off Spotlight indexing?
As mentioned at the start of this post, the CPU hogging was starting to get pretty annoying and I really only use Spotlight for launching apps. It’s great being able to Command+Space and start typing in the app name and hit return when it’s found what I want.


mac 自带键盘长按时，显示特殊符号

当您在 Mac 上长按键盘上的某些字母键（比如 A, E, O, U, N, S, C, Z 等）时，系统会弹出一个 重音符号/特殊字符选择菜单，让您可以方便地输入带有变音符号的字符，这在输入欧洲语言（如法语、德语、西班牙语）时非常有用。
```
defaults write -g ApplePressAndHoldEnabled -bool false
```
