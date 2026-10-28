---
title: "Wireshark技巧"
description: "阅读wireshark说明书的笔记"
date: "2023-05-19T01:05:14+08:00"
lastmod: "2023-07-03T13:05:14+08:00"
image: 
categories: ["tcp"]
tags: ["tcp", "wireshark", "技巧"]
style:
    background: "#2a9d8f"
    color: "#fff"
---

公开版中的命令和输出已做脱敏处理，地址使用文档示例网段，账号和主机名使用占位名称；原始抓包截图不再公开。请按自己的测试环境替换示例值。

[相关文章](https://developer.aliyun.com/article/100476) \
[Wireshark 用户指南](https://www.wireshark.org/docs/wsug_html_chunked/) \
[用 Wireshark 分析 TCP 吞吐瓶颈](https://www.kawabangga.com/posts/4794)

wireshark你一定会喜欢的技巧摘要

1. 修改seq的为绝对值 relative
2. 配置rt
3. 分析

[分析图](https://www.kawabangga.com/posts/4794)

wireshark https 抓包 tls contains "baidu.com"

> wireshark 没有权限

```text
You do not have permission to capture on device "utun7".
((cannot open BPF device) /dev/bpf0: Permission denied)

Please check to make sure you have sufficient permissions.

If you installed Wireshark using the package from wireshark.org, close this dialog and click on the "installing ChmodBPF" link in "You can fix this by installing ChmodBPF." on the main screen, and then complete the installation procedure.
```

或者下图

命令行赋权

1. 直接简单粗暴的777
```
sudo chmod 777 /dev/bpf*
```

2. 查看当前用户名，给当前用户赋权
```
sudo chown clin:wheel /dev/bpf*
```

> 本来这个命令都不打算记录，但最近在自己电脑上重新安装就出现一次，还是老老实实的记录下

### 一、抓包
拿到一个网络包时，我们总是希望它尽可能小。因为操作一个大包相当费时，有时甚至会死机。如果让初学者分析1GB以上的包，估计会被打击得信心全无。所以抓包时应该尽量只抓必要的部分。有很多方法可以实现这一点。

1．只抓包头。一般能抓到的每个包（称为“帧”更准确，但是出于表达习惯，本书可能会经常用“包”代替“帧”和“分段”）的最大长度为1514字节，启用了Jumbo Frame（巨型帧）之后可达9000字节以上，而大多数时候我们只需要IP头或者TCP头就足够分析了。在Wireshark上可以这样抓到包头：单击菜单栏上的Capture-->Options，然后在弹出的窗口上定义“Limit each packet to”的值。我一般设个偏大的数字：80字节，也就是说每个包只抓前80字节。这样TCP层、网络层和数据链路层的信息都可以包括在内。
> 3.0之前版本wireshark更改方式

> 3.0之后的版本

如果问题涉及应用层，就应该再加上应用层协议头的长度。如果你像我一样经常忘记不同协议头的长度，可以输入一个大点的值。即便设成200字节，也比1514字节小多了。\
以上是使用Wireshark抓包时的建议。用tcpdump命令抓包时可以用“-s”参数达到相同效果。比如以下命令只抓eth0上每个包的前80字节，并把结果存到/tmp/tcpdump.cap文件中。

使用`tcpdump`指定抓包字节命令
```
[root@example-host /]# tcpdump -i eth0 -s 80 -w /tmp/tcpdump.cap
```

2．只抓必要的包。服务器上的网络连接可能非常多，而我们只需要其中的一小部分。Wireshark的Capture Filter可以在抓包时过滤掉不需要的包。比如在成百上千的网络连接中，我们只对IP为192.0.2.22的包感兴趣，那就可以在Wireshark上这样设置：单击菜单栏上的Capture-->Options，然后在Capture Filter中输入“host 192.0.2.22”。

> 老版本

> Version 4.0.5版本

#### [wireshark官方的过滤文档](https://wiki.wireshark.org/CaptureFilters)

用tcpdump命令抓包时，也可以用“host”参数达到相同效果。比如以下命令只抓与192.0.2.22通信的包，并把结果存到/tmp/tcpdump.cap文件中。

```
[root@example-host /]# tcpdump -i eth0 host 192.0.2.22 -w /tmp/tcpdump.cap
```

#### 注意：设置Capture Filter之前务必三思，以免把有用的包也过滤掉，尤其是容易被忽略的广播包。当然有时候再怎么考虑也会失算，比如我有一次把对方的IP地址设为filter，结果一个包都没抓到。最后只能去掉filter再抓，才发现是NAT（网络地址转换）设备把对方的IP地址改掉了。
抓的包除了要小，最好还能为每步操作打上标记。这样的包一目了然，赏心悦目。比如要在Windows上抓一个包含三步操作的问题，我会这样抓。

想指定ping，发送三次包，每次只发送一个`ping`包(`count`)，不通次数发送的`ping`的`size`大小不一样，

windows机器指定ping方式
```
（1）ping <IP> -n 1 -l 1
（2）操作步骤1
（3）ping <IP> -n 1 -l 2
（4）操作步骤2
（5）ping <IP> -n 1 -l 3
（6）操作步骤3
```

windows ping命令解释
```
用法: ping [-t] [-a] [-n count] [-l size] [-f] [-i TTL] [-v TOS]
            [-r count] [-s count] [[-j host-list] | [-k host-list]]
            [-w timeout] [-R] [-S srcaddr] [-c compartment] [-p]
            [-4] [-6] target_name

选项:
    -t             Ping 指定的主机，直到停止。
                   若要查看统计信息并继续操作，请键入 Ctrl+Break；
                   若要停止，请键入 Ctrl+C。
    -a             将地址解析为主机名。
    -n count       要发送的回显请求数。
    -l size        发送缓冲区大小。
    -f             在数据包中设置“不分段”标记(仅适用于 IPv4)。
    -i TTL         生存时间。
    -v TOS         服务类型(仅适用于 IPv4。该设置已被弃用，
                   对 IP 标头中的服务类型字段没有任何
                   影响)。
    -r count       记录计数跃点的路由(仅适用于 IPv4)。
    -s count       计数跃点的时间戳(仅适用于 IPv4)。
    -j host-list   与主机列表一起使用的松散源路由(仅适用于 IPv4)。
    -k host-list    与主机列表一起使用的严格源路由(仅适用于 IPv4)。
    -w timeout     等待每次回复的超时时间(毫秒)。
    -R             同样使用路由标头测试反向路由(仅适用于 IPv6)。
                   根据 RFC 5095，已弃用此路由标头。
                   如果使用此标头，某些系统可能丢弃
                   回显请求。
    -S srcaddr     要使用的源地址。
    -c compartment 路由隔离舱标识符。
    -p             Ping Hyper-V 网络虚拟化提供程序地址。
    -4             强制使用 IPv4。
    -6             强制使用 IPv6。
```

mac/linux ping命令执行
```
ping <IP> -c 1 -s 1
操作步骤1
ping <IP> -c 1 -s 2
操作步骤2
ping <IP> -c 1 -s 3
操作步骤3
```

> 这个抓包在mac上命令方式不一样，导致我一直没有执行成功

如图3所示，如果我需要分析步骤1，则只要看146～183之间的包即可。注意到146号包最底下的“Data（1 byte）”了吗？byte的数目表示是第几步，这样就算在步骤很多的情况下也不会混乱。 \
抓包的技巧还有很多，比如可以写一个脚本来循环抓包，等侦察到某事件时自动停止。一位工程师即便不懂网络分析，但如果能抓得一手好包，也是一项很了不起的技能了。

### 二、个性化设置
Wireshark的默认设置堪称友好，但不同用户的从事领域和使用习惯各有不同，所以有时需要根据自己的情况对配置略作修改。

1．我经常需要参照服务器上的日志时间，找到发生问题时的网络包。所以就把Wireshark的时间调成跟服务器一样的格式。单击Wireshark的View-->Time Display Format-->Date and Time of Day，就可以实现此设置。

Version 4.0.5版本设置

2．不同类型的网络包可以自定义颜色，比如网络管理员可能会把OSPF等协议或者与Spanning Tree Protocol（生成树协议）相关的网络包设成最显眼的颜色。而文件服务器的管理员则更关心FTP、SMB和NFS协议的颜色。我们可以通过View -->Coloring Rules来设置颜色。如果同事已经有一套非常适合你工作内容的配色方案，可以请他从Coloring Rules窗口导出，然后导入到你的Wireshark里。记得下次和他吃饭时主动买单，要知道配一套养眼的颜色可要花不少时间。

3．更多的设置可以在Edit-->Preferences窗口中完成。这个窗口的设置精度可以达到一些协议的细节。比如在此窗口单击Protocols-->TCP就可以看到多个TCP相关选项，将鼠标停在每一项上都会有详细介绍。假如经常要对Sequence Number做加减运算，不妨选中Relative sequence numbers，这样会使Sequence number看上去比实际小很多。

4．如果你在其他时区的服务器上抓包，然后下载到自己的电脑上分析，最好把自己电脑的时区设成跟抓包的服务器一样。这样，Wireshark显示的时间才能匹配服务器上日志的时间。比如说，服务器的日志显示2/13/2014 13:01:32有一个错误信息。那我们要在自己电脑上调整时区之后，才能到Wireshark上检查2/13/2014 13:01:32左右的包，否则就得先换算时间。

三、过滤
很多时候，解决问题的过程就是层层过滤，直至找到关键包。前面已经介绍过抓包时的Capture Filter功能了。其实在包抓下来之后，还可以进一步过滤，而且这一层的过滤功能更加强大。例如，一个"IP为192.0.2.10，且TCP端口为445"的过滤表达式可以写为 `ip.addr == 192.0.2.10 && tcp.port == 445`。

要说过滤的作用与技巧，就算专门写一本小册子都不为过。篇幅所限，本文只能"过滤"出最适合初学者的部分。

1．如果已知某个协议发生问题，可以用协议名称过滤一下。以Windows Domain的身份验证问题为例，如果已知该域的验证协议是Kerberos，那么就在Filter框输入Kerberos作为关键字过滤。除了纯粹的Kerberos包，你还将得到Session Setup之类包含Kerberos的包。

用协议过滤时务必考虑到协议间的依赖性。比如NFS共享挂载失败，问题可能发生在挂载时所用的mount协议，也可能发生在mount之前的portmap协议。这种情况下就需要用"portmap || mount"来过滤了。如果不懂协议间的依赖关系怎么办？我也没有好办法，只能暂时放弃这个技巧，等熟悉了该协议后再用。

2．IP地址加port号是最常用的过滤方式。除了手工输入ip.addreq &&tcp.porteq<端口号>之类的过滤表达式，Wireshark还提供了更快捷的方式：右键单击感兴趣的包，选择Follow TCP/UDP Stream（选择TCP还是UDP要视传输层协议而定）就可以自动过滤。而且该Stream的对话内容会在新弹出的窗口中显示出来。

经常有人在论坛上问，Wireshark是按照什么过滤出一个TCP/UDP Stream的？答案就是：两端的IP加port。单击Wireshark的Statistics-->Conversations，再单击TCP或者UDP标签就可以看到所有的Stream。

3．用鼠标帮助过滤。我们有时因为Wireshark而苦恼，并不是因为它功能不够，而是强大到难以驾驭。比如在过滤时，有成千上万的条件可供选择，但怎么写才是合乎语法的？虽然 [http://www.wireshark.org/docs/dfref/](http://www.wireshark.org/docs/dfref/) 提供了参考，但经常查找毕竟太费时费力了。Wireshark考虑到了这个需求，右键单击Wireshark上感兴趣的内容，然后选择Prepare a Filter-->Selected，就会在Filter框中自动生成过滤表达式。在有复杂需求的时候，还可以选择And、Or等选项来生成一个组合的过滤表达式。

假如右键单击之后选择的不是Prepare a Filter，而是Apply as Filter-->Selected，则该过滤表达式生成之后还会自动执行。图12显示了在一个SMB包的SMB Command: Read AndX上右键单击，并选择Selected之后，所有的Read包都会被过滤出来。

4．我们可以把过滤后得到的网络包存在一个新的文件里，因为小文件更方便操作。单击Wireshark的File-->Save As，选中Displayed单选按钮再保存，得到的新文件就是过滤后的部分。

有时候你会发现，保存后的文件再打开时会显示很多错误。这是因为过滤后得到的不再是一个完整的TCP Stream，就像抓包时漏抓了很多一样。所以选择Displayed选项时要慎重考虑。

注意：有些Wireshark版本把这个功能移到了菜单File-->Export Specified Packets…选项中，如下图所示。

总体来说，过滤是Wireshark中最有趣，最难，也是最有价值之处，值得我们用心学习。

四、让Wireshark自动分析
有些类型的问题，我们根本不需要研究包里的细节，直接交给Wireshark分析就行了。

1．单击Wireshark的Analyze-->Expert Info Composite，就可以在不同标签下看到不同级别的提示信息。比如重传的统计、连接的建立和重置统计，等等。在分析网络性能和连接问题时，我们经常需要借助这个功能。下图是TCP包的重传统计。

2．单击Statistics-->Service Response Time，再选定协议名称，可以得到响应时间的统计表。我们在衡量服务器性能时经常需要此统计结果。图16展示的是SMB2读写操作的响应时间。

> 4.0.5版本的协议很少，甚至没有看到tcp协议，把所有协议看了，只有NCP、SMB两种协议有内容，内容不像分析数据。

3．单击Statistics-->TCP Stream Graph，可以生成几类统计图。比如我曾经用Time-Sequence Graph (Stevens)生成了下图。

从老图中可以看出25～40秒，以及65～75秒之间没有传输数据。进一步研究，发现发送方内存不足，所以偶尔出现暂停现象，添加内存后问题就解决了。

为什么Wireshark要把这个图称为“Stevens”呢？我猜是为了向《TCP/IP Illustrated》的作者Richard Stevens致敬。这也是我非常喜欢的一套书，在此推荐给所有读者。

4．单击Statistics-->Summary，可以看到一些统计信息，比如平均流量等，这有助于我们推测负载状况。比如下图中的网络包才1.594Mbit/s，说明流量低得很。

Version 4.0.5版本没有找到 Statistics-->Summary 选项，但找到 Statistics-->Conversations(对话)，但看起来结果差不多

Version 4.0.5版本没有找到 Statistics-->Summary 选项，但找到 Statistics-->Capture File Properties，菜单改了

参考最新菜单解释[https://www.wireshark.org/docs/wsug_html_chunked/ChUseStatisticsMenuSection.html](https://www.wireshark.org/docs/wsug_html_chunked/ChUseStatisticsMenuSection.html)

五、最容易上手的搜索功能
与很多软件一样，Wireshark也可以通过“Ctrl+F”搜索关键字。假如我们怀疑包里含有“error”一词，就可以按下“Ctrl+F”之后选中“String”单选按钮，然后在Filter中输入“error”进行搜索。很多应用层的错误都可以靠这个方法锁定问题包。

一篇文章不可能涵盖所有技巧，本文就到此为止。最后要分享的，是我认为最“笨”但也是最重要的一个技巧——勤加练习。只要练到这些技巧都变成习惯，就可以算登堂入室了。
