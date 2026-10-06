---
title: "用 Netem 和 TCP 缓冲区观察下载速度"
date: "2023-05-15T00:56:03+08:00"
lastmod: "2023-05-15T00:56:03+08:00"
categories: ["tcp"]
slug: "tcp-netem-buffer-experiments"
draft: false
---

# tcp实验

## 1 实验准备

### 1.1 虚拟机
使用 VMware 创建两台本地隔离虚拟机，系统为 `Ubuntu 20.04 LTS`。以下私有地址只作为本地实验示例，与图中的地址一致：
- tcp-server: 192.168.77.131
- tcp-client: 192.168.77.132

#### 1.1.1 虚拟机相关信息
系统相关信息
1. 内核版本
2. `tc qdesc`信息
3. 系统内核相关参数
```
root@tcp-server:~# uname -a
Linux tcp-server 5.4.0-149-generic #166-Ubuntu SMP Tue Apr 18 16:51:45 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux
root@tcp-server:~# tc qdisc show dev ens33
qdisc fq_codel 0: root refcnt 2 limit 10240p flows 1024 quantum 1514 target 5.0ms interval 100.0ms memory_limit 32Mb ecn 
root@tcp-server:~# sudo sysctl -a | egrep "rmem|wmem|tcp_mem|adv_win|moderate"
net.core.rmem_default = 212992
net.core.rmem_max = 212992
net.core.wmem_default = 212992
net.core.wmem_max = 212992
net.ipv4.tcp_adv_win_scale = 1
net.ipv4.tcp_mem = 44544        59392   89088
net.ipv4.tcp_moderate_rcvbuf = 1
net.ipv4.tcp_rmem = 4096        131072  6291456
net.ipv4.tcp_wmem = 4096        16384   4194304
net.ipv4.udp_rmem_min = 4096
net.ipv4.udp_wmem_min = 4096
vm.lowmem_reserve_ratio = 256   256     32      0       0
```

> Tips: 可以给虚拟机挂载本地文件目录，可以免去拷贝tcpdump file到本地，直接使用

### 1.2 大文件

#### 1.2.1 `dd`生成大文件
```
dd if=/dev/zero of=large_file bs=1G count=2
```

### 1.3 服务器

#### 1.3.1 ubuntu安装`nginx`
最早使用 Python HTTP 服务器，多次实验结果不够稳定。为减少应用服务器差异，本组实验改用 Nginx。
```
root@tcp-server:~# apt install -y nginx
Reading package lists... Done
Building dependency tree       
Reading state information... Done
nginx is already the newest version (1.18.0-0ubuntu1.4).
0 upgraded, 0 newly installed, 0 to remove and 19 not upgraded.
root@tcp-server:~# systemctl start nginx
root@tcp-server:~# systemctl status nginx
● nginx.service - A high performance web server and a reverse proxy server
     Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2023-05-29 15:09:35 UTC; 23h ago
       Docs: man:nginx(8)
   Main PID: 2154 (nginx)
      Tasks: 3 (limit: 4573)
     Memory: 515.4M
     CGroup: /system.slice/nginx.service
             ├─2154 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
             ├─2155 nginx: worker process
             └─2156 nginx: worker process

May 29 15:09:35 tcp-server systemd[1]: Starting A high performance web server and a reverse proxy server...
May 29 15:09:35 tcp-server systemd[1]: Started A high performance web server and a reverse proxy server.
```

#### 1.3.2 配置`nginx`

修改nginx配置文件，能通过`http://ip/path`访问到文件。具体操作如下。

`nginx`默认配置文件启动了80端口，配置文件为`/etc/nginx/sites-enabled/default`，查看配置文件发现默认`nginx`的`html`路径为`/var/www/html`。
将刚刚生成的大文件`large_file`移动到`/var/www/html`。

#### 1.3.3 测试`nginx`服务器配置

在`tcp-client`机器上访问文件

```
root@tcp-client:~# curl -O http://192.168.77.131/large_file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 2048M  100 2048M    0     0  32.4M      0  0:01:03  0:01:03 --:--:-- 30.9M
root@tcp-client:~# ping 192.168.77.131
PING 192.168.77.131 (192.168.77.131) 56(84) bytes of data.
64 bytes from 192.168.77.131: icmp_seq=1 ttl=64 time=0.480 ms
64 bytes from 192.168.77.131: icmp_seq=2 ttl=64 time=0.716 ms
64 bytes from 192.168.77.131: icmp_seq=3 ttl=64 time=0.671 ms
64 bytes from 192.168.77.131: icmp_seq=4 ttl=64 time=0.602 ms
^C
--- 192.168.77.131 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3064ms
rtt min/avg/max/mdev = 0.480/0.617/0.716/0.089 ms
```

