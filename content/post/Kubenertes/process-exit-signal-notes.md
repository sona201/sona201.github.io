---
title: "进程退出码 130、137、143 与信号"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["Kubenertes"]
slug: "process-exit-signal-notes"
draft: false
---

k8s kill restart exit status  137

128+信号值


exit 130
命令行输入
sleep 100000
然后执行 <Ctrl-C>
查看命令状态   echo $?
结果输出: 130(128+2)


---
exit 137
终端1:命令行输入: sleep 100000
终端2:kill sleep
终端1:查看命令状态   echo $?
结果输出: 137(128+9)

143
ps aux | grep sleep | grep -v grep | awk '{print $2}'
kill -term <ProcessID>
kill -15 <ProcessID>


