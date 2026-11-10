---
title: "SSH 远程执行命令时，为什么环境变量不一样"
date: "2026-11-01T00:00:00+08:00"
lastmod: "2026-11-01T00:00:00+08:00"
description: "从 SSH 远程命令找不到程序的问题，梳理 Bash 的登录与交互模式、启动文件和环境变量的传递边界。"
categories: ["Linux"]
tags: ["SSH", "Bash", "Shell"]
slug: "ssh-remote-command-environment"
draft: false
---

读到 feihu 的[《ssh连接远程主机执行脚本的环境变量问题》](https://feihu.me/blog/2014/env-problem-when-ssh-executing-command-on-remote/)，里面的问题很具体：先登录远程机器再运行脚本，一切正常；把脚本直接放在 `ssh` 命令后面，却报 `command not found`。

原文发表于 2014 年，测试环境是 SUSE Linux Enterprise。它从 Bash 启动方式寻找原因，这个方向仍然适用。不过，要把它作为今天排查问题的参考，还需要补上 SSH 的特殊处理，并区分终端、shell 模式和脚本解释器。这篇笔记按 Bash 与 OpenSSH 的文档重新整理；其他 shell 需要查各自的启动规则。

## 同一个用户，不代表同一套环境

先看登录后再运行脚本的方式：

```sh
# 在本地终端登录，再在远程执行脚本
ssh user@host
~/bin/job.sh
```

另一种方式是在本地直接提交远程命令：

```sh
ssh user@host '~/bin/job.sh'
```

在常见的 Bash 账户配置下，前一种方式会进入交互式登录 shell；后一种方式由 `sshd` 使用账户配置的 shell，通过 `-c` 执行命令字符串。这里至少涉及本地 shell、远程命令 shell，以及脚本可能另行启动的解释器三个环节。[OpenSSH 的 sshd 手册](https://man.openbsd.org/sshd#LOGIN_PROCESS)说明了远程 shell 的选择和执行过程。

因此，登录时添加到 `PATH` 的目录，不一定会出现在一次新的远程命令会话里。另一个已经登录的终端中执行过 `export`，也不会修改以后由 `sshd` 创建的会话环境。

上面的单引号还有一个作用：让 `~` 留到远程解析。类似地，查看远程路径应写成：

```sh
ssh user@host 'printf "%s\n" "$PATH"'
```

如果外层改成双引号，`$PATH` 会先在本地展开，看到的就可能是本机路径。下面的远程命令示例假定账户 shell 能解析这些 Bourne 风格语法。

## 登录与交互是两个独立的维度

对 Bash 来说，登录模式由启动方式决定，例如 `argv[0]` 以 `-` 开头，或显式传入 `--login` / `-l`；并不是“输入过密码”就算登录 shell。交互模式可以通过 `-i` 显式开启；通常自动判定还要求没有 `-c` 或脚本文件参数，并且标准输入和标准错误连接终端。[Bash 启动参数](https://www.gnu.org/software/bash/manual/html_node/Invoking-Bash.html)

常用的启动规则可以整理成下面这样。表中假定以 `bash` 名称启动，没有使用 `--noprofile`、`--norc` 等抑制选项，也不讨论特权执行模式。

| 调用场景 | 登录 | 交互 | 主要启动文件 |
| --- | --- | --- | --- |
| 在终端中运行 `bash -l` | 是 | 是 | `/etc/profile`，再读用户登录文件 |
| `bash -lc 'command'` | 是 | 否 | 登录文件；若设置了 `BASH_ENV`，还会处理它 |
| 在终端中直接运行 `bash` | 否 | 是 | `~/.bashrc` |
| 普通的 `bash script.sh` 或 `bash -c 'command'` | 否 | 否 | `BASH_ENV` 指定的文件（若设置） |

“用户登录文件”是按 `~/.bash_profile`、`~/.bash_login`、`~/.profile` 的顺序，读取第一个存在且可读的文件，不是依次读取全部文件。Bash 本身也不会因为是登录 shell 就自动读取 `~/.bashrc`；常见做法是在登录文件中显式加载它。

`/etc/bash.bashrc`、`/etc/bashrc` 等系统级 rc 文件则与发行版、编译配置或其他启动文件的显式调用有关，不能把某台机器上的顺序当作所有 Bash 的固定规则。`.bash_login` 也是有效的 Bash 登录文件，没有必须禁用它的规则。[Bash 启动文件](https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html)、[Debian 的 Bash 编译配置补丁](https://sources.debian.org/patches/bash/5.2.37-2/deb-bash-config.diff/)

## SSH 的两个容易误判的地方

### `ssh -t` 不会自动让 Bash 进入交互模式

`-t` 的作用是申请伪终端（PTY）。如果仍然给 SSH 提供了命令，远程 Bash 通常仍然通过 `-c` 执行它，没有因此得到 `-i`。所以，“分配了终端”和“这是交互式 Bash”要分开检查。[OpenSSH 的 `-t` 参数](https://man.openbsd.org/ssh#t)

确认远程账户使用 Bash 后，可以比较：

```sh
ssh -T user@host 'printf "flags=%s\n" "$-"; if [ -t 0 ]; then echo tty=yes; else echo tty=no; fi'
ssh -tt user@host 'printf "flags=%s\n" "$-"; if [ -t 0 ]; then echo tty=yes; else echo tty=no; fi'
```

第二条用 `-tt`，是为了在本地没有终端时也强制请求 PTY；仍取决于服务器是否允许。在通常配置下，`tty` 会从 `no` 变成 `yes`，但两次 `$-` 都没有 `i`。判断当前 Bash 是否交互，检查 `$-` 中有没有 `i`；判断是否登录，使用 `shopt -q login_shell`。[Bash 交互模式检测](https://www.gnu.org/software/bash/manual/html_node/Is-this-Shell-Interactive_003f.html)

### 非交互的 SSH Bash 也可能读取 `.bashrc`

Bash 对远程 shell 守护进程有特殊处理：当它识别出自己由 `sshd` 等启动、处于相应的非交互场景时，会尝试读取 `~/.bashrc`。以 `sh` 名称启动时不适用这条规则。因此，不能把 `ssh host command` 简单归为“只读 `BASH_ENV`”的普通脚本场景；具体行为还受调用方式和构建配置影响。[Bash 维护者提供的手册：启动文件](https://tiswww.case.edu/php/chet/bash/bashref.html#Bash-Startup-Files)

即使读到了 `.bashrc`，文件里的配置也不一定全部执行。比如这样的提前返回：

```bash
case $- in
    *i*) ;;
    *) return ;;
esac

# 写在这里的 PATH 设置，非交互 shell 执行不到
export PATH="$HOME/.local/bin:$PATH"
```

遇到这种情况，需要检查配置的位置和执行条件。把终端配色、提示符、补全等整套交互配置搬进脚本，并不能稳定地解决环境问题。

## 先确认是哪一层找不到命令

如果远程账户 shell 是 Bash，可以在出错的同类会话中查看：

```sh
ssh user@host '
    printf "bash=%s\nflags=%s\n" "${BASH_VERSION-}" "$-"
    if [ -n "${BASH_VERSION-}" ]; then
        if shopt -q login_shell; then echo login=yes; else echo login=no; fi
    fi
    printf "PATH=%s\n" "$PATH"
    command -v app
'
```

把 `app` 换成实际的程序名。若错误发生在 `job.sh` 内部，还应在脚本报错位置之前查看 `PATH` 和 `command -v app`，因为脚本可能使用另一个解释器，或者修改过环境。`$SHELL` 通常反映账户配置的 shell，不能单独证明当前脚本由谁解释。

脚本的 shebang 也要一起看：

```sh
#!/bin/sh
```

和：

```bash
#!/bin/bash
```

不是同一份启动约定。`/bin/sh` 不保证指向 Bash；即使指向 Bash，以 `sh` 名称运行时，也不会按普通非交互 Bash 的方式读取 `BASH_ENV`。显式执行 `sh job.sh` 或 `bash job.sh` 时，则由命令里指定的解释器读取脚本，不能指望 shebang 改变这一选择。[Bash 的 shell 脚本说明](https://www.gnu.org/software/bash/manual/html_node/Shell-Scripts.html)

`#!/usr/bin/env bash` 又多了一步：`env` 需要从当时的 `PATH` 查找 Bash。在讨论路径问题时，这一步也不能忽略。

## 把任务需要的环境写明确

如果只缺少一个程序的搜索路径，最直接的处理是在任务入口设定它，或使用程序的绝对路径。例如，下面的路径只是示例，需要换成远程机器的实际安装目录：

```sh
ssh user@host 'PATH=/opt/myapp/bin:/usr/local/bin:/usr/bin:/bin; export PATH; exec "$HOME/bin/job.sh"'
```

如果任务依赖多个变量，可以放在专用文件中，例如 `~/.config/myjob/env.sh`：

```sh
export PATH=/opt/myapp/bin:/usr/local/bin:/usr/bin:/bin
export APP_ENV=production
```

然后显式加载，再执行脚本：

```sh
ssh user@host '. "$HOME/.config/myjob/env.sh" && exec "$HOME/bin/job.sh"'
```

这样，脚本得到的是为这个任务准备的环境。配置文件应当是自己管理、可信且兼容当前 shell 的代码。

对于确定由 Bash 执行的任务，也可以让 `BASH_ENV` 指向这份专用文件：

```sh
ssh user@host 'BASH_ENV="$HOME/.config/myjob/env.sh" /bin/bash "$HOME/bin/job.sh"'
```

这条命令是在远程为接下来启动的 Bash 设置变量。仅在本地 `export BASH_ENV=...`，不会自动让远程收到它；SSH 环境变量转发需要客户端与服务端配置共同允许，而且传过去的只是路径字符串，不是文件内容。[SendEnv](https://man.openbsd.org/ssh_config#SendEnv)、[AcceptEnv](https://man.openbsd.org/sshd_config#AcceptEnv)

还有一种明确的需求是：这个任务就是要使用远程账户的登录配置。这时可以显式启动登录 Bash：

```sh
ssh user@host "exec /bin/bash -lc 'exec ~/bin/job.sh'"
```

这里的 `-l` 负责读取登录配置，`-c` 负责执行后面的命令。它仍然是非交互 Bash，也不保证执行 `.bashrc` 中被交互检查挡住的配置。如果登录文件会输出文字、启动其他程序或覆盖变量，这些行为也会跟着发生。因此，自动化任务使用哪一种入口，要根据它实际需要的环境来选。

## 复核范围

2026-11-01 复核了上述文档规则，并在本机 Bash 3.2.57 中做了隔离实验：有 PTY 的 `bash -c` 仍不带交互标志 `i`；`bash --noprofile -lc` 仍会读取指定的 `BASH_ENV`；同一 Bash 以 `sh` 名称启动时不读取它。这些实验没有改动用户的启动文件。

这里没有连接实际远程服务器验证 SSH 启动文件。某台服务器是否读取 `.bashrc`、发行版追加了哪些系统配置，仍需在那台机器上按实际账户和命令检查。
