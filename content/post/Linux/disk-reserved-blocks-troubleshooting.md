---
title: "Linux 磁盘写满与保留空间排查"
date: "2023-08-26T23:39:32+08:00"
lastmod: "2023-08-26T23:39:32+08:00"
categories: ["Linux"]
slug: "disk-reserved-blocks-troubleshooting"
draft: false
---

## Linux下磁盘写满问题

### 一、问题描述

总是会出现磁盘不小心打满，然后执行 `rm` 命令发现 `rm: cannot remove 'test': No space left on device`，这种情况不知道如何处理。

### 二、解决方案

#### 1. 扩磁盘

现在都是云，可以尝试挂多块盘，具体操作看厂商的操作文档吧，我也不熟悉。

#### 2. 保留磁盘空间

linux的硬盘分区程序会自动为root或指定的用户保留一定的磁盘空间默认是5％，可以通过这个方式解决。这其实也是这篇文章的主要目的之一。

本次实验使用 ext 文件系统。ext2/ext3/ext4 可以通过保留块机制为超级用户留出空间；本文的 tune2fs 操作针对这类文件系统。

```bash
[root@centos7.6 ~]# man mkfs.ext4
...

OPTIONS
...
       -m reserved-blocks-percentage
              Specify  the percentage of the filesystem blocks reserved for the super-user.  This avoids fragmentation, and allows root-owned daemons, such as syslogd(8), to continue to function correctly after non-privileged processes are prevented from writing to the filesystem.  The default percentage is 5%.

```

只摘要重点，谷歌机器翻译下

```
指定为超级用户保留的文件系统块的百分比。这可以避免碎片，并允许 root 拥有的守护进程（例如 syslogd(8)）在阻止非特权进程写入文件系统后继续正常运行。默认百分比为 5%。
```

简单说就是系统怕磁盘打满，给管理员留了 5% 的磁盘空间，给特殊处理情况。

##### 一个猜想

一次排障时，虚拟机上直接运行的 Docker 应用持续报错并输出到控制台，容器日志文件增长到 93G。
想起来释放磁盘这个方法，就决定试一试。

当时释放保留空间没有解决问题，猜测可能是日志写入过快，释放的空间很快再次耗尽。这个猜测没有直接验证。

##### 相关命令

相关的执行命令

```bash
tune2fs -l /dev/sda1  # 查看所有磁盘信息
tune2fs -l /dev/sda1 | grep "Reserved block count"  # 查看保留区间
tune2fs -r 25600 /dev/sda1  # 手动指定磁盘 Reserved block 大小
tune2fs -m 0 /dev/sda1  # 指定 Reserved block 百分比，0 表示 0%
tune2fs -m 5 /dev/sda1  # 指定 Reserved block 百分比为 5%
```

系统执行命令

```bash
[root@centos7.6 ~]# df
Filesystem     1K-blocks     Used Available Use% Mounted on
devtmpfs         7878504        0   7878504   0% /dev
tmpfs            7888884        0   7888884   0% /dev/shm
tmpfs            7888884   731848   7157036  10% /run
tmpfs            7888884        0   7888884   0% /sys/fs/cgroup
/dev/sda1      103079844 19579640  78240996  21% /
overlay        103079844 19579640  78240996  21% /var/lib/docker/overlay2/EXAMPLE_LAYER/merged
tmpfs            1577780        0   1577780   0% /run/user/0
[root@centos7.6 ~]# tune2fs -m 0 /dev/sda1
tune2fs 1.42.9 (28-Dec-2013)
Setting reserved blocks percentage to 0% (0 blocks)
[root@centos7.6 ~]# df
Filesystem     1K-blocks     Used Available Use% Mounted on
devtmpfs         7878504        0   7878504   0% /dev
tmpfs            7888884        0   7888884   0% /dev/shm
tmpfs            7888884   731848   7157036  10% /run
tmpfs            7888884        0   7888884   0% /sys/fs/cgroup
/dev/sda1      103079844 19579644  83483816  19% /
overlay        103079844 19579644  83483816  19% /var/lib/docker/overlay2/EXAMPLE_LAYER/merged
tmpfs            1577780        0   1577780   0% /run/user/0
```

