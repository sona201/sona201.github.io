---
title: "Bash if 判断空字符串笔记"
date: "2024-04-02T15:57:44+08:00"
lastmod: "2024-04-02T15:57:44+08:00"
categories: ["Linux"]
slug: "bash-if-empty-string-notes"
draft: false
---

> 老生常谈的if判断字符串加x的问题

```
if [ "$3"x = "r"x ]


string='My string';

if [ $string = "My" ]; then
   echo "It's there!";
else
   echo "xxxx";
fi
```

主要是双括号与单括号的情况区分

双括号的情况下是不需要用x来替代的

单括号的情况下，不加x，变量为空时，会报错

#### 执行报错结果
```
[root@iZf8z68utftnb7w6jdl1f0Z ~]# cat test.sh 
string='';


if [ $string = "My" ]; then
   echo "It's there!";
else
   echo "xxxx";
fi
[root@iZf8z68utftnb7w6jdl1f0Z ~]# bash test.sh 
test.sh: line 4: [: =: unary operator expected
xxxx
[root@iZf8z6
```