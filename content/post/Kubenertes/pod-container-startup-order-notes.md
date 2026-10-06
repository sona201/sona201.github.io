---
title: "Pod 多容器启动顺序与 Init Container 笔记"
date: "2024-03-13T16:55:49+08:00"
lastmod: "2024-03-13T16:55:49+08:00"
categories: ["Kubenertes"]
slug: "pod-container-startup-order-notes"
draft: false
---

## pod内多个容器启动问题

### 问题描述

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mc3
  labels:
    app: mc3
spec:
  containers:
  - name: webapp
    image: training/webapp
  - name: nginx
    image: nginx:alpine
    ports:
    - containerPort: 80
    volumeMounts:
    - name: nginx-proxy-config
      mountPath: /etc/nginx/nginx.conf
      subPath: nginx.conf
  volumes:
  - name: nginx-proxy-config
    configMap:
      name: mc3-nginx-conf
```

如上的pod容器启动，在一个pod内有多个容器的启动顺序问题，这种算不算 sidecar 模式

找到一个解释

In what order containers are being started in a Pod?

Currently, all containers in a Pod are being started in parallel and there is no way to define that one container must be started after other container (however, there are Kubernetes Init Containers). Therefore, in your IPC example there is a chance that the second container starts before the first one. In this case, the second container will fail, because in the consumer mode it expects that the message queue exists. To fix this issue we, for example, can change the application to wait for the message queue to be created.

翻译(微软翻译)：目前，Pod 中的所有容器都是并行启动的，并且无法定义一个容器必须在另一个容器之后启动（但是，有 Kubernetes 初始化容器）。因此，在 IPC 示例中，第二个容器有可能在第一个容器之前启动。在这种情况下，第二个容器将失败，因为在 consumer 该模式下，它期望消息队列存在。例如，为了解决此问题，我们可以更改应用程序以等待创建消息队列。

[原文链接](https://linchpiner.github.io/k8s-multi-container-pods.html)

### 解决方案1
具体的版本不清楚了，但这种方式用的人不多。或者用的是initContainers

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
  labels:
    app.kubernetes.io/name: MyApp
spec:
  containers:
  - name: myapp-container
    image: busybox:1.28
    command: ['sh', '-c', 'echo The app is running! && sleep 3600']
  initContainers:
  - name: init-myservice
    image: busybox:1.28
    command: ['sh', '-c', "until nslookup myservice.$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace).svc.cluster.local; do echo waiting for myservice; sleep 2; done"]
  - name: init-mydb
    image: busybox:1.28
    command: ['sh', '-c', "until nslookup mydb.$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace).svc.cluster.local; do echo waiting for mydb; sleep 2; done"]
```

[案例来自官网](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/)

