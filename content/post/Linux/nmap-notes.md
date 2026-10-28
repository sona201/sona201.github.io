---
title: "Nmap 端口扫描笔记"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["Linux"]
tags: ["linux", "nmap", "network"]
draft: false
---

公开版中的命令和输出已做脱敏处理，地址使用文档示例网段，账号和主机名使用占位名称；原始抓包截图不再公开。请按自己的测试环境替换示例值。

以往只知道扫描端口用nmap，可以看出 open closed filtered 对应的状态是 开 关 防火墙拦截

nmap 192.0.2.10 -p 8080 -Pn

其实这个用法不对，-Pn是不使用ping，主要是在扫描多台机器的时候使用

对于我查看某一台机器的端口跟协议

nmap 192.0.2.10 -sU -p 514  # 扫描upd端口，在服务器上可以抓包看到udp
nmap 192.0.2.10 -sP -p 8080 # 扫描tcp端口，在服务器上可以抓包看到tcp

同时检查两个类型
```
[root@example-host ~]# nmap 192.0.2.11 -sS -sU -p 514

Starting Nmap 6.40 ( http://nmap.org ) at 2023-04-13 12:53 CST
Nmap scan report for 192.0.2.11
Host is up (0.00071s latency).
PORT    STATE         SERVICE
514/tcp closed        shell
514/udp open|filtered syslog

Nmap done: 1 IP address (1 host up) scanned in 0.31 seconds
[root@example-host ~]# nmap 192.0.2.11 -sT -sU -p 514

Starting Nmap 6.40 ( http://nmap.org ) at 2023-04-13 12:53 CST
Nmap scan report for 192.0.2.11
Host is up (0.00087s latency).
PORT    STATE         SERVICE
514/tcp closed        shell
514/udp open|filtered syslog

Nmap done: 1 IP address (1 host up) scanned in 0.28 seconds
```

使用wireshark抓包显示(yum install -y wireshark)

