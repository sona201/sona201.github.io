---
title: "macOS Rime 安装与中英文切换配置"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["tools"]
slug: "rime-macos-install"
draft: false
---

## 简介
rime是一款输入法，自定义配置的，为啥要搞这个，因为现在的信息泄露太严重了，实在忍不住了

## 安装
[官网下载地址](https://rime.im/download/)

mac 安装 `Install via Homebrew: brew install --cask squirrel`

## 开源配置
### 配置管理工具
[一个叫东风破的配置管理插件](https://github.com/rime/plum)

```bash
curl -fsSL https://raw.githubusercontent.com/rime/plum/master/rime-install | bash
```
### 别人的配置
[一个叫雾凇拼音的配置](https://github.com/iDvel/rime-ice)

通过东风破plus安装
```
cd plum
bash rime-install iDvel/rime-ice:others/recipes/full
```

### mac 增加 rime 输入法

系统配置 -> 键盘 -> 文字输入 -> 输入法 -> 编辑

![rime_add1](/images/rime_add1.png)
![rime_add2](/images/rime_add2.png)

### 使用习惯
日常习惯的搜狗的shift中英文切换方式，但rime需要手动配置 \
[配置链接](https://github.com/iDvel/rime-ice/issues/133)

点击鼠须管logo，点击用户设定，默认打开路径`/Users/example/Library/Rime/`目录，打开`default.yaml`文件

参考下列配置
```
# 中西文切换
#
# 【good_old_caps_lock】 CapsLock 切换到大写或切换中英。
# （macOS 偏好设置的优先级更高，如果勾选【使用大写锁定键切换“ABC”输入法】则始终会切换输入法）
#
# 切换中英：
# 不同的选项表示：打字打到一半时按下了 CapsLock、Shift、Control 后： 
# commit_code  上屏原始的编码，然后切换到英文
# commit_text  上屏拼出的词句，然后切换到英文
# clear        清除未上屏内容，然后切换到英文
# inline_ascii 无输入时，切换中英；有输入时，切换到临时英文模式，按回车上屏后回到中文状态
# noop         屏蔽快捷键，不切换中英，但不要屏蔽 CapsLock
ascii_composer:
  good_old_caps_lock: true  # true | false
  switch_key:
    Caps_Lock: clear  # commit_code | commit_text | clear
    Shift_L: commit_code     # commit_code | commit_text | inline_ascii | clear | noop
    Shift_R: commit_code     # commit_code | commit_text | inline_ascii | clear | noop
    Control_L: noop   # commit_code | commit_text | inline_ascii | clear | noop
    Control_R: noop   # commit_code | commit_text | inline_ascii | clear | noop
```
将下面的`shift_L`/`Shift_R` 改为你想要的配置，我改成了`commit_code`

mac自带的切换输入法是 `Lock`，将大写切换键改成 `Shift-Lock`

这样就基本没有使用的不适