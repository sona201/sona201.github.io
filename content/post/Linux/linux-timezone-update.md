---
title: "Linux 修改时区与 crontab 时间排查"
date: "2024-08-16T00:41:07+08:00"
lastmod: "2024-08-16T00:41:07+08:00"
categories: ["Linux"]
slug: "linux-timezone-update"
draft: false
---

#linux #localtime #zone #Shanghai #Asia
#### linux 修改时区
```
[root@example-host ~]$ ll /etc/localtime
lrwxrwxrwx 1 root root 29 Aug  7 02:30 /etc/localtime -> /usr/share/zoneinfo/Etc/GMT+8
[root@example-host ~]$ rm -f /etc/localtime
[root@example-host ~]$ ln -s /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
[root@example-host ~]$ date -R
Mon, 04 Nov 2024 15:08:29 +0800
```
####  crontab时间和系统时间不一致

1. 同步系统时间 ：`ntpdate us.pool.ntp.org`
2. 修改完后,需要的话可以输入:`clock -w` 把系统时间写入CMOS
3. 将当前时间和日期写入BIOS，避免重启后失效 ： `hwclock -w`
4. 重启 `crontab`：`service crond restart`  
5. 重启 `rsyslog`： `service rsyslog restart`
