---
title: "PyCharm requirements 检查设置"
date: "2023-11-12T17:18:11+08:00"
lastmod: "2023-11-12T17:18:11+08:00"
categories: ["tools"]
slug: "pycharm-package-requirements-inspection"
draft: false
---

## python requirements 忽略报错

在安装 python requirements 时，总是会遇到依赖版本不匹配，忽略后又找不到开关。在此把相关截图备注下。

![requeirements1](/images/requirements1.png)

pycharm 提示requirements 文件里有相关依赖包没安装或者版本不匹配。如果不小心点了忽略，后续就找不到在哪里打开。

![requeirements2](/images/requirements2.png)

> 目录在 pycharm 里的 editor -> inspections -> package requeirements

- 如果将整个菜单都不够选，就会忽略整个 requeirements.txt 文件
- 但只想忽略某几个包，可以在右下侧把对应的报名加进去。如下图

![requeirements3](/images/requirements3.png)