不调整网络测试下载速度/时间，看看抓包分析rtt，tcptrace图

- 客户端机器上抓包
```
root@tcp-client:~# tcpdump -i ens33 "host 192.168.77.131" -w tcpdump-clinet-none.cap
tcpdump: listening on ens33, link-type EN10MB (Ethernet), capture size 262144 bytes
^C155254 packets captured
155254 packets received by filter
0 packets dropped by kernel
```
- 服务端上抓包
```
root@tcp-server:~# tcpdump -i ens33 -s 120 "host 192.168.77.132" -w tcpdump-server-none.cap
tcpdump: listening on ens33, link-type EN10MB (Ethernet), capture size 120 bytes
^C133195 packets captured
133195 packets received by filter
0 packets dropped by kernel
```
抓包命令解释:
- 可以不指定 `-s`，抓全量，这样可以看出更多信息，但也会导致文件下载很大。
- 分析tcp图表，rtt(Round Trip Time)一个tcp包往返的时间，一般使用`ping`命令也能发现，但不能完全代替，因为会有内核数据处理损耗等导致误差。
- 分析sequence(tcptrace)图标，详细到50ms内，看网络延迟，`ack`响应时间。 


服务端抓包rtt图，rtt变化比较大

![tcpdump-server-none-rtt](/images/tcpdump-server-none-rtt.png)

客户端端抓包rtt图，rtt时间大概在10以内

![tcpdump--none-rtt](/images/tcpdump-client-none-rtt.png)

## 2 实验1:增加rt，验证 tc 延迟

`clinet`使用`tc`模拟延迟

`root netem` 作用于所配置网卡的出站流量。本实验在 client 端配置，因此其发往 server 的请求和 ACK 会受到延迟影响；若在 server 端配置，则延迟作用于 server 发出的数据。

```
root@tcp-client:~# tc qdisc add dev ens33 root netem delay 100ms
root@tcp-client:~# tc qdisc show dev ens33
qdisc netem 8002: root refcnt 2 limit 1000 delay 100.0ms
root@tcp-client:~# curl -O http://192.168.77.131/large_file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 2048M  100 2048M    0     0  13.9M      0  0:02:27  0:02:27 --:--:-- 23.8M
```

服务端抓包，有几段很明显的ack响应延迟，平均下载速度也小了，13.9M

![tcpdump-server-tc-delay100-tcptrace](/images/tcpdump-server-tc-delay100-tcptrace.png)

客户端抓包，rtt图延迟直接在100以上，与预期一致；对比没有延迟的rtt图，几乎是所有数据点上浮100ms

![tcpdump-client-tc-delay100-rtt](/images/tcpdump-client-tc-delay100-rtt.png)


## 3 实验2:写死 server wmem

删除之前增加的延迟配置
```
root@tcp-client:~# tc qdisc del dev ens33 root
root@tcp-client:~# tc qdisc show dev ens33
qdisc fq_codel 0: root refcnt 2 limit 10240p flows 1024 quantum 1514 target 5.0ms interval 100.0ms memory_limit 32Mb ecn 
root@tcp-client:~# 
```
调整内核参数

内核参数说明
```bash
sudo sysctl -a | egrep "rmem|wmem|tcp_mem|adv_win|moderate"

net.ipv4.tcp_rmem = 4096 131072 6291456 // 最小值、默认值、最大值
net.ipv4.tcp_wmem = 4096 16384 4194304 // 最小值、默认值、最大值
```

sysctl：可以查看和修改内核参数
rmem：套接字接收缓冲区大小
wmem：套接字发送缓冲区大小

下面的实现会调整 rmem 和 wmem 的大小做相关的实验。

修改前参数
```
root@tcp-client:~# sysctl -a | egrep "rmem|wmem|tcp_mem|adv_win|moderate"
net.core.rmem_default = 212992
net.core.rmem_max = 212992
net.core.wmem_default = 212992
net.core.wmem_max = 212992
net.ipv4.tcp_adv_win_scale = 1
net.ipv4.tcp_mem = 44544        59392   89088
net.ipv4.tcp_moderate_rcvbuf = 1
net.ipv4.tcp_rmem = 4096        131072  6291456
net.ipv4.tcp_wmem = 4096        16384   4194304
net.ipv4.udp_rmem_min = 4096
net.ipv4.udp_wmem_min = 4096
vm.lowmem_reserve_ratio = 256   256     32      0       0
```

