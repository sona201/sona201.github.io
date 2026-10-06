---
title: "查看 Linux 发行版与内核版本"
date: "2024-01-08T00:31:04+08:00"
lastmod: "2024-01-08T00:31:04+08:00"
categories: ["Linux"]
slug: "linux-distribution-kernel-version"
draft: false
---

## 查看 Linux 发行版名称和版本号有很多种方法

[参考原文](https://linux.cn/article-9586-1.html)

偶尔需要查看系统的版本，安装对应的包，整理的一些方法，依次列举

### 1. /proc/version 文件
这个是系统生成的虚拟文件，直接可以查看内核版本，也能列举系统名称，但不能快速区分centos与redhat区别
```bash
[root@example-host ~]# cat /proc/version
Linux version 3.10.0-957.27.2.el7.x86_64 (mockbuild@kbuilder.bsys.centos.org) (gcc version 4.8.5 20150623 (Red Hat 4.8.5-36) (GCC) ) #1 SMP Mon Jul 29 17:46:05 UTC 2019
```

### 2. uname 命令
这个命令能查到信息，但似乎只有内核信息，没有系统层面的
```bash
[root@example-host ~]# uname -a
Linux example-host 3.10.0-957.27.2.el7.x86_64 #1 SMP Mon Jul 29 17:46:05 UTC 2019 x86_64 x86_64 x86_64 GNU/Linux
```

### 3./etc/*-release 文件

```bash
[root@example-host ~]# ll /etc/*-release
-rw-r--r--. 1 root root  38 Nov 23  2018 /etc/centos-release
-rw-r--r--. 1 root root 393 Nov 23  2018 /etc/os-release
lrwxrwxrwx. 1 root root  14 Aug  8  2019 /etc/redhat-release -> centos-release
lrwxrwxrwx. 1 root root  14 Aug  8  2019 /etc/system-release -> centos-release
[root@example-host ~]# cat /etc/centos-release
CentOS Linux release 7.6.1810 (Core) 
[root@example-host ~]# cat /etc/os-release 
NAME="CentOS Linux"
VERSION="7 (Core)"
ID="centos"
ID_LIKE="rhel fedora"
VERSION_ID="7"
PRETTY_NAME="CentOS Linux 7 (Core)"
ANSI_COLOR="0;31"
CPE_NAME="cpe:/o:centos:centos:7"
HOME_URL="https://www.centos.org/"
BUG_REPORT_URL="https://bugs.centos.org/"

CENTOS_MANTISBT_PROJECT="CentOS-7"
CENTOS_MANTISBT_PROJECT_VERSION="7"
REDHAT_SUPPORT_PRODUCT="centos"
REDHAT_SUPPORT_PRODUCT_VERSION="7"

[root@example-host ~]# 
```

### 4. dmesg 命令
某次在 busybox 环境执行时没有查到结果，原因尚未确认。

```bash
[root@example-host ~]# dmesg | grep "Linux"
[    0.000000] Linux version 3.10.0-957.27.2.el7.x86_64 (mockbuild@kbuilder.bsys.centos.org) (gcc version 4.8.5 20150623 (Red Hat 4.8.5-36) (GCC) ) #1 SMP Mon Jul 29 17:46:05 UTC 2019
[    0.254399] SELinux:  Initializing.
[    0.255084] SELinux:  Starting in permissive mode
[    0.487992] ACPI: Added _OSI(Linux-Dell-Video)
[    1.050709] SELinux:  Registering netfilter hooks
[    1.094702] Linux agpgart interface v0.103
[    1.131062] usb usb1: Manufacturer: Linux 3.10.0-957.27.2.el7.x86_64 uhci_hcd
[    1.143529] Loaded X.509 cert 'CentOS Linux kpatch signing key: ea0413152cde1d98ebdca3fe6f0230904c9ef717'
[    1.143544] Loaded X.509 cert 'CentOS Linux Driver update signing key: 7f421ee0ab69461574bb358861dbe77762a4201b'
[    1.144013] Loaded X.509 cert 'CentOS Linux kernel signing key: 520a4e2d9d553ef84201c188b87fe51b9de11a5e'
[    6.210714] SELinux: 2048 avtab hash slots, 112490 rules.
[    6.252057] SELinux: 2048 avtab hash slots, 112490 rules.
[    6.278128] SELinux:  8 users, 14 roles, 5036 types, 318 bools, 1 sens, 1024 cats
[    6.278131] SELinux:  129 classes, 112490 rules
[    6.281956] SELinux:  Class bpf not defined in policy.
[    6.282833] SELinux: the above unknown classes and permissions will be allowed
[    6.284136] SELinux:  Completing initialization.
[    6.284137] SELinux:  Setting up existing superblocks.
[    6.298096] systemd[1]: Successfully loaded SELinux policy in 106.735ms.
[2823938.364972] SELinux: 2048 avtab hash slots, 112490 rules.
[2823938.406930] SELinux: 2048 avtab hash slots, 112490 rules.
[2823938.434186] SELinux:  8 users, 14 roles, 5036 types, 318 bools, 1 sens, 1024 cats
[2823938.434190] SELinux:  129 classes, 112490 rules
[2823938.438594] SELinux:  Class bpf not defined in policy.
[2823938.439621] SELinux: the above unknown classes and permissions will be allowed
[2823938.440956] SELinux:  Converting 2330 SID table entries...
[2824055.815791] SELinux: 2048 avtab hash slots, 112502 rules.
[2824055.854177] SELinux: 2048 avtab hash slots, 112502 rules.
[2824055.880975] SELinux:  8 users, 14 roles, 5036 types, 318 bools, 1 sens, 1024 cats
[2824055.880978] SELinux:  129 classes, 112502 rules
[2824055.885003] SELinux:  Class bpf not defined in policy.
[2824055.886025] SELinux: the above unknown classes and permissions will be allowed
[2824055.887375] SELinux:  Converting 2336 SID table entries...
[root@example-host ~]# 
```

### 5.lsb_release 命令
需要安装相关的包，centos7 如下，执行的命令其实是 `lsb_release` `lsb_release -a` \
感觉这个方法是这几个里最麻烦的
```bash
[root@example-host ~]# yum install redhat-lsb-core 
# 此处省略软件包下载和安装输出
[root@example-host ~]# lsb_release
LSB Version:    :core-4.1-amd64:core-4.1-noarch
[root@example-host ~]# lsb_release -a
LSB Version:    :core-4.1-amd64:core-4.1-noarch
Distributor ID: CentOS
Description:    CentOS Linux release 7.6.1810 (Core) 
Release:        7.6.1810
Codename:       Core
[root@example-host ~]# lsb_release -a
LSB Version:    :core-4.1-amd64:core-4.1-noarch
Distributor ID: CentOS
Description:    CentOS Linux release 7.6.1810 (Core) 
Release:        7.6.1810
Codename:       Core
```
