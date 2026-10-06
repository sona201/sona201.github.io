---
title: "SED 查询文本与行号"
date: "2024-07-13T16:14:33+08:00"
lastmod: "2024-07-13T16:14:33+08:00"
categories: ["Linux"]
slug: "sed-command"
draft: false
---

#linux  #command #sed


#### sed 打印匹配内容
```
# sed -n -e '/build/p' filename
[cli_rebuild]

p -打印行
n -
e --e<script>或--expression=<script>：以选项中的指定的script来处理输入的文本文件；
```

####  sed 打印匹配内容行号
```
sed -n -e '/build/=' filename
```

#### sed 打印匹配内容和行号
```
# sed -n -e '/build/p' -e '/build/=' filename
[cli_rebuild]
28
```

#### 打印文件中间几行，显示 5-10 行中间的内容
```shell
sed -n "3p" filename
sed -n '5,10p' filename
```


#### 打印文件某一行到最后一行
```shell
sed -n '5,$p' filename
```

#### 某个时间段日志，`2020-07-17T18:15:52` 日志中的时间格式，并且存在该时间

```shell
sed -n "/2020-07-17T18:15:52/,/2020-07-17T22:52:45/p" filename
```