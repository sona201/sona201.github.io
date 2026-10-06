---
title: "Linux 本地用户与 LDAP 同名冲突排查"
date: "2023-07-29T23:29:50+08:00"
lastmod: "2023-07-29T23:29:50+08:00"
categories: ["Linux"]
slug: "linux-local-user-ldap-conflict"
draft: false
---

User already exists  error when user doesn't exist on the system » Easy as Linux

## 问题描述

创建本地 `admin` 用户时系统提示该用户已存在，但本地用户文件中找不到该用户，需要排查 NSS 目录服务是否返回了同名账户。

## 目标
查出原因，并解决问题

## 设计
无

## 核心技术
`google`，`经验`

猜测1: 用户创建时关联的group存在，不能创建。
```
[user@example-host ~]$ id admin
uid=10000(admin) gid=10000(example-group) groups=10000(example-group)
[user@example-host ~]$ grep -w admin /etc/group
# 本地 group 文件没有对应的 admin 用户组
```

发现并不存在对应用户组

猜测2: 谷歌搜到方法: easyaslinux
[easyaslinux](https://www.easyaslinux.com/quick-fix/user-already-exists-error-when-user-doesnt-exist-on-the-system/)

使用 getent 命令 搜索用户信息 \
getent is a Linux command that helps the user to get the entries in a number of important text files called databases.
```
[user@example-host ~]$ getent passwd admin
admin:*:10000:10000:Directory User:/home/admin:/bin/bash
[user@example-host ~]$ getent passwd example-user
example-user:x:1001:1001::/home/example-user:/bin/bash
```
发现admin用户输出的信息跟普通用户有区别 \
密码栏(冒号为分隔符第二个)，显示的结果是* ，一般是x，表示密码存在 /etc/shadow 文件里 \
Lets dig into Name Service Switch library config file. 查查nss的库文件 \
备注: The Name Service Switch (NSS) framework was designed to let administrators specify which files or directory services to query to obtain information. \

```
[user@example-host ~]$ grep '^passwd:' /etc/nsswitch.conf
passwd:     files sss
```

问题找到了，nss在ldap中搜到当前用户，(sss被当成一个ldap客户端配置相关信息)

```bash
systemctl status sssd
```

SSSD 正在运行，NSS 会通过目录服务查询用户。

机器使用目录服务进行统一身份管理，SSSD 作为客户端也返回了同名 `admin` 用户，导致本地创建用户发生冲突。



## 动手实践
卸载后这台机器信息就能新增用户了，此时发现用户密码配置变了
```
[user@example-host ~]$ getent passwd admin
admin:x:1002:1002:Local User:/home/admin:/bin/bash
```

此时表示用户不在是一个ldap用户了，他的密码配置文件又变成了 /etc/shadow 

权限相关的问题也解决了

## 优化

找到问题的根源，现在有三个方式解决问题
1. Remove the user from ldap server.
2. Remove the ldap reference from the /etc/nsswitch.conf file so that NSS library dont look for the user in ldap server.
3. Keep the user in the ldap as it is, but create the same user in the system! Let me explain how we do it further.

1. 删除ldap中的用户
2. 从 /etc/nsswitch.conf 文件中删除 ldap 引用，这样 NSS 库就不会在 ldap 服务器中查找用户。
3. 保持用户在 ldap 中的原样，但在系统中创建相同的用户！让我解释一下我们如何进一步做到这一点。

很明显，最好的解决方法是第三种:
使用`luseradd`命令

```
yum install libuser
luseradd admin
```

不需要停止ipa服务，不影响权限，完美解决问题