---
title: "文件上传卡住时排查 TCP Zero Window 与 Nginx 缓冲"
date: "2023-06-28T15:52:28+08:00"
lastmod: "2023-06-28T15:52:28+08:00"
categories: ["tcp"]
slug: "nginx-upload-zero-window-troubleshooting"
draft: false
---

# 文件上传卡住时的 TCP 与 Nginx 排查

## 一、背景
我写了一个python服务，里面有个文件上传的功能，直接把本地文件上传到服务器
我的服务：入口是nginx，用gunicorn 启动 django 框架
本地测试"文件上传接口"，170M的文件传输没有问题，但部署在服务器上，传输会卡在47%的进度条这里。
分析抓包，发现上传卡死的时候，会出现 tcp zero window，window窗口直接变0，然后一直不会恢复

## 二、实验环境

入口为 Nginx，后端使用 Gunicorn 启动 Django，监听 `127.0.0.1:8000`。当时服务器使用 Linux 3.10 内核。此前做过 `tc` 实验，排查时先确认原有延迟和丢包规则已经清理。

## 三、最初的排查思路

最初怀疑是否需要通过内核参数强制 reset 连接，后来发现，应先检查接收方应用是否及时读取数据，以及反向代理的缓冲行为。

## 四、解决方案


确认 TCP 出现 `Zero Window` 后，最初认为可以通过调整某个内核参数直接解决。后续排查发现，窗口变为零只描述接收方暂时无法继续接收的状态，仍需要找到具体原因。

![kernel_tcp_cache](/images/kernel_tcp_cache.png)

TCP 数据先进入接收方的套接字接收缓冲区，再由应用读取。当接收方通告的可用接收窗口变为零时，发送方需要等待窗口恢复；排查时需要结合缓冲区状态和应用读取数据的行为。

后续想到一个方法就是进行抓包，诡异的是，最外层nginx暴露的是443端口，抓包有数据，但python服务8000端口抓包却没有数据，最后发现是抓包条件有问题，在服务器上应该


抓取nginx数据包
```
sudo tcpdump -i eth0 "tcp port 443"
```

因为python服务是绑定是本地网卡，
```
sudo netstat -lntp
# 本例只保留与上传链路相关的两条监听信息：
# Nginx: 0.0.0.0:443
# Gunicorn: 127.0.0.1:8000
```

根据网卡的 `inet` 来判断当前使用的网卡为lo，所以用如下命令进行python服务抓包

```
tcpdump -i lo "tcp port 8000"
```

通过抓包发现，当传输一个大文件时，在nginx端能抓包，但在python端却没有数据，最开始是tcpdump直接写入文件，发现python抓包数据包为0，后面就改为直接标准输出

通过输出发现当进行文件传输时，nginx有数据，但python没有数据，这时开始怀疑是不是nginx的问题，多次搜索后发现`python`的`Gunicorn`服务建议nginx配置参数
```
proxy_buffering off;
```
这个参数在前端传大`json`文件给后端时也有人遇到过，似乎看到一丝希望，兴致冲冲的配置玩参数后测试，还是nginx端接收完数据最后一次性传给后端，外加几个`buffer_size`的结果还是一样，
这就让我郁闷，我开始怀疑nginx版本问题，查看怎么确认参数是否正确，是否生效，但并没有找到一个标准结果，无奈只能先放弃

后来在搜索 `proxy_buffering` 时发现了 `proxy_request_buffering`。两者方向不同：前者控制从上游收到的响应缓冲，后者控制发往上游的请求体缓冲。

关闭请求体缓冲后重新测试，大文件上传期间，Nginx 与 Python 后端都能同时抓到数据，说明请求体开始持续传给上游。

保留一个只展示关键请求缓冲参数的配置示例：

```nginx
upstream app_backend {
    server 127.0.0.1:8000;
}

server {
    listen 8080;
    server_name localhost;
    client_max_body_size 200m;

    location /api/ {
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_request_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

至此，这个问题暂时先告一段落，不过这次也确实会发现不像以前特别害怕排查这类问题，完全没有思路，也不知道怎么面对`wireshark`

## 参考文件
[Gunicorn Doc](https://docs.gunicorn.org/en/latest/deploy.html) \
[MySQL JDBC StreamResult通信原理浅析](https://blog.csdn.net/xieyuooo/article/details/83109971) \
[wireshark tcp segment of a reassembled pdu](https://www.wireshark.org/lists/wireshark-users/200805/msg00206.html#:~:text=1.-,what%20does%20%22TCP%20segment%20of%20a%20reassembled%20PDU%22%20mean%3F,packet%20will%20show%20the%20packet.) \
[TCP报文（ tcp dup ack 、TCP Retransmission）](https://blog.csdn.net/ynchyong/article/details/109110028) \
[两张动图-彻底明白TCP的三次握手与四次挥手](https://blog.csdn.net/qzcsu/article/details/72861891) \
[Nginx的proxy buffer参数总结](https://www.cnblogs.com/wshenjin/p/11608744.html) \
[Module ngx_http_proxy_module](http://nginx.org/en/docs/http/ngx_http_proxy_module.html) \
[nginx-proxy-request-buffering-is-not-working-as-expected](https://stackoverflow.com/questions/47125684/nginx-proxy-request-buffering-is-not-working-as-expected)
