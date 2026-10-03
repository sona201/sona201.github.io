---
title: "斐讯 K2 从 Padavan 刷 OpenWrt 24.10.8"
description: "记录斐讯 K2 PSG1218 A6 从 Padavan 切换到 OpenWrt 24.10.8 的实际刷机过程，包括 Breed、备份、固件选择、SHA256 校验和刷机后的检查。"
date: "2026-10-03T17:30:00+08:00"
lastmod: "2026-10-03T17:30:00+08:00"
categories: ["网络"]
tags: ["OpenWrt", "斐讯K2", "Padavan", "Breed", "路由器"]
image:
---

最近在学习 VLAN、子网、路由和家庭组网，手里正好有一台闲置多年的斐讯 K2。它之前已经刷成 Padavan，但管理页面切换一次经常需要 30 秒左右，于是决定把它重新刷成 OpenWrt，当作网络实验机。

这篇文章记录这次实际操作过程。设备和 Breed 版本不同，操作方式可能不同，刷机前一定先确认自己的型号和 Flash 布局。

## 一、设备信息

路由器铭牌信息：

- 型号：斐讯 K2 / PSG1218
- 硬件版本：A6
- SoC：MediaTek MT7620A
- RAM：64 MB DDR2
- Flash：Winbond W25Q64，8 MB
- 当前系统：Padavan 3.4.3.9-099
- Bootloader：Breed 1.1 r1033

Padavan SSH 中可以看到：

```text
MediaTek SoC: MT7620A, RevID: 0206, RAM: DDR2, XTAL: 20MHz
CPU/OCP/SYS frequency: 580/193/193 MHz
SPI flash chip: W25Q64BV (ef 40170000) (8192 Kbytes)
```

当前 Flash 分区：

```text
0x000000000000-0x000000030000 : "Bootloader"
0x000000030000-0x000000040000 : "Config"
0x000000040000-0x000000050000 : "Factory"
0x000000050000-0x00000016c2d0 : "Kernel"
0x00000016c2d0-0x0000007c0000 : "RootFS"
0x0000007c0000-0x000000800000 : "Storage"
0x000000050000-0x000000800000 : "Firmware_Stub"
```

固件从 `0x50000` 开始，这一点后面选择 K2 v22.4 profile 时很重要。

## 二、先判断 Padavan 卡顿是不是硬件问题

Padavan 后台非常卡，但路由器本身负载并不高，所以先测试局域网延迟：

```bash
ping 192.168.123.1
```

实际结果平均只有约 1 ms，并且没有丢包。同时 Padavan 页面显示 CPU 占用很低、还有约 30 MB 空闲内存。

因此更像是旧 Padavan/Web 服务或配置问题，而不是单纯网络链路太慢。

既然本来就准备把 K2 当实验机，最终没有继续修旧 Padavan。

## 三、确认 Breed

Breed 可以理解为路由器上的 Bootloader/救援环境，有点类似 PC 的 BIOS/UEFI。只要 Breed 本身还在，即使后面的 OpenWrt 刷坏了，一般仍有机会重新刷固件恢复。

进入 Breed 的方法：

1. K2 断电。
2. 按住 RESET。
3. 保持 RESET 的同时通电。
4. 等几秒后松开 RESET。
5. 电脑有线连接 LAN 口。
6. 将电脑放到 `192.168.1.0/24` 网段。
7. 浏览器访问 `http://192.168.1.1`。

这台机器成功进入 Breed，显示：

```text
Breed 版本：1.1 (r1033)
CPU：MediaTek MT7620A
内存：64MB DDR2
Flash：Winbond W25Q64 8MB
```

## 四、刷之前一定先备份

在 Breed 的「固件备份」页面分别保存：

```text
eeprom.bin
firmware.bin
full.bin
```

其中：

- `eeprom.bin`：Factory/EEPROM 数据，包含无线校准等设备相关信息，非常重要。
- `firmware.bin`：当前 Padavan 固件备份。
- `full.bin`：完整 Flash 备份，适合严重故障时恢复。

这三个文件建议至少保存两份。

刷机过程中不要随便执行：

```text
mtd erase ...
mtd write ...
dd ... of=/dev/mtd...
```

尤其不要乱写 Bootloader 和 Factory 分区。

## 五、选择 OpenWrt 固件

最终选择：

```text
OpenWrt 24.10.8
Target: ramips/mt7620
Device: Phicomm K2 v22.4 or older
```

官方目录：

https://downloads.openwrt.org/releases/24.10.8/targets/ramips/mt7620/

下载了两个文件：

```text
openwrt-24.10.8-ramips-mt7620-phicomm_k2-v22.4-initramfs-kernel.bin
openwrt-24.10.8-ramips-mt7620-phicomm_k2-v22.4-squashfs-sysupgrade.bin
```

这台 K2 的 Padavan Flash 布局中 firmware 从 `0x50000` 开始，与 v22.4 profile 对应。正式启动 OpenWrt 后，LuCI 最终也识别为：

```text
Phicomm K2 v22.4 or older
```

### 校验 SHA256

不要跳过固件校验。

initramfs：

```bash
shasum -a 256 ~/Downloads/openwrt-24.10.8-ramips-mt7620-phicomm_k2-v22.4-initramfs-kernel.bin
```

得到：

```text
63fd43bd57e499e10e05fbaa46551a5150fa087f16c7030d348c9f77ff2539f2
```

sysupgrade：

