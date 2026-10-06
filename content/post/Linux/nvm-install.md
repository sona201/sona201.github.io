---
title: "NVM 安装与常用命令"
date: "2024-07-06T01:17:38+08:00"
lastmod: "2024-07-06T01:17:38+08:00"
categories: ["Linux"]
slug: "nvm-install"
draft: false
---

#nvm #install 

[nvm-github](https://github.com/nvm-sh/nvm#installing-and-updating)

## 安装或更新

### 安装或更新脚本

安装 `nvm`或者更新`nvm`可以直接执行下列命令

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```

```bash
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```

Running either of the above commands downloads a script and runs it. The script clones the nvm repository to `~/.nvm`, and attempts to add the source lines from the snippet below to the correct profile file (`~/.bash_profile`, `~/.zshrc`, `~/.profile`, or `~/.bashrc`).
脚本逻辑：将 nvm 存储库克隆到“~/.nvm”，并尝试将下面代码片段中的源代码行添加到正确的配置文件（“~/.bash_profile”、“~/.zshrc”、“~/.profile”） `，或`~/.bashrc`）。

```bash
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
```

##### nvm 常用命令
- `nvm install stable` 安装最新稳定版`node`
- `nvm install <version>` 安装指定版本，如：安装`v14.4.0`，`nvm install v14.4.0`
- `nvm uninstall <version>` 删除已安装的指定版本，语法与`install`类似
- `nvm use <version>` 切换使用指定的版本`node`
- `nvm ls` 列出所有安装的版本
- `nvm alias default <version>` 如: `nvm alias default v11.1.0`