```bash
[root@centos7.6 ~]# df -h
Filesystem      Size  Used Avail Use% Mounted on
devtmpfs        7.6G     0  7.6G   0% /dev
tmpfs           7.6G     0  7.6G   0% /dev/shm
tmpfs           7.6G  715M  6.9G  10% /run
tmpfs           7.6G     0  7.6G   0% /sys/fs/cgroup
/dev/sda1        99G   19G   75G  21% /
overlay          99G   19G   75G  21% /var/lib/docker/overlay2/EXAMPLE_LAYER/merged
tmpfs           1.6G     0  1.6G   0% /run/user/0
[root@centos7.6 ~]# tune2fs -l /dev/sda1
tune2fs 1.42.9 (28-Dec-2013)
Filesystem volume name:   <none>
Last mounted on:          /
Filesystem UUID:          1cf0b662-ebd1-44a2-bbd2-0a6e58aec5fa
Filesystem magic number:  0xEF53
Filesystem revision #:    1 (dynamic)
Filesystem features:      has_journal ext_attr resize_inode dir_index filetype needs_recovery extent 64bit flex_bg sparse_super large_file huge_file uninit_bg dir_nlink extra_isize
Filesystem flags:         signed_directory_hash 
Default mount options:    user_xattr acl
Filesystem state:         clean
Errors behavior:          Continue
Filesystem OS type:       Linux
Inode count:              6553600
Block count:              26214139
Reserved block count:     1310706
Free blocks:              24938639
Free inodes:              6477545
First block:              0
Block size:               4096
Fragment size:            4096
Group descriptor size:    64
Reserved GDT blocks:      1016
Blocks per group:         32768
Fragments per group:      32768
Inodes per group:         8192
Inode blocks per group:   512
Flex block group size:    16
Filesystem created:       Fri Feb 26 16:09:26 2021
Last mount time:          Tue Aug  1 10:17:16 2023
Last write time:          Sat Aug 26 19:24:38 2023
Mount count:              9
Maximum mount count:      -1
Last checked:             Fri Feb 26 16:09:26 2021
Check interval:           0 (<none>)
Lifetime writes:          6584 MB
Reserved blocks uid:      0 (user root)
Reserved blocks gid:      0 (group root)
First inode:              11
Inode size:               256
Required extra isize:     28
Desired extra isize:      28
Journal inode:            8
Default directory hash:   half_md4
Directory Hash Seed:      eb7540bb-6293-40e6-b29c-da8dc74aea46
Journal backup:           inode blocks
[root@centos7.6 ~]# tune2fs -m 0 /dev/sda1
tune2fs 1.42.9 (28-Dec-2013)
Setting reserved blocks percentage to 0% (1310706 blocks)
[root@centos7.6 ~]# df -h
Filesystem      Size  Used Avail Use% Mounted on
devtmpfs        7.6G     0  7.6G   0% /dev
tmpfs           7.6G     0  7.6G   0% /dev/shm
tmpfs           7.6G  715M  6.9G  10% /run
tmpfs           7.6G     0  7.6G   0% /sys/fs/cgroup
/dev/sda1        99G   19G   80G  19% /
overlay          99G   19G   80G  19% /var/lib/docker/overlay2/EXAMPLE_LAYER/merged
tmpfs           1.6G     0  1.6G   0% /run/user/0
[root@centos7.6 ~]# tune2fs -l /dev/sda1
tune2fs 1.42.9 (28-Dec-2013)
Filesystem volume name:   <none>
Last mounted on:          /
Filesystem UUID:          1cf0b662-ebd1-44a2-bbd2-0a6e58aec5fa
Filesystem magic number:  0xEF53
Filesystem revision #:    1 (dynamic)
Filesystem features:      has_journal ext_attr resize_inode dir_index filetype needs_recovery extent 64bit flex_bg sparse_super large_file huge_file uninit_bg dir_nlink extra_isize
Filesystem flags:         signed_directory_hash 
Default mount options:    user_xattr acl
Filesystem state:         clean
Errors behavior:          Continue
Filesystem OS type:       Linux
Inode count:              6553600
Block count:              26214139
Reserved block count:     0
Free blocks:              24938639
Free inodes:              6477545
First block:              0
Block size:               4096
Fragment size:            4096
Group descriptor size:    64
Reserved GDT blocks:      1016
Blocks per group:         32768
Fragments per group:      32768
Inodes per group:         8192
Inode blocks per group:   512
Flex block group size:    16
Filesystem created:       Fri Feb 26 16:09:26 2021
Last mount time:          Tue Aug  1 10:17:16 2023
Last write time:          Sat Aug 26 18:32:52 2023
Mount count:              9
Maximum mount count:      -1
Last checked:             Fri Feb 26 16:09:26 2021
Check interval:           0 (<none>)
Lifetime writes:          6584 MB
Reserved blocks uid:      0 (user root)
Reserved blocks gid:      0 (group root)
First inode:              11
Inode size:               256
Required extra isize:     28
Desired extra isize:      28
Journal inode:            8
Default directory hash:   half_md4
Directory Hash Seed:      eb7540bb-6293-40e6-b29c-da8dc74aea46
Journal backup:           inode blocks
[root@centos7.6 ~]# tune2fs -m 5 /dev/sda1
tune2fs 1.42.9 (28-Dec-2013)
Setting reserved blocks percentage to 5% (1310706 blocks)
```

#### 实际解决方案 /dev/null

说到上面的问题，磁盘已经打满，当时因为只有一块盘，`rm` 也失效。在我手足无措的时候，同事来帮忙解决了。

```bash
container_id=$(docker inspect --format '{{.Id}}' example-container)
cat /dev/null > "/var/lib/docker/containers/${container_id}/${container_id}-json.log"
```

通过将 `/dev/null` 重定向到日志文件，直接把现有日志截断为零字节。当时删除文件失败，而截断文件成功释放了空间；这不意味着 `rm` 必须申请与文件大小相同的空间。

当然似乎是运气不错，理论上磁盘打满夸张点会直接导致 `ssh` 都无法登录。