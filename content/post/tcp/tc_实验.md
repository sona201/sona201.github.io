---
title: "Tc_实验"
description: "tcp的tc实验记录"
date: "2023-05-19T01:05:14+08:00"
lastmod: "2023-07-03T13:05:14+08:00"
categories: ["tcp"]
tags: ["wmem", "tc", "实验"]
image: 
style:
    background: "#2a9d8f"
    color: "#fff"
---

公开版中的命令和输出已做脱敏处理，地址使用文档示例网段，账号和主机名使用占位名称；原始抓包截图不再公开。请按自己的测试环境替换示例值。

## 排查python server当时的系统信息

发现并没有异常，仅记录`device eth0 entered promiscuous mode`表示当时网卡 eth0 进入混杂模式,应该与当时启用tcpdump有关。

## 一、将python server改为nginx server方式，测试下载有没有异常
```
[root@example-host ~]# curl -O http://192.0.2.21/404.html
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  3650  100  3650    0     0  2313k      0 --:--:-- --:--:-- --:--:-- 3564k
[root@example-host ~]# curl -O http://192.0.2.21/sample.bin
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 1880M  100 1880M    0     0   396M      0  0:00:04  0:00:04 --:--:--  396M
```

一切正常

## 二、服务端参数修改异常参数测试
使用nginx server，设置成`net.ipv4.tcp_wmem="4096 4096 4096"`

顺便记录下nginx配置
```
server {
    listen       80;
    listen       [::]:80;
    server_name  _;
    root         /usr/share/nginx/html;

    # Load configuration files for the default server block.
    # include /etc/nginx/default.d/*.conf;

    error_page 404 /404.html;
    location = /404.html {
    }

    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
    }
}
```

#### 命令行窗口1
```
[root@example-host ~]# curl -O http://192.0.2.21/sample.bin
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:--  0:00:13 --:--:--     0
```

#### 命令行窗口2
```
[root@example-host ~]# curl -O http://192.0.2.21/404.html
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  3650  100  3650    0     0  2676k      0 --:--:-- --:--:-- --:--:-- 3564k
[root@example-host ~]# curl -O http://192.0.2.21/sample.bin
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:--  0:01:00 --:--:--     0^C
[root@example-host ~]# curl -O http://192.0.2.21/404.html
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  3650  100  3650    0     0  2664k      0 --:--:-- --:--:-- --:--:-- 3564k
```

### 2.2 测试改为异常数据的临界值，使用二分法测试
```
[root@example-host html]# sysctl -w net.ipv4.tcp_wmem="4096 4096 9000"
net.ipv4.tcp_wmem = 4096 4096 9000
# 这个可以正常下载
[root@example-host html]# sysctl -w net.ipv4.tcp_wmem="4096 4096 8259"
net.ipv4.tcp_wmem = 4096 4096 8259
# 这个可以正常下载
[root@example-host html]# sysctl -w net.ipv4.tcp_wmem="4096 4096 8257"
net.ipv4.tcp_wmem = 4096 4096 8257
[root@example-host html]# sysctl -w net.ipv4.tcp_wmem="4096 4096 8258"
net.ipv4.tcp_wmem = 4096 4096 8258
# 这个不能下载
```

> 结论：参数配置再 `net.ipv4.tcp_wmem="4096 4096 8258"` 及以下不能正常请求

## 三、排除文件原因，使用dd生成2G文件

设置为`sysctl -w net.ipv4.tcp_wmem="4096 4096 4096"`,大文件确实会被卡住，小文件不受影响。

用`dd if=/dev/zero of=large_file bs=1G count=2`生成的文件2G大小文件。

#### 命令行窗口1
```
[root@example-host ~]# curl -O http://192.0.2.21/large_file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:--  0:00:04 --:--:--     0
```
#### 命令行窗口2
```
[root@example-host ~]# curl -O http://192.0.2.21/404.html
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  3650  100  3650    0     0  2905k      0 --:--:-- --:--:-- --:--:-- 3564k
```

同样，换成 large_file 文件一样不能下载。得出结果与之前文件一致：
- 临界值就是在`net.ipv4.tcp_wmem = 4096 4096 8259`
- 下载大文件卡住时，同时下载小文件不受影响。

## 四、确认内核版本
当前是用的linux版本内核为
```
[root@example-host html]# uname -a
Linux 192.0.2.21 3.10.0-957.27.2.el7.x86_64 #1 SMP Mon Jul 29 17:46:05 UTC 2019 x86_64 x86_64 x86_64 GNU/Linux
```

