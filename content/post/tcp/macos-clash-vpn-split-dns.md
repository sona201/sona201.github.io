---
title: "在 macOS 上让企业 VPN 与 Clash 共存"
description: "一次从 Shadowrocket 迁移到 Clash Verge Rev 的实际记录，梳理企业 VPN、系统代理、内部 DNS 分流、订阅更新和测速排查之间的关系。"
date: "2026-10-21T00:00:00+08:00"
lastmod: "2026-10-21T00:00:00+08:00"
categories: ["网络"]
tags: ["macOS", "Clash Verge Rev", "Mihomo", "VPN", "DNS"]
slug: "macos-clash-vpn-split-dns"
draft: false
---

我的 Mac 需要同时访问公司内网、国内网站和海外服务。在家要连接企业 VPN，在公司使用办公网络；个人代理原先使用 Shadowrocket。麻烦出在切换网络时：有时公司页面打不开，有时多个网站同时异常，重开两个客户端后又恢复了。

排查中还遇到了另一个问题：关闭代理测速能到两百多 Mbps，代理测速页面上却曾看到约 36 Mbps。最初很容易把这些现象归到同一个原因，但实际涉及物理链路、VPN 路由、DNS、代理节点和测速方法。

最后采用的组合是 **企业 VPN 保持公司要求的模式，Clash 使用系统代理，TUN 关闭，并只给 Clash 内部增加 DNS 分流**。公司规则保存在本地，节点订阅单独更新。本文记录这套配置的形成过程，以及每项测试能说明什么。

文中的公司域名、内网地址和服务器地址均使用示例值；不包含原始配置、订阅链接或账户截图。配置行为以本次使用的 Clash Verge Rev 2.5.8 和 Mihomo v1.19.32 为准。

## 先分清系统代理和 VPN 的职责

企业 VPN 被固定在全局模式，客户端不能切换为仅接管内网的模式。我能调整的是个人代理如何参与这条链路。

| 接管方式 | 作用范围 | 与企业 VPN 共存时需要留意的地方 |
| --- | --- | --- |
| 系统代理 | 由遵守系统代理设置的应用把请求交给本地代理端口 | 部分终端程序和应用不会自动遵守，需要单独配置或显式指定代理 |
| TUN | 通过虚拟网络接口接收被路由到该接口的流量 | 会增加路由和 DNS 接管关系，需要与企业 VPN 一起分析 |

