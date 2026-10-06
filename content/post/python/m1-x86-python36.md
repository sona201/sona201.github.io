---
title: "在 Mac M1 上安装 x86 Python 3.6"
date: "2024-11-23T00:50:09+08:00"
lastmod: "2024-11-23T00:50:09+08:00"
categories: ["python"]
slug: "m1-x86-python36"
draft: false
---

[原文摘自stackoverflow](https://stackoverflow.com/questions/71862398/install-python-3-6-on-mac-m1)
[参考连接1](https://tocandraw.com/coding/python/1703/)
[参考连接2](https://notemi.cn/installing-python-on-mac-m1-pyenv.html)

### 前提摘要

> 现在苹果的电脑都是arm架构的芯片，功耗是大大减小了，续航得到了很大的提高，但芯片的架构导致程序不支持就很蛋疼，现实里就是需要接手一个python老项目，就是用的老框架，一些旧依赖库甚至需要降版本才能安装运行，很巧我就遇到了，不然也不会有这篇文章。

### 背景

公司的一个老项目，本来跑的好好的，但用的不顺手，想改动下，拉下代码，怎么都跑不起来。我按照我以前的经验来安装遇到一堆问题，各种搜索，一直没有彻底解决，请教了同事，他跟我说arm芯片的两种比较好的解决方案就是安装x86的解释器，或者搞个容器（linux）环境，远程部署。
容器部署确实一劳永逸，但同事给我演示的时候发现`vscode`没有python3.6版本，于是我决定尝试下安装x86的python解释器

### 相关介绍

总的来说，arm的芯片可以安装arm架构的二进制文件（废话），还可以通过 rosetta 来安装x86的二进制文件，但是他们的路径不一样，这里同样包括`homebrew`，有`arm`和`x86`两个版本，对应的路径分别是
```
/usr/local/bin/brew  # x86
/opt/homebrew/bin/brew  # arm
```

目前支持rosetta的终端是iterm，可以直接勾选

#### 安装Homebrew

#### 安装pyenv

#### 安装python3.6

确认python3.6是x86版本
```
Python 3.6.15 (default, Oct 30 2024, 01:16:00) 
[GCC Apple LLVM 15.0.0 (clang-1500.3.9.4)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import platform
>>> print(platform.machine()) 
x86_64
>>> 
```

#### 遇到的问题

> # [Error in anyjson setup command: use_2to3 is invalid](https://stackoverflow.com/questions/72414481/error-in-anyjson-setup-command-use-2to3-is-invalid)

在安装python依赖库，一个很老的库`django-celery`报错，暂时不想替换别的库，发现需要降级`setuptools`

1. 第一步
```python
pip install "setuptools<58.0.0"
```
2. 第二步
```python
pip install django-celery
```

就是因为这个库，才需要降级到python3.6，因为这个库里有用到了一个关键字`async`，在python3.7之后`async`已经变成python官方关键字，所以这个库不能在3.6以上的python里跑

后面对应的依赖库还是能尽量升级就升级，不然迁移两行泪


```python
#Install Rosetta
/usr/sbin/softwareupdate --install-rosetta --agree-to-license

# Install x86_64 brew
arch -x86_64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"

# Set up x86_64 homebrew and pyenv and temporarily set aliases
alias brew86="arch -x86_64 /usr/local/bin/brew"
alias pyenv86="arch -x86_64 pyenv"

# Install required packages and flags for building this particular python version through emulation
brew86 install pyenv gcc libffi gettext

# -------------- change to openssl@1.1 here and others as well ----------+
#                                                                        ↓
export CPPFLAGS="-I$(brew86 --prefix libffi)/include -I$(brew86 --prefix openssl@1.1)/include -I$(brew86 --prefix readline)/lib"
export CFLAGS="-I$(brew86 --prefix openssl@1.1)/include -I$(brew86 --prefix bzip2)/include -I$(brew86 --prefix readline)/include -I$(xcrun --show-sdk-path)/usr/include -Wno-implicit-function-declaration" 
export LDFLAGS="-L$(brew86 --prefix openssl@1.1)/lib -L$(brew86 --prefix readline)/lib -L$(brew86 --prefix zlib)/lib -L$(brew86 --prefix bzip2)/lib -L$(brew86 --prefix gettext)/lib -L$(brew86 --prefix libffi)/lib"

# Providing an incorrect openssl version forces a proper openssl version to be downloaded and linked during the build
export PYTHON_BUILD_HOMEBREW_OPENSSL_FORMULA=openssl@1.1

# Install Python 3.6
pyenv86 install --patch 3.6.15 <<(curl -sSL https://raw.githubusercontent.com/pyenv/pyenv/master/plugins/python-build/share/python-build/patches/3.6.15/Python-3.6.15/0008-bpo-45405-Prevent-internal-configure-error-when-runn.patch\?full_index\=1)
```