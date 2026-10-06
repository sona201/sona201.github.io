---
title: "Docker 数据目录、日志与 Registry 配置笔记"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["Kubenertes"]
slug: "docker-operations-notes"
draft: false
---

### docker 迁移


```bash
systemctl enable docker
systemctl start docker
# 增加普通用户管理docker权限
usermod -aG docker your-user
# 修改docker挂载目录
systemctl stop docker
systemctl stop docker.socket
mv /var/lib/docker /data/
ln -s /data/docker /var/lib/docker
systemctl start docker
```

### docker log

docker logs -f -t --tail 100 CONTAINER_ID

```
$ docker logs [OPTIONS] CONTAINER
  Options:
        --details        显示更多的信息
    -f, --follow         跟踪实时日志
        --since string   显示自某个timestamp之后的日志，或相对时间，如42m（即42分钟）
        --tail string    从日志末尾显示多少行日志， 默认是all
    -t, --timestamps     显示时间戳
        --until string   显示自某个timestamp之前的日志，或相对时间，如42m（即42分钟）
```

#### 查看指定时间后的日志，只显示最后100行
```
$ docker logs -f -t --since="2018-02-08" --tail=100 CONTAINER_ID
```

#### 查看最近30分钟的日志
```
$ docker logs --since 30m CONTAINER_ID
```

#### 查看某时间之后的日志
```
$ docker logs -t --since="2018-02-08T13:23:37" CONTAINER_ID
```

#### 查看某时间段日志
```
$ docker logs -t --since="2018-02-08T13:23:37" --until "2018-02-09T12:23:37" CONTAINER_ID
```

#### 允许Docker使用无权限验证的Docker Registry
配置insecure-registries，docker才能使用无权限验证的docker registry

默认情况下，Docker不能使用没有配置权限验证的Docker Registry，会出现如下报错：
```
docker pull registry.example.com:5000/ubuntu
Error response from daemon: server gave HTTP response to HTTPS client
```

这时需要修改 Docker 配置文件，将示例 Registry 地址 `registry.example.com:5000` 添加到 insecure-registries 中：
```bash
cat /etc/docker/daemon.json
{
  "insecure-registries" : ["registry.example.com:5000"]
}
```
然后重启docker
```bash
systemctl restart docker
```

#### 容器内部操作

debain 系统换清华源，执行下列命令，换源然后安装应用
```bash
echo -e "# 默认注释了源码镜像以提高 apt update 速度，如有需要可自行取消注释\ndeb https://mirrors.tuna.tsinghua.edu.cn/debian/ buster main contrib non-free\n# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ buster main contrib non-free\ndeb https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-updates main contrib non-free\n# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-updates main contrib non-free\ndeb https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-backports main contrib non-free\n# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian/ buster-backports main contrib non-free\ndeb https://mirrors.tuna.tsinghua.edu.cn/debian-security buster/updates main contrib non-free\n# deb-src https://mirrors.tuna.tsinghua.edu.cn/debian-security buster/updates main contrib non-free" >> /etc/apt/sources.list
```

#### 容器暴露端口

当容器内部没有启动一个端口，但外部暴露这个端口，现象: 宿主机会启动这个端口，端口被占用，但访问这个端口会失败，curl会提示
```
curl: (56) Recv failure: Connection reset by peer
```