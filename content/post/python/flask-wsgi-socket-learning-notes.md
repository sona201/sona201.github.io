---
title: "从 Flask WSGI 到 socket 的学习记录"
date: "2021-01-10T00:51:58+08:00"
lastmod: "2021-01-10T00:51:58+08:00"
categories: ["python"]
slug: "flask-wsgi-socket-learning-notes"
draft: false
---



想搞清楚flask源码

需要搞清楚 flask 逻辑

需要wsgi_app 怎么实现

```python
        from werkzeug.serving import run_simple

        try:
            run_simple(host, port, self, **options)
```

`self`表示Flask 实例化`app = Flask(__name__)`



https://segmentfault.com/a/1190000010756866



这个流程可以参考



还有一个问题，`wsgi_app(environ, start_response)`里的`start_response`为什么是个方法

里面直接返回

```python
from eventlet import wsgi
import eventlet


def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])
    body = '<h1>Hello, %s!</h1>' % (environ['PATH_INFO'][1:] or 'web')
    return [body.encode('utf-8')]


wsgi.server(eventlet.listen(('', 8080)), application)

```



`start_response('200 OK', [('Content-Type', 'text/html')])`怎么理解

http://liaoph.com/python-wsgi/



socket编程方式



```python
import socket

# 创建一个socket:
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 建立连接:
s.connect(('www.sina.com.cn', 80))

# 发送数据:
s.send(b'GET / HTTP/1.1\r\nHost: www.sina.com.cn\r\nConnection: close\r\n\r\n')

# 接收数据:
buffer = []
while True:
    # 每次最多接收1k字节:
    d = s.recv(1024)
    if d:
        buffer.append(d)
    else:
        break

data = b''.join(buffer)

# 关闭连接:
s.close()

header, html = data.split(b'\r\n\r\n', 1)
print(header.decode('utf-8'))

# 把接收的数据写入文件:
with open('sina.html', 'wb') as f:
    f.write(html)

```



创建一个`socket`，建立连接，获取html，写入本地文件





先根据  `start_response('200 OK', [('Content-Type', 'text/html')])` http://liaoph.com/python-wsgi/

理清思路，WSGI Server 实现纯手动写server

wsgi协议

 再根据`https://segmentfault.com/a/1190000010756866` 将流程梳理