```bash
shasum -a 256 ~/Downloads/openwrt-24.10.8-ramips-mt7620-phicomm_k2-v22.4-squashfs-sysupgrade.bin
```

得到：

```text
da17725d7b626b67feeed0a4b3ccb71970238539450f43d5b36426cccb344dc8
```

都与 OpenWrt 官方 SHA256 一致后再继续。

## 六、先进入 OpenWrt recovery/initramfs

这次没有一上来就在 OpenWrt 中永久写入 sysupgrade，而是先进入 OpenWrt 的 recovery/initramfs 环境。

成功后 LuCI 顶部会看到类似提示：

```text
System running in recovery (initramfs) mode.
```

此时 OpenWrt 是临时运行状态。

确认页面能够正常打开、设备型号能够识别后，再进行正式安装。

> 不同 Breed 版本提供的启动/刷写方式可能不同。这里最重要的是先确认自己已经进入 OpenWrt recovery/initramfs，再执行下面的 sysupgrade，而不是照搬其他型号路由器的 Breed 参数。

## 七、正式刷入 OpenWrt

进入 recovery OpenWrt 后：

```text
System
→ Backup / Flash Firmware
→ Flash new firmware image
```

选择：

```text
openwrt-24.10.8-ramips-mt7620-phicomm_k2-v22.4-squashfs-sysupgrade.bin
```

上传以后 OpenWrt 会再次显示文件大小和 SHA256。

实际看到：

```text
Size: 6.25 MiB
SHA256: da17725d7b626b67feeed0a4b3ccb71970238539450f43d5b36426cccb344dc8
```

这里再次确认 SHA256 与 Mac 本地以及官方值一致。

由于是从 Padavan 全新切换到 OpenWrt，我取消了：

```text
Keep settings and retain the current configuration
```

然后点击 Continue 开始写 Flash。

写入期间：

- 不断电。
- 不按 RESET。
- 不拔网线。
- 不刷新页面。

等待路由器完成写入和重启。

## 八、第一次启动

正式 OpenWrt 启动后访问：

```text
http://192.168.1.1
```

LuCI 显示：

```text
Model: Phicomm K2 v22.4 or older
Firmware Version: OpenWrt 24.10.8
Kernel Version: 6.6.144
Target Platform: ramips/mt7620
```

这说明 profile 选择正确，刷机成功。

第一件事先设置 root 密码，然后通过 SSH 检查：

```bash
ssh root@192.168.1.1

df -h
free -m
uptime
cat /proc/mtd
```

最终 Flash 分区类似：

```text
mtd0: "u-boot"
mtd1: "u-boot-env"
mtd2: "factory"
mtd3: "firmware"
mtd4: "kernel"
mtd5: "rootfs"
mtd6: "rootfs_data"
```

Breed 和 Factory 都还保留着。

## 九、8MB Flash 的现实限制

刷完以后：

```text
/overlay 总空间约 1.4 MB
剩余约 1.2 MB
```

所以 K2 跑 OpenWrt 最大的问题不是 CPU，而是 Flash 和 RAM 太小。

看到：

```text
/dev/root  100%
```

不用紧张。OpenWrt 的 `/dev/root` 是只读 SquashFS，显示 100% 属于正常现象。真正需要关注的是可写的 `/overlay`。

这台 K2 比较适合：

- 学 VLAN。
- 学 DHCP。
- 学静态路由。
- 学 NAT 和防火墙。
- 学 DNS。
- 测试 Wi-Fi 网络隔离。

不适合：

- OpenClash。
- Passwall。
- AdGuard Home。
- 大量 LuCI 插件。

只有 1 MB 左右的可写空间，随便安装几个软件包就可能把 Flash 填满。

## 十、无线还能不能用？

可以。

刷 OpenWrt 后并不是无线功能消失了。K2 的官方 OpenWrt profile 已包含对应无线驱动，通常不需要另外安装驱动模块。

OpenWrt 首次启动时无线可能默认关闭，在：

```text
Network → Wireless
```

配置 SSID、加密方式并启用即可。

如果无线页面没有识别到 Radio，可以通过 SSH 检查：

```bash
wifi status
iwinfo
ls /sys/class/ieee80211/
dmesg | grep -Ei 'mt76|wifi|wlan|80211'
opkg list-installed | grep -E 'mt76|mac80211|wireless|wpad'
```

K2 的 Flash 太小，不要看到无线没开启就先执行 `opkg install`，应该先确认驱动是否已经存在。

## 总结

这次实际升级路径可以概括成：

```text
K2 PSG1218 A6
      ↓
Padavan
      ↓
确认 Breed
      ↓
备份 EEPROM / Padavan / Full Flash
      ↓
OpenWrt 24.10.8 v22.4 initramfs/recovery
      ↓
校验 sysupgrade SHA256
      ↓
OpenWrt sysupgrade
      ↓
OpenWrt 24.10.8
```

对一台 8MB Flash、64MB RAM 的老 K2 来说，OpenWrt 24.10.8 已经比较吃紧，不适合继续堆插件。但拿来做 VLAN、子网、路由、DHCP、防火墙等网络实验，反而是个不错的废物利用方式。

### 参考

- OpenWrt Phicomm K2：https://openwrt.org/toh/phicomm/k2
- OpenWrt 24.10.8 ramips/mt7620：https://downloads.openwrt.org/releases/24.10.8/targets/ramips/mt7620/
