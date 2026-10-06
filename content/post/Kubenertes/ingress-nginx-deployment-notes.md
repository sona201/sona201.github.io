---
title: "Ingress NGINX 部署与 RBAC 学习笔记"
date: "2023-11-17T18:34:52+08:00"
lastmod: "2023-11-17T18:34:52+08:00"
categories: ["Kubenertes"]
slug: "ingress-nginx-deployment-notes"
draft: false
---

## kubernetes deploy ingress-controller

会启动job，是一次性任务。主要是创建证书使用

docker 镜像使用 orbstack 当成 docker 容器会开启 docker 最新实验特性，根据芯片下载对应的版本，这也算一个坑

yaml 文件提供的镜像地址都是国外的，需要转换为国内的， 刚好也自建 nexus docker 仓库，需要配置服务器配置 docker 信任源
```
{
    "storage-driver": "overlay2",
    "insecure-registries" : ["registry.example.com:5000"]
}
```

当前对应的k8s版本是 1.23，(官网提示)能安装的 ingress 版本
v1.3.0、v1.3.1、v1.4.0、v1.5.1、v1.6.4

之前找到一个 ingress 安装入门文档，结果文档太老，使用的是 v0.15.0镜像，对应的部署控制器还是 rc ，这个控制器在 0.47这个版本里已经被删除了。
[相关文档链接](https://developer.aliyun.com/article/642705) ，吐槽一句，国内文档还是有点跨，不够新。

https://blog.csdn.net/zhou920786312/article/details/126246557  比较老

https://ytool.cloud/k8s/net/ingress/install.html ，这个文档比较新，但我没有采用，因为不是很想用helm 无脑安装，不清楚做了啥


https://www.cnblogs.com/wtzbk/p/15427237.html 这个版本比较新，但我没用
https://cloud.tencent.com/developer/article/1579931 这个讲的也行，只有回过头才知道哪些是对的


```
registry.k8s.io/ingress-nginx/controller:v1.9.4@sha256:5b161f051d017e55d358435f295f5e9a297e66158f136321d9b04520ec6c48a3
```
后面的@sha 表示文件的校验码，类似 md5，我直接下载这个链接的时候，发现下载的镜像没有对应的版本，后来还是指定版本了


安装 ingress 的 yaml 文件里有job，这个是一次性的任务，如果执行报错了，再次执行
```
kubectl apply -f ingress-nginx.yaml
```

会提示报错，需要执行删除 job 命令
```bash
kubectl delete job --all -n ingress-nginx --context=huawei
```

查看容器是否启动，直接看应用是否 ready
```bash
kubectl get po -n ingress-nginx --context=huawei -w
```
-w 表示--watch，就是监视，在 watch 的时候出现一次弹出多条重复的信息，表示有多个变动，只是展示信息不够详细
只能看到多条重复信息，不是实现故障，信息重复

容器未启动需要查看事件 events
```bash
kubectl describe po xxx
```

查看事件只提示拉镜像成功，没有更多的有用信息，就需要在看看容器日志
```bash
kubectl logs xxx
```

ingress-nginx.yaml 文件解释


创建两个账户 ServiceAccount
- ingress-nginx
- ingress-nginx-admission
区别在于
ingress-nginx 设置了
automountServiceAccountToken: true
属于 namespace 下自动调用的 token，不需要在调用时指定 ServiceAccountName
```
使用默认的 Service Account 访问 API server
当您创建 pod 的时候，如果您没有指定一个 service account，系统会自动得在与该pod 相同的 namespace 下为其指派一个default service account。如果您获取刚创建的 pod 的原始 json 或 yaml 信息（例如使用kubectl get pods/podename -o yaml命令），您将看到spec.serviceAccountName字段已经被设置为 default。
```
然后就是对应的 Role ClusterRole
RoleBinding ClusterRoleBinding

ServiceAccount(ingress-nginx) --RoleBinding-->  Role(ingress-nginx)
ServiceAccount(ingress-nginx) --ClusterRoleBinding-->  ClusterRole(ingress-nginx)


ServiceAccount(ingress-nginx-admission) --RoleBinding-->  Role(ingress-nginx-admission)
ServiceAccount(ingress-nginx-admission) --ClusterRoleBinding-->  ClusterRole(ingress-nginx-admission)

标准的 rbac 那一套，指定当前账户有哪个角色，角色对应的有哪些资源(pod/configmap/service...)的哪些权限(get/list/update/watch...)

在 deployment 中用到了 serviceAccountName: ingress-nginx
在  2 个 job 中用到了 serviceAccountName: ingress-nginx-admission

下面是一个摘要
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:...
  name: ingress-nginx-controller
  namespace: ingress-nginx
spec:
  minReadySeconds: 0
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      app.kubernetes.io/component: controller
      app.kubernetes.io/instance: ingress-nginx
      app.kubernetes.io/name: ingress-nginx
  strategy:...
  template:
    metadata:
      labels:...
    spec:
      containers:
      - args:...
      dnsPolicy: ClusterFirst
      nodeSelector:...
      serviceAccountName: ingress-nginx
      terminationGracePeriodSeconds: 300
      volumes:...
```

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  labels:
    app.kubernetes.io/component: admission-webhook
    app.kubernetes.io/instance: ingress-nginx
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
    app.kubernetes.io/version: 1.5.1
  name: ingress-nginx-admission-create
  namespace: ingress-nginx
spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/component: admission-webhook
        app.kubernetes.io/instance: ingress-nginx
        app.kubernetes.io/name: ingress-nginx
        app.kubernetes.io/part-of: ingress-nginx
        app.kubernetes.io/version: 1.5.1
      name: ingress-nginx-admission-create
    spec:
      containers:
      - args:
        - create
        - --host=ingress-nginx-controller-admission,ingress-nginx-controller-admission.$(POD_NAMESPACE).svc
        - --namespace=$(POD_NAMESPACE)
        - --secret-name=ingress-nginx-admission
        env:
        - name: POD_NAMESPACE
          valueFrom:...
        image: registry.k8s.io/ingress-nginx/kube-webhook-certgen:v20220916-gd32f8c343@sha256:39c5b2e3310dc4264d638ad28d9d1d96c4cbb2b2dcfb52368fe4e3c63f61e10f
        imagePullPolicy: IfNotPresent
        name: create
        securityContext:...
      nodeSelector:...
      restartPolicy: OnFailure
      securityContext:...
      serviceAccountName: ingress-nginx-admission
```

ValidatingWebhookConfiguration 描述准入Webhook 的配置，该Webhook 可在不更改对象的情况下接受或拒绝对象请求。

准入 Webhook 是一种用于接收准入请求并对其进行处理的 HTTP 回调机制。 可以定义两种类型的准入 Webhook， 即验证性质的准入 Webhook 和变更性质的准入 Webhook。 变更性质的准入 Webhook 会先被调用。它们可以修改发送到 API 服务器的对象以执行自定义的设置默认值操作。