```
[root@example-host ~]# tshark -i eth0 host 192.0.2.12
Running as user "root" and group "root". This could be dangerous.
Capturing on 'eth0'
  1 0.000000000 192.0.2.12 -> 192.0.2.11  TCP 58 52956 > https [SYN] Seq=0 Win=1024 Len=0 MSS=1460
  2 0.000025685  192.0.2.11 -> 192.0.2.12 TCP 54 https > 52956 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0
  3 0.000684895 192.0.2.12 -> 192.0.2.11  ICMP 42 Echo (ping) request  id=0xfd77, seq=0/0, ttl=58
  4 0.000691926  192.0.2.11 -> 192.0.2.12 ICMP 42 Echo (ping) reply    id=0xfd77, seq=0/0, ttl=64 (request in 3)
  5 0.000700081 192.0.2.12 -> 192.0.2.11  ICMP 54 Timestamp request    id=0x0a0f, seq=0/0, ttl=47
  6 0.000703470  192.0.2.11 -> 192.0.2.12 ICMP 54 Timestamp reply      id=0x0a0f, seq=0/0, ttl=64
  7 0.001042903 192.0.2.12 -> 192.0.2.11  TCP 54 52956 > http [ACK] Seq=1 Ack=1 Win=1024 Len=0
  8 0.001046910  192.0.2.11 -> 192.0.2.12 TCP 54 http > 52956 [RST] Seq=1 Win=0 Len=0
  9 0.027864364 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 10 0.127943082 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 11 14.128607309 192.0.2.12 -> 192.0.2.11  TCP 54 39871 > http [ACK] Seq=1 Ack=1 Win=1024 Len=0
 12 14.128627342  192.0.2.11 -> 192.0.2.12 TCP 54 http > 39871 [RST] Seq=1 Win=0 Len=0
 13 14.128641456 192.0.2.12 -> 192.0.2.11  ICMP 42 Echo (ping) request  id=0x0cd3, seq=0/0, ttl=45
 14 14.128645487  192.0.2.11 -> 192.0.2.12 ICMP 42 Echo (ping) reply    id=0x0cd3, seq=0/0, ttl=64 (request in 13)
 15 14.128700635 192.0.2.12 -> 192.0.2.11  ICMP 54 Timestamp request    id=0x548d, seq=0/0, ttl=38
 16 14.128703903  192.0.2.11 -> 192.0.2.12 ICMP 54 Timestamp reply      id=0x548d, seq=0/0, ttl=64
 17 14.128931731 192.0.2.12 -> 192.0.2.11  TCP 58 39871 > https [SYN] Seq=0 Win=1024 Len=0 MSS=1460
 18 14.128934644  192.0.2.11 -> 192.0.2.12 TCP 54 https > 39871 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0
 19 14.144575335 192.0.2.12 -> 192.0.2.11  TCP 74 45644 > shell [SYN] Seq=0 Win=29200 Len=0 MSS=1460 SACK_PERM=1 TSval=1253548131 TSecr=0 WS=128
 20 14.144579164  192.0.2.11 -> 192.0.2.12 TCP 54 shell > 45644 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0
 21 110.999002405 192.0.2.12 -> 192.0.2.11  TCP 58 47406 > https [SYN] Seq=0 Win=1024 Len=0 MSS=1460
 22 110.999020511  192.0.2.11 -> 192.0.2.12 TCP 54 https > 47406 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0
 23 110.999740448 192.0.2.12 -> 192.0.2.11  ICMP 42 Echo (ping) request  id=0x52de, seq=0/0, ttl=44
 24 110.999745364  192.0.2.11 -> 192.0.2.12 ICMP 42 Echo (ping) reply    id=0x52de, seq=0/0, ttl=64 (request in 23)
 25 110.999802251 192.0.2.12 -> 192.0.2.11  ICMP 54 Timestamp request    id=0x51bd, seq=0/0, ttl=39
 26 110.999805574  192.0.2.11 -> 192.0.2.12 ICMP 54 Timestamp reply      id=0x51bd, seq=0/0, ttl=64
 27 111.000109881 192.0.2.12 -> 192.0.2.11  TCP 54 47406 > http [ACK] Seq=1 Ack=1 Win=1024 Len=0
 28 111.000113185  192.0.2.11 -> 192.0.2.12 TCP 54 http > 47406 [RST] Seq=1 Win=0 Len=0
 29 111.014724099 192.0.2.12 -> 192.0.2.11  TCP 74 48930 > 5140 [SYN] Seq=0 Win=29200 Len=0 MSS=1460 SACK_PERM=1 TSval=1253645001 TSecr=0 WS=128
 30 111.014728072  192.0.2.11 -> 192.0.2.12 TCP 54 5140 > 48930 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0

 31 124.893938777 192.0.2.12 -> 192.0.2.11  TCP 54 40999 > http [ACK] Seq=1 Ack=1 Win=1024 Len=0
 32 124.893957805  192.0.2.11 -> 192.0.2.12 TCP 54 http > 40999 [RST] Seq=1 Win=0 Len=0
 33 124.894706497 192.0.2.12 -> 192.0.2.11  ICMP 42 Echo (ping) request  id=0xc1d2, seq=0/0, ttl=54
 34 124.894711077  192.0.2.11 -> 192.0.2.12 ICMP 42 Echo (ping) reply    id=0xc1d2, seq=0/0, ttl=64 (request in 33)
 35 124.894756587 192.0.2.12 -> 192.0.2.11  ICMP 54 Timestamp request    id=0xf398, seq=0/0, ttl=52
 36 124.894759362  192.0.2.11 -> 192.0.2.12 ICMP 54 Timestamp reply      id=0xf398, seq=0/0, ttl=64
 37 124.895121682 192.0.2.12 -> 192.0.2.11  TCP 58 40999 > https [SYN] Seq=0 Win=1024 Len=0 MSS=1460
 38 124.895124588  192.0.2.11 -> 192.0.2.12 TCP 54 https > 40999 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0
 39 124.920843490 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 41255  Destination port: 5140
 40 124.920851871  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)

 41 1105.706644739 192.0.2.12 -> 192.0.2.11  TCP 58 48674 > https [SYN] Seq=0 Win=1024 Len=0 MSS=1460
 42 1105.706670049  192.0.2.11 -> 192.0.2.12 TCP 54 https > 48674 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0
 43 1105.706680241 192.0.2.12 -> 192.0.2.11  TCP 54 48674 > http [ACK] Seq=1 Ack=1 Win=1024 Len=0
 44 1105.706682527  192.0.2.11 -> 192.0.2.12 TCP 54 http > 48674 [RST] Seq=1 Win=0 Len=0
 45 1105.707410604 192.0.2.12 -> 192.0.2.11  ICMP 42 Echo (ping) request  id=0xb2e7, seq=0/0, ttl=53
 46 1105.707415647  192.0.2.11 -> 192.0.2.12 ICMP 42 Echo (ping) reply    id=0xb2e7, seq=0/0, ttl=64 (request in 45)
 47 1105.707491509 192.0.2.12 -> 192.0.2.11  ICMP 54 Timestamp request    id=0x2406, seq=0/0, ttl=55
 48 1105.707494181  192.0.2.11 -> 192.0.2.12 ICMP 54 Timestamp reply      id=0x2406, seq=0/0, ttl=64
```

