---
title: "VMware 虚拟机扩容与 LVM 文件系统调整"
date: "2024-04-15T14:44:53+08:00"
lastmod: "2024-04-15T14:44:53+08:00"
categories: ["Linux"]
slug: "vmware-lvm-disk-extension"
draft: false
---

# vmware 给已有机器扩容

## 1 vmware 虚机增加磁盘空间
修改完成后，会提示硬盘已准备。需要重启虚拟机。

在 VMware 的虚拟机设置中扩大已有虚拟磁盘容量，本例将磁盘从 60 GiB 扩到 80 GiB。

### 1.1 查看重启后机器的磁盘是否有变化
下面的图是磁盘更新前跟磁盘更新后的 lsblk 命令的结果


```bash
lsblk
```

本例扩容前 `/dev/sda` 为 60G，扩容后为 80G；已有 `/dev/sda3` 分区仍为 44G，需要继续更新分区。

## 2 更新磁盘分区
### 2.1 查看磁盘分区

```bash
fdisk -l /dev/sda
```

记录需要扩容的 `/dev/sda3` 分区起始扇区，重新创建时必须保留这个起点。

### 2.2 修改磁盘分区
本例需要扩容的是 LVM 物理卷所在的 `/dev/sda3` 分区，简化为以下步骤：
1. 删除根分区，但是不要写入磁盘（即输入 w）
2. 创建新的分区，新的分区的起点必须是删除的根分区的起点（默认就会是一样的，但是要非常注意）
   执行 `fdisk /dev/sda`，用 `p` 查看分区表、`d` 删除目标分区、`n` 重新建立同编号分区；保持原起始扇区，把结束扇区扩至磁盘末尾。确认起点和分区类型后再写入。
3. 写入磁盘（即输入 w）

本例重新创建后，`/dev/sda3` 从 44 GiB 扩到 64 GiB。其他分区保持原位置和大小。

### 2.3 刷新一下分区信息
分区操作完成，刷新一下分区信息并再次查看分区信息

```bash
partprobe /dev/sda
```
```bash
lsblk
pvdisplay
```

刷新后分区显示为 64G，但 LVM 物理卷大小可能仍是 44G。

## 3 调整LVM中物理卷
可以看到 pv的 /dev/sda3还是 44G 没有更新完成
需要调整LVM中物理卷的容量大小，执行命令

```bash
pvresize /dev/sda3
```
```bash
pvdisplay
```

确认 `/dev/sda3` 对应的物理卷大小已经更新为 64 GiB。

可以看到  /dev/sda3 的pv 大小已经更新为 64G

## 4 扩展逻辑卷
查看逻辑卷大小

```bash
lvdisplay
```

执行命令扩展逻辑卷，并再次查看

```bash
lvextend -l +100%FREE /dev/centos/root
```
```bash
lvdisplay
```

逻辑卷 `/dev/centos/root` 扩容后，再确认其容量已经增长。

## 5 文件系统扩容
df查看磁盘大小，还是没有更新，需要对文件系统扩容，默认文件系统为xfs，所以使用 xfs_growfs 命令

```bash
xfs_growfs /dev/centos/root
```

```bash
df -Th /
```

最后查看磁盘大小已经更新为80G
