---
title: "Bash PS1、PS2、PS3、PS4 提示符笔记"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["Linux"]
slug: "bash-prompt-variables"
draft: false
---

## SHELL 提示符  PS1/PS2/PS3/PS4

### 默认值定义

#### BASH含义：

```bash
PS1    The value of this parameter is expanded (see PROMPTING below) and used as the primary prompt string.  The default value is ``\s-\v\$ ''.
PS2    The value of this parameter is expanded as with PS1 and used as the secondary prompt string.  The default is ``> ''.
PS3    The value of this parameter is used as the prompt for the select command (see SHELL GRAMMAR above).
PS4    The value of this parameter is expanded as with PS1 and the value is printed before each command bash displays during an execution trace.  The first character of PS4 is repli‐
      cated multiple times, as necessary, to indicate multiple levels of indirection.  The default is ``+ ''.
```

#### 默认系统变量
```bash
[root@local ~]# echo -e "\$PS1默认值: $PS1\n\$PS2默认值: $PS2\n\$PS3默认值: $PS3\n\$PS4默认值: $PS4"
$PS1默认值: [\u@\h \W]\$ 
$PS2默认值: > 
$PS3默认值: 
$PS4默认值: + 
```

#### 中文解释

PS1: 是在命令行提示的，例如`[root@local ~]#`
PS2: 换行符提示符，默认 `\`
PS3: 命令`select`的提示符 默认为空
PS4: 代码设置`debug`模式下的提示符 默认为 `+`

### 使用场景

#### PS1

PS1是使用最多，修改最多的，一般是普通的修改和`oh my zsh`的安装



| 字符 | 描述                                                         |
| :--- | :----------------------------------------------------------- |
| \a   | 铃声字符                                                     |
| \d   | 格式为“日 月 年”的日期                                       |
| \e   | ASCII转义字符                                                |
| \h   | 本地主机名                                                   |
| \H   | 完全合格的限定域主机名                                       |
| \j   | shell当前管理的作业数                                        |
| \1   | shell终端设备名的基本名称                                    |
| \n   | ASCII换行字符                                                |
| \r   | ASCII回车                                                    |
| \s   | shell的名称                                                  |
| \t   | 格式为“小时:分钟:秒”的24小时制的当前时间                     |
| \T   | 格式为“小时:分钟:秒”的12小时制的当前时间                     |
| \@   | 格式为am/pm的12小时制的当前时间                              |
| \u   | 当前用户的用户名                                             |
| \v   | bash shell的版本                                             |
| \V   | bash shell的发布级别                                         |
| \w   | 当前工作目录                                                 |
| \W   | 当前工作目录的基本名称                                       |
| \!   | 该命令的bash shell历史数                                     |
| \#   | 该命令的命令数量                                             |
| \$   | 如果是普通用户，则为美元符号`$`；如果超级用户（root 用户），则为井号`#`。 |
| \nnn | 对应于八进制值 nnn 的字符                                    |
| \\   | 斜杠                                                         |
| \[   | 控制码序列的开头                                             |
| \]   | 控制码序列的结尾                                             |