> 多个不连续的端口，用逗号隔开。如果是连续的端口则可以写成 1-100。如果不加 p 参数，则默认是常用的 1000 个端口号（80、3306 这种）。示例使用500-520，如下：
#### 客户端命令
```
[root@example-host ~]# nmap 192.0.2.11 -sU -p 500-520

Starting Nmap 6.40 ( http://nmap.org ) at 2023-04-13 12:44 CST
Nmap scan report for 192.0.2.11
Host is up (0.0020s latency).
PORT    STATE         SERVICE
500/udp closed        isakmp
501/udp open|filtered stmf
502/udp closed        asa-appl-proto
503/udp open|filtered intrinsa
504/udp closed        citadel
505/udp closed        mailbox-lm
506/udp closed        ohimsrv
507/udp open|filtered crs
508/udp closed        xvttp
509/udp open|filtered snare
510/udp closed        fcp
511/udp open|filtered passgo
512/udp closed        biff
513/udp open|filtered who
514/udp open|filtered syslog
515/udp open|filtered printer
516/udp closed        videotex
517/udp closed        talk
518/udp closed        ntalk
519/udp closed        utime
520/udp closed        route

Nmap done: 1 IP address (1 host up) scanned in 7.34 seconds
[root@example-host ~]#
```

#### 服务端抓包
```
[root@example-host ~]# tshark -i eth0 host 192.0.2.12
Running as user "root" and group "root". This could be dangerous.
Capturing on 'eth0'
  1 0.000000000 192.0.2.12 -> 192.0.2.11  TCP 54 62247 > http [ACK] Seq=1 Ack=1 Win=1024 Len=0
  2 0.000012221  192.0.2.11 -> 192.0.2.12 TCP 54 http > 62247 [RST] Seq=1 Win=0 Len=0
  3 0.000762781 192.0.2.12 -> 192.0.2.11  ICMP 42 Echo (ping) request  id=0xb3b0, seq=0/0, ttl=36
  4 0.000766991  192.0.2.11 -> 192.0.2.12 ICMP 42 Echo (ping) reply    id=0xb3b0, seq=0/0, ttl=64 (request in 3)
  5 0.000838519 192.0.2.12 -> 192.0.2.11  ICMP 54 Timestamp request    id=0x06f6, seq=0/0, ttl=51
  6 0.000841192  192.0.2.11 -> 192.0.2.12 ICMP 54 Timestamp reply      id=0x06f6, seq=0/0, ttl=64
  7 0.000951930 192.0.2.12 -> 192.0.2.11  TCP 58 62247 > https [SYN] Seq=0 Win=1024 Len=0 MSS=1460
  8 0.000954938  192.0.2.11 -> 192.0.2.12 TCP 54 https > 62247 [RST, ACK] Seq=1 Ack=1 Win=0 Len=0
  9 0.027985374 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: fcp
 10 0.027994873  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 11 0.028001484 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: mailbox-lm
 12 0.028003845  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 13 0.028022978 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: comsat
 14 0.028025210  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 15 0.028027405 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: talk
 16 0.028029347  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 17 0.028032578 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: utime
 18 0.028034575  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 19 0.028036755 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: ntalk
 20 0.028038599  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 21 0.028045655 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: ohimsrv
 22 0.028948371 192.0.2.12 -> 192.0.2.11  RIPv1 66 Request
 23 0.028969173 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: xvttp
 24 0.029197536 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 25 0.031863656 192.0.2.12 -> 192.0.2.11  ISAKMP 234
 26 0.032008756 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: crs
 27 0.032016229 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: snare
 28 0.032033619 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: passgo
 29 0.032036457 192.0.2.12 -> 192.0.2.11  WHO 42 [Malformed Packet]
 30 0.032189560 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: stmf
 31 0.032713768 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: citadel
 32 0.033107393 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: printer
 33 0.033109814 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: mbap
 34 0.033278278 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: intrinsa
 35 0.033298074 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62503  Destination port: videotex
 36 1.129203755 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: citadel
 37 1.129223655  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 38 1.129284377 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: ohimsrv
 39 1.129309553 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: videotex
 40 1.129312606 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: xvttp
 41 1.129528131 192.0.2.12 -> 192.0.2.11  RIPv1 66 Request
 42 1.130112522 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: intrinsa
 43 1.130166382 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: stmf
 44 1.130325399 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: printer
 45 1.130332607 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: mbap
 46 1.130349056 192.0.2.12 -> 192.0.2.11  WHO 42 [Malformed Packet]
 47 1.130432807 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: passgo
 48 1.130480550 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: snare
 49 1.130491911 192.0.2.12 -> 192.0.2.11  ISAKMP 234
 50 1.130498465 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 51 1.130722396 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62504  Destination port: crs
 52 2.230257219 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: xvttp
 53 2.230278546  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 54 2.231344354 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: ohimsrv
 55 2.231462577 192.0.2.12 -> 192.0.2.11  RIPv1 66 Request
 56 2.231471661 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 57 3.330665951 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: ohimsrv
 58 3.330688702  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 59 3.331863055 192.0.2.12 -> 192.0.2.11  RIPv1 66 Request
 60 3.335033853 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 61 4.431829038 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 62 4.431842894 192.0.2.12 -> 192.0.2.11  RIPv1 66 Request
 63 4.431861359  192.0.2.11 -> 192.0.2.12 ICMP 94 Destination unreachable (Port unreachable)
 64 4.482917482 192.0.2.12 -> 192.0.2.11  ISAKMP 234
 65 5.534215739 192.0.2.12 -> 192.0.2.11  ISAKMP 234
 66 5.534233734  192.0.2.11 -> 192.0.2.12 ICMP 262 Destination unreachable (Port unreachable)
 67 5.583253458 192.0.2.12 -> 192.0.2.11  Syslog 42 [Malformed Packet]
 68 5.633197137 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: crs
 69 5.683380838 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: intrinsa
 70 5.733662264 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: crs
 71 5.783480335 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: intrinsa
 72 5.833938985 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62507  Destination port: crs
 73 5.883631178 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62507  Destination port: intrinsa
 74 5.934858792 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62508  Destination port: crs
 75 5.984879106 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62508  Destination port: intrinsa
 76 6.034732591 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: mbap
 77 6.034746749  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 78 6.085044904 192.0.2.12 -> 192.0.2.11  WHO 42 [Malformed Packet]
 79 6.135110230 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: stmf
 80 6.185641460 192.0.2.12 -> 192.0.2.11  WHO 42 [Malformed Packet]
 81 6.235075713 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: stmf
 82 6.284280617 192.0.2.12 -> 192.0.2.11  WHO 42 [Malformed Packet]
 83 6.334345777 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62507  Destination port: stmf
 84 6.384432615 192.0.2.12 -> 192.0.2.11  WHO 42 [Malformed Packet]
 85 6.434504759 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62508  Destination port: stmf
 86 6.484691016 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: passgo
 87 6.534721820 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: printer
 88 6.586292165 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: passgo
 89 6.634804117 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: printer
 90 6.685869463 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62507  Destination port: passgo
 91 6.734998702 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62507  Destination port: printer
 92 6.785940760 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62508  Destination port: passgo
 93 6.836494406 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62508  Destination port: printer
 94 6.885275082 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: snare
 95 6.935324065 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62505  Destination port: videotex
 96 6.986555913 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: snare
 97 7.035634422 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62506  Destination port: videotex
 98 7.035648502  192.0.2.11 -> 192.0.2.12 ICMP 70 Destination unreachable (Port unreachable)
 99 7.085655195 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62507  Destination port: snare
100 7.188406089 192.0.2.12 -> 192.0.2.11  UDP 42 Source port: 62508  Destination port: snare
```

如果要扫描多个 ip，可以把 ip 放入到文件中，然后通过 iL 参数指定即可，格式：nmap -iL iplist.txt -sU -p 1-100。
nmap 通过 sU 参数使用 udp 进行端口发现，原理是根据是否有返回信息，是否包含端口不可达来判断。

nmap 在二层做主机发现时使用的参数是 sn（ping 扫描，不做端口扫描）。在三层做主机发现时也是使用的 sn 参数，这里二三层都用的 sn 参数，而具体使用的是二层协议 arp 还是三层协议 icmp，判断依据是是否属于同一个网段。在四层发现时主要利用的是 tcp 和 udp，而 nmap 用到的主要参数就是 PU 和 PA。

nmap 使用 udp 来做端口扫描时，用到的参数是 sU，来看下 man 手册的介绍：
![nmap man](/images/nmap-man.png)