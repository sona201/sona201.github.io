---
title: "Bash while read 逐行处理"
date: "2023-02-27T00:26:22+08:00"
lastmod: "2023-02-27T00:26:22+08:00"
categories: ["Linux"]
slug: "bash-while-read-lines"
draft: false
---

```bash
get_pod="NAME    READY   STATUS    RESTARTS   AGE
pod-a   2/2     Running   0          6h
pod-b   2/2     Running   0          5h
pod-c   2/2     Running   0          4h
pod-d   2/2     Running   0          3h"

IFS="\n"

while read line;
do echo $line;
done <<< $get_pod
```