### 3.1 不调整 RT，仅调整server的wmem参数
修改，限死 `wmem`
```
root@tcp-server:~# sysctl -w net.ipv4.tcp_wmem="4096 4096 4096"
net.ipv4.tcp_wmem = 4096 4096 4096
```
查看curl命令使用时间结果，下载速度很快，平均速度甚至大约不限制的情况
```
root@tcp-client:~# curl -O http://192.168.77.131/large_file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 2048M  100 2048M    0     0  48.4M      0  0:00:42  0:00:42 --:--:-- 43.5M
```

平均下载速度Average Dload: 48.4M

server抓包
```
root@tcp-server:~# tcpdump -i ens33 -s 120 "host 192.168.77.132" -w tcpdump-server-wmem4096.cap
tcpdump: listening on ens33, link-type EN10MB (Ethernet), capture size 120 bytes
^C55406 packets captured
55406 packets received by filter
0 packets dropped by kernel
```

client抓包
```
root@tcp-client:~# tcpdump -i ens33 "host 192.168.77.131" -w tcpdump-clinet-wmem4096.cap
tcpdump: listening on ens33, link-type EN10MB (Ethernet), capture size 262144 bytes
^C72485 packets captured
72485 packets received by filter
0 packets dropped by kernel
```

看stevens概览图，很平滑
![tcpdump-client-wmem4096-stevens-overview](/images/tcpdump-client-wmem4096-stevens-overview.png)

放大看stevens图，也没有很明显的延迟，两个包之间的ack时间也很短
![tcpdump-client-wmem4096-stevens-detail](/images/tcpdump-client-wmem4096-stevens-detail.png)

看看server的window窗口图，暂时也没看出啥特别的
![tcpdump-server-wmem4096-window-scaling](/images/tcpdump-server-wmem4096-window-scaling.png)

### 3.2 接下来对 client 端调整 rt 为 100ms，看下整个下载情况。
```
root@tcp-client:~# tc qdisc add dev ens33 root netem delay 100ms
root@tcp-client:~# 
root@tcp-client:~# curl -O http://192.168.77.131/large_file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 2048M  100 2048M    0     0  2497k      0  0:13:59  0:13:59 --:--:-- 11.4M
```
平均下载速度Average Dload: 2497k

很明显速度下降很多，最后的下载速度只有11.4M

从stevens图里看结果，斜度比较平，中途还有很大的曲折

![tcpdump-clinet-wmem4096-delay100-stevens-overview](/images/tcpdump-clinet-wmem4096-delay100-stevens-overview.png)

另一个角度看ack响应时间
![tcpdump-clinet-wmem4096-delay100-stevens](/images/tcpdump-clinet-wmem4096-delay100-stevens.png)

窗口明显上不去
![tcpdump-clinet-wmem4096-delay100-window-scaling](/images/tcpdump-clinet-wmem4096-delay100-window-scaling.png)

rtt时间也是很明显100以上
![tcpdump-clinet-wmem4096-delay100-rtt](/images/tcpdump-clinet-wmem4096-delay100-rtt.png)

### 3.3 调整 client 端调整 rt 为 10ms，看下整个下载情况。
```
root@tcp-client:~# tc qdisc del dev ens33 root
root@tcp-client:~# tc qdisc add dev ens33 root netem delay 10ms
root@tcp-client:~# curl -O http://192.168.77.131/large_file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 2048M  100 2048M    0     0   9.9M      0  0:03:25  0:03:25 --:--:-- 8479k
```

平均下载速度Average Dload: 9.9M

![tcpdump-clinet-wmem4096-delay10-stevens-overview](/images/tcpdump-clinet-wmem4096-delay10-stevens-overview.png)

![tcpdump-clinet-wmem4096-delay10-stevens](/images/tcpdump-clinet-wmem4096-delay10-stevens.png)


窗口明显上不去
![tcpdump-clinet-wmem4096-delay10-window-scaling](/images/tcpdump-clinet-wmem4096-delay10-window-scaling.png)


rtt时间也是很明显10以上
![tcpdump-clinet-wmem4096-delay10-rtt](/images/tcpdump-clinet-wmem4096-delay10-rtt.png)

与上述100ms对比，发现同样的`wmem 4096`参数下, rt越大，速度越慢


### 3.4 调整 client 端调整 rt 为 200ms，看下整个下载情况。

```
root@tcp-client:~# tc qdisc del dev ens33 root
root@tcp-client:~# tc qdisc add dev ens33 root netem delay 200ms
root@tcp-client:~# tc qdisc show dev ens33
qdisc netem 8005: root refcnt 2 limit 1000 delay 200.0ms
root@tcp-client:~# curl -O http://192.168.77.131/large_file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 2048M  100 2048M    0     0  2069k      0  0:16:53  0:16:53 --:--:-- 6733k
```

rt延迟时间200ms，平均下载速度Average Dload: 2069k

