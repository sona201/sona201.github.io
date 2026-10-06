---
title: "AWK 文本替换笔记"
date: "2024-07-21T22:52:19+08:00"
lastmod: "2024-07-21T22:52:19+08:00"
categories: ["Linux"]
slug: "awk-text-replacement"
draft: false
---

#linux #awk #command 

# awk用法之：文本替换

awk用法之：文本替换

awk的sub/gsub函数用来替换字符串，其语法格式是：

```shell
sub(/regexp/, replacement, target)
```

注意第三个参数target，如果忽略则使用$0作为参数，即整行文本。

- 例子1：替换单个串

只把每行的第一个AAAA替换为BBBB

```shell
awk '{ sub(/AAAA/,"BBBB"); print $0 }' t.txt
```

- 例子2：替换所有的串

把每一行的所有AAAA替换为BBBB

```shell
awk '{ gsub(/AAAA/,"BBBB"); print $0 }' t.txt
```

- 例子3：替换满足条件的行的串

只在出现字符串CCCC的前提下，将行中所有AAAA替换为BBBB

```shell
awk '/CCCC/ { gsub(/AAAA/,"BBBB"); print $0; next }{ print $0 }' t.txt
```

- 例子4：替换多个可选串

不管是AAAA，还是CCCC，全部替换为BBBB

```shell
awk '{ gsub(/AAAA|aaaa/,"BBBB"); print $0 }' t.txt
```

- 例子5：全字匹配替换

全字匹配AAAA；即不匹配AAA,以及AAAAA，也就是说完整的四个字符串AAAA。

```shell
awk '{ sub(/\<AAAA\>/,"BBBB"); print $0 }' t.txt
```

- 例子6：规则表达式匹配

把所有以A开头，不管后面连续包含几个A的串替换成一个字符B。

```shell
awk '{ gsub(/^A*/,"B"); print $0 }' t.txt
```