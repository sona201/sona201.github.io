---
title: "Bash trap 捕获 SIGINT 的示例"
date: "2023-10-06T18:09:39+08:00"
lastmod: "2023-10-06T18:09:39+08:00"
categories: ["Linux"]
slug: "bash-trap-sigint"
draft: false
---

[user@local ~]$ cat trap.sh
#!/bin/bash
trap "echo xxxxx; exit" SIGINT
mkdir -p /home/username/traptest/docs
while :
do
    echo $(date) Writing fortune to /home/username/traptest/docs/index.html
    echo "do something $(date)" > /home/username/traptest/docs/index.html
    sleep 10
done