---
title: "Access Log 常用统计命令"
date: "2024-07-06T01:17:38+08:00"
lastmod: "2024-07-06T01:17:38+08:00"
categories: ["Linux"]
slug: "access-log-statistics"
draft: false
---

1.根据访问IP统计UV

```bash
awk '{print $1}' access.log | sort | uniq -c | wc -l
```


2.统计访问URL统计PV  

```bash
awk '{print $7}' access.log | wc -l
```

3.查询访问最频繁的URL

```bash
awk '{print $7}' access.log | sort | uniq -c | sort -n -k 1 -r | more
```  
  
  
4.查询访问最频繁的IP
```bash
awk '{print $1}' access.log | sort | uniq -c | sort -n -k 1 -r | more
```
  
  
5.根据时间段统计查看日志

```bash
cat  access.log | sed -n '/14\/Mar\/2015:21/,/14\/Mar\/2015:22/p' | more
``` 
  
  
6.通过日志查看含有send的url,统计ip地址的总连接数
```bash
cat access.log | grep "send" | awk '{print $1}' | sort | uniq -c | sort -nr
```
  
  
7.通过日志查看当天访问次数最多的时间段
```bash
awk '{print $4}' access.log | grep "24/Mar/2011" |cut -c 14-18 | sort | uniq -c | sort -nr | head
```  
  
  
8.通过日志查看当天指定ip访问次数过的url和访问次数
```bash
cat access.log | grep "192.0.2.10" | awk '{print $7}' | sort | uniq -c | sort -nr
```