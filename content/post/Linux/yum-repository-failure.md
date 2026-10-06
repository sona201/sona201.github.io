---
title: "Yum 软件源失败时的处理"
date: "2026-04-10T20:43:02+08:00"
lastmod: "2026-04-10T20:43:02+08:00"
categories: ["Linux"]
slug: "yum-repository-failure"
draft: false
---


yum 安装的时候，发现某个repo网络异常

```
[root@example-host ~]# strace -f -e trace=network yum install mtr
-bash: strace: command not found
[root@example-host ~]# strace
-bash: strace: command not found
[root@example-host ~]# yum install strace
Loaded plugins: fastestmirror, product-id, search-disabled-repos
Determining fastest mirrors
epel/x86_64/metalink                                                                                                                                                                                                                     | 4.5 kB  00:00:00     
 * base: mirrors.aliyun.com
 * epel: d2lzkl7pfhq30w.cloudfront.net
 * extras: mirrors.aliyun.com
 * updates: mirrors.aliyun.com
base                                                                                                                                                                                                                                     | 3.6 kB  00:00:00     
docker-ce-stable                                                                                                                                                                                                                         | 3.5 kB  00:00:00     
endpoint                                                                                                                                                                                                                                 | 2.9 kB  00:00:00     
extras                                                                                                                                                                                                                                   | 2.9 kB  00:00:00     
https://rpm.releases.hashicorp.com/RHEL/7/x86_64/stable/repodata/repomd.xml: [Errno 14] HTTPS Error 404 - Not Found
Trying other mirror.
To address this issue please refer to the below wiki article 

https://wiki.centos.org/yum-errors

If above article doesn't help to resolve this issue please use https://bugs.centos.org/.



 One of the configured repositories failed (Hashicorp Stable - x86_64),
 and yum doesn't have enough cached data to continue. At this point the only
 safe thing yum can do is fail. There are a few ways to work "fix" this:

     1. Contact the upstream for the repository and get them to fix the problem.

     2. Reconfigure the baseurl/etc. for the repository, to point to a working
        upstream. This is most often useful if you are using a newer
        distribution release than is supported by the repository (and the
        packages for the previous distribution release still work).

     3. Run the command with the repository temporarily disabled
            yum --disablerepo=hashicorp ...

     4. Disable the repository permanently, so yum won't use it by default. Yum
        will then just ignore the repository until you permanently enable it
        again or use --enablerepo for temporary usage:

            yum-config-manager --disable hashicorp
        or
            subscription-manager repos --disable=hashicorp

     5. Configure the failing repository to be skipped, if it is unavailable.
        Note that yum will try to contact the repo. when it runs most commands,
        so will have to try and fail each time (and thus. yum will be be much
        slower). If it is a very temporary problem though, this is often a nice
        compromise:

            yum-config-manager --save --setopt=hashicorp.skip_if_unavailable=true

failure: repodata/repomd.xml from hashicorp: [Errno 256] No more mirrors to try.
https://rpm.releases.hashicorp.com/RHEL/7/x86_64/stable/repodata/repomd.xml: [Errno 14] HTTPS Error 404 - Not Found
```

上面显示某个repo 网络连接异常，如果网络异常，可以先指定禁用repo，前提是需要知道repo名字
不行的话，可以手动将 xxx.repo 重命名  xxx.repo_back

```bash
yum install mtr --disablerepo=hashicorp --disablerepo=epel
```