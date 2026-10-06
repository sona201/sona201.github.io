---
title: "命令参数 - 与标准输入输出笔记"
date: "2023-02-27T00:26:22+08:00"
lastmod: "2023-02-27T00:26:22+08:00"
categories: ["Linux"]
slug: "shell-dash-standard-input"
draft: false
---

## Chapter 3. Special Characters

[link](https://tldp.org/LDP/abs/html/special-chars.html)

搜到一个命令

```bash
cat yaml | kubectl replace -f -
```

这让我想到我平时用的命令
```bash
cat file | vim -
```

原本以为 `-` 是vim的一个特殊用法，让我意识到这应该是shell的用法，而不是vim的特定方法

网上就搜到上面的文章，主要是讲特殊字符meta字符，大概意思就是

`-` 会转发到 stdin/stdout

> redirection from/to stdin or stdout [dash].

example
```
bash$ cat -
abc
abc

...

Ctl-D
```

## 实际运用
Backup of all files changed in last day

```bash

#!/bin/bash

#  Backs up all files in current directory modified within last 24 hours
#+ in a "tarball" (tarred and gzipped file).

BACKUPFILE=backup-$(date +%m-%d-%Y)
#                 Embeds date in backup filename.
#                 Thanks, Joshua Tschida, for the idea.
archive=${1:-$BACKUPFILE}
#  If no backup-archive filename specified on command-line,
#+ it will default to "backup-MM-DD-YYYY.tar.gz."

tar cvf - `find . -mtime -1 -type f -print` > $archive.tar
gzip $archive.tar
echo "Directory $PWD backed up in archive file \"$archive.tar.gz\"."


#  Stephane Chazelas points out that the above code will fail
#+ if there are too many files found
#+ or if any filenames contain blank characters.

# He suggests the following alternatives:
# -------------------------------------------------------------------
#   find . -mtime -1 -type f -print0 | xargs -0 tar rvf "$archive.tar"
#      using the GNU version of "find".


#   find . -mtime -1 -type f -exec tar rvf "$archive.tar" '{}' \;
#         portable to other UNIX flavors, but much slower.
# -------------------------------------------------------------------


exit 0
```