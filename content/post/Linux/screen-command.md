---
title: "Screen 常用命令"
date: "2024-06-06T16:14:27+08:00"
lastmod: "2024-06-06T16:14:27+08:00"
categories: ["Linux"]
slug: "screen-command"
draft: false
---


screen 生成新的窗口
screen -ls 查看当前的screen窗口
exit 或者  ctrl d 退出
screen  将当前窗口放后台

```
# 使用yum安装screen
yum install screen
# 创建一个名为test的会话窗口
screen -S test
# 暂离窗口
Ctrl+a d(即按住Ctrl，依次再按a,d)
# 查看存在的会话窗口
screen -ls
# 进入窗口
screen -r test
screen -r 进程ID
# 关闭窗口
exit
# 窗口切换
Ctrl+a c ：在当前screen会话中创建窗口
Ctrl+a w ：窗口列表
Ctrl+a n ：下一个窗口
Ctrl+a p ：上一个窗口
Ctrl+a 0-9 ：在第0个窗口和第9个窗口之间切换
```

https://www.cnblogs.com/Steven0805/p/7521719.html

https://handerfly.github.io/linux/2019/03/31/Screan%E5%91%BD%E4%BB%A4%E7%9A%84%E4%BD%BF%E7%94%A8/

https://blog.csdn.net/weixin_43332715/article/details/122022030

	https://cloud.tencent.com/developer/article/1722221