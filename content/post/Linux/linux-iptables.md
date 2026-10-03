---
title: "Linux iptables 使用笔记"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["Linux"]
tags: ["linux", "iptables", "firewall"]
draft: false
---

#iptable #linux 

本文主要介绍如下几点内容。

- [禁止Filewalld开机启动](https://help.aliyun.com/zh/ecs/how-to-use-iptables-in-centos7#HMwSJ)
- [安装iptables](https://help.aliyun.com/zh/ecs/how-to-use-iptables-in-centos7#bkQcB)
- [启动iptables并设置为开机启动](https://help.aliyun.com/zh/ecs/how-to-use-iptables-in-centos7#xxJAA)
- [查看并修改iptables默认规则](https://help.aliyun.com/zh/ecs/how-to-use-iptables-in-centos7#wQHtr)

### 禁止Filewalld开机启动

为了防止与iptables冲突，您必须先禁止Filewalld开机启动。

#### 1. 查看`firewalld`服务状态。

```bash
systemctl status firewalld
```

#### 2. 当服务处于active状态，运行以下命令关闭Firewalld服务。

```bash
systemctl stop firewalld
```

#### 3. 执行如下命令，禁止Filewalld开机启动。

```bash
systemctl disable firewalld
```

### 安装iptables

#### 安装iptables。

```bash
yum install -y iptables-services
```

### 启动iptables并设置为开机启动

#### 1. 启动iptables。

```bash
systemctl start iptables
```

#### 2. 查看iptables是否成功启动。

```bash
systemctl status iptables
```

#### 3. 设置iptables开机启动。

```bash
systemctl enable iptables.service
```

#### 4. 设置完成后，重启实例验证配置。

```bash
systemctl reboot
```

### 查看并修改iptables默认规则

执行`iptables -L`命令，查看iptables默认规则，发现在默认规则下，INTPUT链允许来自任何主机的访问。可以参考如下步骤修改默认规则。

#### 1. 如果之前已经设置过规则，建议执行如下命令，备份原有的iptables文件，避免之前设置的规则丢失。

```bash
cp -a /etc/sysconfig/iptables /etc/sysconfig/iptables.bak
```

#### 2. 清空所有规则。

```bash
iptables -F
```

#### 3. 根据业务需求添加规则，放行或者禁用端口。示例：依次执行如下命令，放行80端口和22端口。

```bash
iptables -I INPUT -p tcp --dport 80 -m state --state NEW -j ACCEPT  
iptables -I INPUT -p tcp --dport 22 -m state --state NEW -j ACCEPT
```

> 示例：依次执行如下命令，添加规则，使INPUT链拒绝所有请求，即ECS实例会拒绝所有请求。如果是线上业务请勿直接操作，会直接中断业务。  

```bash
iptables -P INPUT DROP
```

#### 4. 确认新规则生效。

```bash
iptables -L
```

#### 5. 保存添加的规则。

```bash
iptables-save > /etc/sysconfig/iptables
```
#### 6. 将规则导入到iptables
```bash
iptables-restore < /etc/sysconfig/iptables
```

### 案例：实际操作命令

#### 仅对相关ip开放22端口

```bash
sudo iptables -A INPUT -p tcp -s 10.20.105.62 --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp -s 10.20.105.56 --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp -s 10.20.105.57 --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp -s 10.20.105.54 --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp -s 10.20.105.55 --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j DROP
iptables-save >/etc/sysconfig/iptables
```