这次把 Clash 的系统代理设为 `127.0.0.1:7897`，保持 TUN 关闭。企业 VPN 继续负责公司的网络接入，Clash 根据规则选择直连或个人节点。系统代理、TUN 决定流量如何进入客户端，规则模式则决定进入后的流量如何出站。[Clash Verge Rev 名词解释](https://www.clashverge.dev/guide/term.html)

这里有一个容易误解的地方：**Clash 的 `DIRECT` 只表示不经过它的代理节点，连接仍然遵循 macOS 的路由。** 企业 VPN 开启后，即使某个请求命中 `DIRECT`，也可能继续经过 VPN。反过来，Clash 连接个人节点的那条 TCP 连接也可能被 VPN 承载。下面的命令能查看路由表为目标选择的接口；实际连接还可能受接口绑定或 VPN 策略影响，不能只看策略组名字。

```bash
# 替换为自己的节点地址；这里使用文档示例地址
route -n get 192.0.2.20
scutil --proxy
scutil --dns
```

选择 Clash Verge Rev，主要是为了把本地规则、节点订阅和运行配置分别管理，并通过 API 验证实际命中。已有节点能继续使用，本次没有通过购买另一个客户端解决问题。Shadowrocket 保留作备用，验证 Clash 独立工作时则将它断开，避免把备用客户端提供的 DNS 或路由误认为 Clash 自身的能力。

## 迁移时把节点和本地规则分开

迁移后的配置包含一个节点订阅、19 个策略组和17 个规则集。节点通过 HTTP provider 每小时更新，规则集每天更新；公司域名和个人覆盖规则留在本地工作配置中。

这样刷新节点订阅时，不需要重新编辑公司内网规则，也不会因为订阅模板更新而丢掉本地调整。实际还检查了 provider 的更新时间、更新请求结果，以及重开客户端后策略组选择是否保留。

这套规则最终按下面的优先级处理流量：

| 优先级 | 匹配对象 | 处理方式 |
| --- | --- | --- |
| 最前面 | 公司域名、localhost、列出的 IPv4 私有网段 | `DIRECT` |
| 接着 | 已单独验证的域名覆盖 | 进入指定策略组或精确直连 |
| 再往后 | 海外服务规则集 | 对应服务组或通用代理组 |
| 后面 | 国内域名、国内 IP、局域网规则 | 本地直连 |
| 最后 | 未匹配流量 | 兜底代理组 |

Mihomo 按规则顺序匹配；域名规则提前命中后，不会再由后面的国内 IP 规则改判。`IP-CIDR` 中的 `no-resolve` 表示不要为了这一条规则主动解析域名，并不表示后面的规则也不会解析。[Mihomo 路由规则](https://wiki.metacubex.one/config/rules/)

公司域名同时配置了系统代理绕过列表和 Clash 内部的 `DIRECT` 规则。前者服务于遵守 macOS 代理设置的应用；后者也覆盖显式把请求交给 Clash 的程序。两层各有用途。

### 只给有证据的目标增加覆盖规则

Apple 的一个下载测速域名经过相邻对照，直连更快，因此只增加了精确规则：

```yaml
rules:
  - DOMAIN,mensura.cdn-apple.com,DIRECT
```

没有因此把整个 Apple 域名体系都设为直连。

Claude 的情况则是域名覆盖不足。原规则集已包含 `anthropic.com` 和 `claude.ai`，后来补充了以下五个后缀，并统一交给 `ClaudeAI`：

```yaml
rules:
  - DOMAIN-SUFFIX,claude.com,ClaudeAI
  - DOMAIN-SUFFIX,claude.dev,ClaudeAI
  - DOMAIN-SUFFIX,claudemcpclient.com,ClaudeAI
  - DOMAIN-SUFFIX,claudemcpcontent.com,ClaudeAI
  - DOMAIN-SUFFIX,claudeusercontent.com,ClaudeAI
```

其中捕获到的 `bridge.claudeusercontent.com` 连接，从通用代理组改为命中 `ClaudeAI`。这些组当时仍使用同一个节点，因此这是归类上的修正，不能直接解释为换了出口或提升了速度。

最后把“漏网之鱼”的选择从 `DIRECT` 改为代理。模式仍是规则模式，国内站点和公司域名继续优先匹配前面的规则。需要接受的取舍是：未被国内规则收录的站点，也可能落到兜底代理。

### 规则仓库和客户端如何配合

[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) 提供适配不同客户端的规则和相关脚本；本次使用的是其中的规则数据，并结合了 Loyalsoldier 的集合。[haoel.github.io](https://github.com/haoel/haoel.github.io) 则提供代理部署和网络优化的思路。它们可以作为配置来源与排查参考，不能直接替代本机的 VPN、路由和 DNS 验证。

服务端检查确认已有 VLESS Reality Vision、TCP 传输以及 BBR 和 fq。没有为这次问题继续叠加传输协议或多路复用：先确定慢在哪一段，再决定是否改服务端。

## 把 36 Mbps 拆成可以验证的问题

首先检查本地链路。有线网络那次故障中，当前网络位置缺少实际 USB 网卡对应的服务，旧服务绑定的接口已不存在。补齐服务并获取 DHCP 地址后，有线恢复，协商结果为 `100baseTX full-duplex`。

这个结果说明当时那条以太网链路的协商速率是 100 Mbps，不是运营商套餐的上限。Wi-Fi 显示的连接速率也属于无线链路指标，不能直接当作应用下载速度。服务器面板里的每月流量额度则是累计传输量，与 Mbps 带宽又是两个单位。

后续连接环境发生过变化，另一次有线记录已是千兆全双工，因此不能把下面超过 100 Mbps 的结果套到前述百兆链路上。换不同目标做限量测试后，也发现“代理固定只能跑 36 Mbps”的解释并不成立：

| 测试 | 当时结果 | 可以说明的范围 |
| --- | --- | --- |
| Cloudflare 页面完整测试 | 下载约 142 Mbps，上传约 44.6 Mbps | 该次完整页面测试的结果 |
| 同一页面的 1 MB 阶段 | 中位数约 35.7 Mbps | 小文件阶段可能明显低于完整结果 |
| Mac 经代理下载 Cloudflare 测试文件 | 约 134 Mbps | 当时代理路径可以超过 36 Mbps |
| Apple 限量双连接下载 | 直连约 186 Mbps，代理约 165 Mbps | 同一目标下代理有开销，但并非固定 36 Mbps |
| VPS 本机短时入站下载 | 约 1.47 Gbps | 服务器在该短样本中能够超过千兆 |

这些不是同一轮测试的所有分支，不能拼成一张精确的带宽损耗图。最后一项也没有证明 VPS 套餐的端口上限，更不能保证从家里到服务器的跨境链路达到同样速度。

测速还要检查 HTTP 状态码。一次多连接样本拿到的是 `403`，应作为无效吞吐样本排除；测速网页里的 WebRTC 或 UDP 指标，也不能直接当作 VLESS TCP 隧道的丢包率。

## DNS 结果不同是否就会让代理变慢

针对 Claude 和 Anthropic，做过一轮相邻的企业 VPN 开启、关闭、重新开启测试。过程中没有清理 DNS 缓存，也没有修改代理配置。

结果很明确：VPN 开启时，系统解析出现一组特定 CNAME 和地址；关闭后恢复为公共解析结果；重新开启后又回到前一组。同期直接查询家庭路由器和通过代理查询公共 DoH，返回的仍是公共结果。

这说明差异与 **VPN 启用后的 DNS 路径** 有关。它还不足以说明是客户端 Bug、恶意污染，或之前整机断网的根因。

接下来保持 Host、SNI 和证书校验不变，对不同地址实际建立连接。在当时的正常 Clash 代理路径上，Anthropic 普通域名请求与固定公共 IP 请求的首字节耗时中位数分别约为 `804 ms` 和 `807 ms`；Claude 为 `801 ms` 和 `794 ms`，差别很小。

还有一个更容易误判的现象：连接面板里显示过某个解析地址，正常域名请求却能成功；强制代理节点连接这个地址时反而发生 TLS 错误。对于保留域名的 VLESS TCP 请求，目标可能交给远端继续解析；实际行为还受 metadata 状态影响。因此，**单看客户端的 `destinationIP`，不能证明服务器最终拨号的就是这个地址**。[Mihomo v1.19.32 VLESS 实现](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/adapter/outbound/vless.go)、[metadata 处理](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/constant/metadata.go)

另一轮在 VPN 关闭时，把 Mac 经过代理的请求与 VPS 本机请求放在同一时段比较：

| 目标 | Mac 经代理的首字节耗时 | VPS 本机的首字节耗时 |
| --- | --- | --- |
| Anthropic trace | 约 818 ms | 约 43 ms |
| Claude trace | 约 801 ms | 约 28 ms |

Mac 到节点端口的 TCP 建连中位数约 195 ms；同一连接复用后，请求耗时从约 787 ms 降到约 198 ms、192 ms。这个组合更支持继续检查客户端到节点的链路和连接建立成本，而不是直接给目标网站固定 IP。这里测的是小型 HTTP trace 请求，不是模型首 token 时间。

## 只给 Clash 增加内部 DNS 分流

最后增加 DNS 分流，目的是明确不同域名的解析路径。它没有把整台 Mac 的 DNS 都改成交给 Clash，也不以提高所有网站速度为前提。

采用的分工是：

- 公司域名、局域网域名和未匹配域名继续用 `system`。
- 国内域名集合使用国内 DNS。
- Claude 相关域名通过 `ClaudeAI` 查询境外 DoH，其他已知境外域名经 `DNS_Proxy` 查询。
- 节点域名单独配置直接可用的解析器，避免“先有代理才能查 DNS、先查 DNS 才能连接代理”的循环。

下面是脱敏后的 **配置片段**。它要求已有 `ClaudeAI`、`DNS_Proxy` 策略组，以及 `cn-domains`、`proxy-domains` 规则集；应将名称对应到自己的配置，不能单独当作完整订阅启动。

```yaml
dns:
  enable: true
  listen: 127.0.0.1:1053
  enhanced-mode: redir-host
  ipv6: true
  prefer-h3: false
  use-hosts: true
  use-system-hosts: true
  respect-rules: false
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  proxy-server-nameserver:
    - "223.5.5.5#DIRECT"
    - "119.29.29.29#DIRECT"
  nameserver:
    - system
  nameserver-policy:
    "+.corp.example": [system]
    "+.local": [system]
    "+.lan": [system]
    "+.arpa": [system]
    "localhost": [system]
    "+.anthropic.com":
      - "https://1.1.1.1/dns-query#ClaudeAI"
      - "https://8.8.8.8/dns-query#ClaudeAI"
    "+.claude.ai":
      - "https://1.1.1.1/dns-query#ClaudeAI"
      - "https://8.8.8.8/dns-query#ClaudeAI"
    "+.claude.com":
      - "https://1.1.1.1/dns-query#ClaudeAI"
      - "https://8.8.8.8/dns-query#ClaudeAI"
    "+.claude.dev":
      - "https://1.1.1.1/dns-query#ClaudeAI"
      - "https://8.8.8.8/dns-query#ClaudeAI"
    "+.claudemcpclient.com":
      - "https://1.1.1.1/dns-query#ClaudeAI"
      - "https://8.8.8.8/dns-query#ClaudeAI"
    "+.claudemcpcontent.com":
      - "https://1.1.1.1/dns-query#ClaudeAI"
      - "https://8.8.8.8/dns-query#ClaudeAI"
    "+.claudeusercontent.com":
      - "https://1.1.1.1/dns-query#ClaudeAI"
      - "https://8.8.8.8/dns-query#ClaudeAI"
    "rule-set:proxy-domains":
      - "https://1.1.1.1/dns-query#DNS_Proxy"
      - "https://8.8.8.8/dns-query#DNS_Proxy"
    "rule-set:cn-domains":
      - "223.5.5.5#DIRECT"
      - "119.29.29.29#DIRECT"
```

`nameserver-policy` 指定域名的解析上游，`#ClaudeAI` 指定上游连接使用的代理组。没有另设 `direct-nameserver`，让直接连接的解析也继续遵循域名策略，避免用公共 DNS 覆盖公司域名的解析路径。[Mihomo DNS 配置](https://wiki.metacubex.one/config/dns/)

这里保留未知域名走 `system`，是为了兼容未完整列出的内网名称。所以，**流量兜底走代理，与未知域名的 DNS 也走海外 DoH，是两项不同设置。** 本次只实现了前者。

`system` 也有版本边界：v1.19.32 在 macOS 上读取 `/etc/resolv.conf` 的 nameserver 列表，约五分钟的刷新阈值由查询触发，并非完整复刻 macOS 的 scoped DNS 选择机制。切换 VPN 后的行为需要另外验证。[system DNS 实现](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/dns/system.go)、[POSIX 解析器读取](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/dns/system_posix.go)

## 先隔离验证再应用

修改前备份工作配置、生成的运行配置、策略选择和应用设置，再运行核心配置校验。

真正应用前，先启动临时实例：使用另一个代理端口、独立控制接口和规则缓存，不改变系统代理。临时实例必须等规则集全部加载完成再测试；API 已经开始监听，不代表所有规则和数据文件都已就绪。

验证包括公司域名的系统访问与显式代理访问、Claude 和 Anthropic 的 HTTPS 请求、国内网站，以及 1053 的 TCP 和 UDP 查询。还要看实际命中的规则，不能只凭 YAML 内容判断已经生效。

```bash
# 查看系统仍在使用哪些 DNS
scutil --dns

# 单独验证 Clash 内部解析，替换示例公司域名
dig @127.0.0.1 -p 1053 devops.corp.example A
dig @127.0.0.1 -p 1053 claude.ai A +tcp

# curl 显式走 Clash，避免依赖它是否读取系统代理
curl --proxy http://127.0.0.1:7897 --noproxy '' \
  --connect-timeout 8 --max-time 15 \
  -o /dev/null -w 'code=%{http_code} total=%{time_total}\n' \
  https://claude.ai/cdn-cgi/trace

# 验证系统解析和路由；仍可能经过企业 VPN
curl --noproxy '*' --connect-timeout 5 --max-time 10 \
  -o /dev/null -w 'code=%{http_code}\n' \
  http://devops.corp.example/
```

正式应用后，公司入口返回正常 `302` 跳转，Claude、Anthropic、百度、B 站请求返回 `200`，Google 探针返回 `204`。公司规则、订阅每小时更新、40 条路由规则和策略组选择都保留；系统 DNS 没有改动，TUN 仍关闭。这些结果验证的是解析与请求连通性，不代表所有登录流程、Claude Code 任务或长连接都已覆盖。

首次并发验证中，境外 DoH 曾耗时约 4.4 秒，Claude 请求约 7.67 秒。随后在同一网络同时运行旧、新配置，两轮 Claude 总耗时分别是 `1.920 / 1.926 秒` 和 `1.277 / 1.280 秒`，未见明显回归。冷启动开销和链路波动仍然存在。

此前在内部 DNS 关闭时，做过保持 Clash 进程不变、反复关闭和连接企业 VPN 的测试，公司内网和外网请求能够恢复；但新 DNS 配置后的对应测试被中断，尚未完成。因此目前能确认的是这份配置已生效、当前路径可用，不能据此承诺以后切网都无需等待或重启。

下次遇到异常，我会先保留当时的进程、路由、DNS 和请求结果，再逐项切换。只有保留下失败现场，才有机会分清究竟是解析器没有切换、节点链路波动，还是应用持有的旧连接还没恢复。
