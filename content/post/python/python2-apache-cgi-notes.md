---
title: "Python 2 与 Apache CGI 实验"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["python"]
slug: "python2-apache-cgi-notes"
draft: false
---

### web选型



web服务器首选nginx，但nginx不支持cgi，因为太古老了

所以选用apache

- 主要为理解cgi的模式流程
- 理解header的作用



#### apache的安装

原本想使用ubunt系统，但对配置文件路径不熟悉，作罢

1. Yum 安装

   ```yum install -y httpd```

2. 配置

   apache的配置文件为`/etc/httpd/conf/httpd.conf`

   

   文件需要修改根目录

   ```
   将目录替换
   <Directory />
     AllowOverride none
     Require all denied
   </Directory>
   为：
   <Directory "/var/www/cgi-bin">
     AllowOverride None
     Options +ExecCGI
     Order allow,deny
     Allow from all
   </Directory>
   ```

   

   修改 <IfModule mime_module> 增加 AddHandler

   去掉注释

   ```
   将注释去掉，并增加.py 后缀
   AddHandler cgi-script .cgi .py
   ```

3. 重启apache

- systemctl start httpd.service #启动

- systemctl stop httpd.service #停止

- systemctl restart httpd.service #重启

4. 检查httpd状态

```
[root@gitlab-test ~]# systemctl status httpd.service
● httpd.service - The Apache HTTP Server
   Loaded: loaded (/usr/lib/systemd/system/httpd.service; disabled; vendor preset: disabled)
   Active: active (running) since Wed 2020-02-12 12:07:30 CST; 12s ago
     Docs: man:httpd(8)
           man:apachectl(8)
 Main PID: 58363 (httpd)
   Status: "Total requests: 0; Current requests/sec: 0; Current traffic:   0 B/sec"
    Tasks: 7
   Memory: 3.2M
   CGroup: /system.slice/httpd.service
           ├─58363 /usr/sbin/httpd -DFOREGROUND
           ├─58365 /usr/sbin/httpd -DFOREGROUND
           ├─58366 /usr/sbin/httpd -DFOREGROUND
           ├─58367 /usr/sbin/httpd -DFOREGROUND
           ├─58368 /usr/sbin/httpd -DFOREGROUND
           ├─58369 /usr/sbin/httpd -DFOREGROUND
           └─58370 /usr/sbin/httpd -DFOREGROUND

Feb 12 12:07:30 gitlab-test systemd[1]: Starting The Apache HTTP Server...
Feb 12 12:07:30 example-host httpd[58363]: AH00558: Set the 'ServerName' directive to suppress this message
Feb 12 12:07:30 gitlab-test systemd[1]: Started The Apache HTTP Server.
Hint: Some lines were ellipsized, use -l to show in full.
```

5. python代码

```python
#!/usr/bin/python
#coding=utf-8

print "Content-type:text/html"
print                           #空行，告诉服务器结束头部
print '<html>'
print '<head>'
print '<meta charset="utf-8">'
print '<title>Hello Word - 我的第一个CGI程序！</title>'
print '</head>'
print '<body>'
print '<h2>嘿！ this is cgi!~</h2>'
print '</body>'
print '</html>'
```



增加权限

```bash
chmod 755 /var/www/cgi-bin/hello.py 
```



6. 测试结果

在当前服务器上使用命令

curl localhost/cgi-bin/hello.py

结果成功





