---
title: "将 Bash 函数作为命令使用"
date: "2024-04-03T17:11:17+08:00"
lastmod: "2024-04-03T17:11:17+08:00"
categories: ["Linux"]
slug: "bash-source-function-command"
draft: false
---

## 函数作为命令行命令

### 配置函数脚本

```bash
# $ cat ~/.bashrc 
# .bashrc

# Source global definitions
if [ -f /etc/bashrc ]; then
        . /etc/bashrc
fi

# Uncomment the following line if you don't like systemctl's auto-paging feature:
# export SYSTEMD_PAGER=

# User specific aliases and functions
. ~/.utils/toolsfunc.sh
```

然后把脚本放到对应目录就可以执行了


