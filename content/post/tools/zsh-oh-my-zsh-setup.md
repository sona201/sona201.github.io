---
title: "Zsh 与 Oh My Zsh 安装配置笔记"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["tools"]
slug: "zsh-oh-my-zsh-setup"
draft: false
---

# zsh安装配置使用

[ohmyz 官网 ](https://ohmyz.sh/)

> Zsh 是什么

- `Zsh` 是一款强大的虚拟终端，既是一个系统的虚拟终端，也可以作为一个脚本语言的交互解析器。
- 打开终端，在终端上输入 `zsh --version` 这个命令来查看我们的电脑上是否安装了 `Zsh`
- 终端查询版本为： `zsh 5.7.1 (x86_64-apple-darwin19.0)`
- 查看系统当前 `shell`，命令行执行: `echo $SHELL`

> Oh My Zsh 是什么

- `Oh My Zsh` 是一款社区驱动的命令行工具，正如它的主页上说的，`Oh My Zsh` 是一种生活方式。它基于 `zsh` 命令行，提供了主题配置，插件机制，已经内置的便捷操作。给我们一种全新的方式使用命令行。
- `Oh My Zsh` 是基于 `zsh` 命令行的一个扩展工具集，提供了丰富的扩展功能。
- 安装 `Oh My Zsh` 前提条件：必须已安装 `zsh`
- 以下操作都是基于 `Mac` 系统。

## 安装oh-my-zsh

### verify zsh

查看系统是否有`zsh shell`

```bash
cat /etc/shells | grep zsh
```

如果当前环境shell已经有了zsh请自动忽略这一步

```
brew install zsh  # mac os 的homebrew
sudo apt install zsh  # ubuntu
sudo yum install zsh  # centos
```

[oh-my-zsh](https://github.com/robbyrussell/oh-my-zsh) github网址

### 安装oh-my-zsh

这里提供三种方法安装oh-my-zsh

- 1、使用wget安装：

```
sh -c "$(wget -O- https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
```

- 2、使用curl安装：

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
```

- 3、手动安装：

```bash
curl -Lo install.sh https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh
sh install.sh
```

执行脚本会有命令行交互，询问是否要启用`zsh shell`，回车`y`。开始使用

## oh-my-zsh插件安装

[部分zsh插件地址](https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins)

- 安装命令行语法高亮插件

[官方安装README](https://github.com/zsh-users/zsh-syntax-highlighting/blob/master/INSTALL.md)

1. cllone项目到`$ZSH_CUSTOM/plugins`文件夹下 (默认为 `~/.oh-my-zsh/custom/plugins`)

```
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
```

2. 在 `Oh My Zsh` 的配置文件 (`~/.zshrc`)中设置:

```
plugins=(其他插件 zsh-syntax-highlighting)
```

3. 运行 `source ~/.zshrc` 使配置文件生效

- 安装命令行自动补全插件

[官方安装README](https://github.com/zsh-users/zsh-autosuggestions/blob/master/INSTALL.md)

1. clone项目到`$ZSH_CUSTOM/plugins`文件夹下 (默认为 `~/.oh-my-zsh/custom/plugins`)

```
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
```

2. 在 `Oh My Zsh` 的配置文件 (`~/.zshrc`)中设置:

```
plugins=(其他插件 zsh-autosuggestions)
```

3. 运行 `source ~/.zshrc ` 使配置文件生效

### oh-my-zsh主题替换

`oh-my-zsh`提供了很多主题，可以通过命令查看当前使用的主题：

```bash
ls ~/.oh-my-zsh/themes
```

可以通过编辑`.zshrc`文件来修改你的主题

```bash
vi ~/.zshrc
```

## 命令行终端显示乱码

基础操作，在`~/.zshrc`中添加如下配置
```
export LC_ALL=en_US.UTF-8  
export LANG=en_US.UTF-8
```
但实际中，默认都会有以上配置

终极问题：`Mac terminal`终端或`iterm2`出现无法显示字符集，显示为问号：

问题根本原因是字体的缺失，或者解释为当前字体无法显示符号，随即解决方法就是安装字体：

```bash
# clone
git clone https://github.com/powerline/fonts.git
# install
cd fonts
./install.sh
```

安装完成后再终端选择字体，字体名称：`Meslo LG S DZ Regular for Powerline`，或者相似的，包含`Powerline`即可。

同理，在ide上也是，ide的命令行终端显示字体修改后即可同样正常显示