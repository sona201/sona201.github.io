---
title: "Bash 逐行读取与嵌套循环笔记"
date: "2023-02-27T00:25:59+08:00"
lastmod: "2023-02-27T00:25:59+08:00"
categories: ["Linux"]
slug: "bash-line-iteration-notes"
draft: false
---

### shell readline for
```bash
while read -r line;
do
   echo "$line" ;
done < input.file
```

```bash
while read x; do echo $x; done << EOF
$(ls -l $1)
EOF
```


```bash
ls -l $1 | while read x; do echo $x; done
ls | while read  line;do echo "/data/path/start.sh";done
```


```bash
IFS='
'
for x in `ls -l $1`; do echo $x; done
```


不改变当前shell的IFS;Put a sub-shell around it if you don't want to set IFS permanently:
```bash
(IFS='
'
for x in `ls -l $1`; do echo $x; done)
```

嵌套循环
```bash
#!/bin/bash

#set -x

cd /data/app


while read -r line;
do
   if [ ! -d $line ]
   then
       echo "$line not exist"
   fi ;
done < /tmp/applist
```