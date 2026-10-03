---
title: "Wsgiref"
description: "合并个人笔记仓库中的 Django WSGI / wsgiref 记录"
date: "2023-05-05"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["django"]
tags: ["django", "wsgi", "wsgiref"]
draft: false
---

django 使用的最小web服务模块
使用的大致逻辑处理
```bash
# from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler


def routers():
    # URLConf 配置
    urlpatterns = (
        ('/book', foo),
        ('/web', bar),
    )
    return urlpatterns


def foo(x):
    return [b'<h1>Hello, book</h1>']


def bar(x):
    return [b'<h1>Hello, web</h1>']


def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])

    urlpatterns = routers()
    path = environ['PATH_INFO']  # http://127.0.0.1:8000/book
    func = None
    for item in urlpatterns:
        if item[0] == path:
            func = item[1]
            break
    if func:
        return func(environ)
    else:
        return ['<h1>404</h1>'.encode('utf-8')]


# httpd = make_server('127.0.0.1', 8000, application)
# def make_server(
#     host, port, app, server_class=WSGIServer, handler_class=WSGIRequestHandler
# )
httpd = WSGIServer(('127.0.0.1', 8000), WSGIRequestHandler)
httpd.set_app(application)

print('Serving HTTP on port 8000...')
httpd.serve_forever()
```
application 其实是 mvc架构的 control 层，负责路由的处理跟转发
然后对应的函数 foo/bar 进行处理

httpd.server_forever()  可以理解为while循环，等待请求

application 负责处理，将请求(参数、环境变量)转给对应的 func处理

这里的env

### django封装

django 中的run 方法其实就是wsgiref的make_server的升级版
```python
def run(addr, port, wsgi_handler, ipv6=False, threading=False, server_cls=WSGIServer):
    server_address = (addr, port)
    if threading:
        httpd_cls = type("WSGIServer", (socketserver.ThreadingMixIn, server_cls), {})
    else:
        httpd_cls = server_cls
    httpd = httpd_cls(server_address, WSGIRequestHandler, ipv6=ipv6)
    if threading:
        # ThreadingMixIn.daemon_threads indicates how threads will behave on an
        # abrupt shutdown; like quitting the server by the user or restarting
        # by the auto-reloader. True means the server will not wait for thread
        # termination before it quits. This will make auto-reloader faster
        # and will prevent the need to kill the server manually if a thread
        # isn't terminating correctly.
        httpd.daemon_threads = True
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()
```

抽象下
```python
# def run(addr, port, wsgi_handler, ipv6=False, threading=False, server_cls=WSGIServer):
# server_address = (addr, port)
httpd = WSGIServer((addr, port), WSGIRequestHandler, ipv6=ipv6)
# django的 WSGIServer 不是wsgiref的 WSGIServer, 但基本一样，加了ipv6的配置，加了错误处理逻辑
httpd.set_app(wsgi_handler)
httpd.serve_forever()
```

django封装的WSGIServer方法
```python
class WSGIServer(simple_server.WSGIServer):
    """BaseHTTPServer that implements the Python WSGI protocol"""

    request_queue_size = 10

    def __init__(self, *args, ipv6=False, allow_reuse_address=True, **kwargs):
        if ipv6:
            self.address_family = socket.AF_INET6
        self.allow_reuse_address = allow_reuse_address
        super().__init__(*args, **kwargs)

    def handle_error(self, request, client_address):
        if is_broken_pipe_error():
            logger.info("- Broken pipe from %s\n", client_address)
        else:
            super().handle_error(request, client_address)
```


`django` 中 `wsgi_handler` 等同于 `wsgiref` 中 `application`
区别在于 `wsgi_handler` 是一个对象，而 `application` 是个函数，可以直接调用

`wsgi_handler`的延伸
`wsgi_handler`跟`django`项目的配置`settings`一起, 有一个`wsgi.py`文件，内容如下
```python
def get_wsgi_application():
    """
    The public interface to Django's WSGI support. Return a WSGI callable.

    Avoids making django.core.handlers.WSGIHandler a public API, in case the
    internal WSGI implementation changes or moves in the future.
    """
    django.setup(set_prefix=False)
    return WSGIHandler()
```
这里的 `WSGIHandler()` 就是一个核心类，用来处理"每个进来的请求"


django请求

https://0x90e.github.io/django-launch-and-request-flow/
https://www.brennantymrak.com/articles/comprehending-class-based-views-view-base-class
https://stackoverflow.com/questions/28770701/django-class-based-views-understanding-the-arguments-in-the-view-class


