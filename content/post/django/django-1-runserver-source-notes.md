---
title: "Django 1.0 runserver 启动流程"
date: "2023-02-27T00:26:22+08:00"
lastmod: "2023-02-27T00:26:22+08:00"
categories: ["django"]
slug: "django-1-runserver-source-notes"
draft: false
---

Django源码: 从入口到请求响应


execute_from_command_line(sys.argv)


django python manage.py runserver 流程
python manage.py runserver 流程分析
版本
python27
django 1.0
搭建可运行的环境
创建python27 虚拟环境
github 下载 django-1.0.tar.gz（1.0 版本的django）
解压
可以看到，有个 demo 在 examples 目录
把 django 目录拷贝到 examples 下面，这样 example 可以正确导入 django1.0
启动项目


```bash
python manage.py runserver
```
项目启动成功，可以修改代码来跟踪执行流程

流程
以下代码存在删减，主要展示代码流程

从 manage.py 开始，执行了 execute_manager 方法，传入 settings 模块

```python
execute_manager(settings)
django.core.management.execute_manager 方法

def execute_manager(settings_mod, argv=None):
    # setup_environ 函数，只是设置了环境变量，执行配置模块
    # os.environ['DJANGO_SETTINGS_MODULE'] = examples.settting
    setup_environ(settings_mod)

    # admin manage 工具类
    utility = ManagementUtility(argv)
    utility.execute()
```

ManagementUtility 类

```python
class ManagementUtility(object):
    def __init__(self, argv=None):
        # 初始化，例如
        self.argv = ['.../examples/manage.py', 'runserver']
        self.prog_name = 'manage.py'
    def execute(self):
        # 删除了部分代码，最终执行代码大致如下
    
        # 这是一个命令行工具类，表名能接受什么样的参数，这里主要检查两个参数
        # --settings 指定配置文件
        # --pythonpath 执行 python 环境变量
        parser = LaxOptionParser(usage="%prog subcommand [options] [args]",
                                 version=get_version(),
                                 option_list=BaseCommand.option_list)
    
        # 使用命令行工具类解析命令行参数，也就是获取 --settings 和 --pythonpath 的参数值
        options, args = parser.parse_args(self.argv)
        # 如果 --settings 参数存在，会覆盖之前设置的 os.environ['DJANGO_SETTINGS_MODULE']
        # 如果 --pythonpath 参数存在，会把指定路径添加到 sys.path 的第一位，优先从此处加载模块
        handle_default_options(options)
    
        # fetch_command
        # fetch_command 分析在下边
        # fetch_command 返回 django.core.management.commands.runserver.Command
        # run_from_argv
        # run_from_argv 分析在下边
        self.fetch_command(subcommand).run_from_argv(self.argv)
    
    def fetch_command(self, subcommand):
        # get_commands
        # get_commands 返回 django.core.management.commands 目录下的所有模块，每个模块处理对应的参数
        # 每个模块的值都是 django.core，app_name = 'django.core'
        app_name = get_commands()[subcommand]
    
        # load_command_class 方法
        # 返回了 django.core.management.commands.runserver.Command
        klass = load_command_class(app_name, subcommand)
    
        return klass
```

run_from_argv 方法
```python
# django.core.management.commands.runserver.Command 
# 继承 django.core.management.base import BaseCommand
# run_from_argv 也是继承的
def run_from_argv(self, argv):
    # 调用 execute
    self.execute(*args, **options.__dict__)

def execute(self, *args, **options):
    # 调用 handle
    # 注意 handle 被重写了
    # 调用的是 django.core.management.commands.runserver.Command.handle
    output = self.handle(*args, **options)
handle

def handle(self, addrport='', *args, **options):
    def inner_run():
        # WSGI 处理程序
        # WSGIHandler 可调用，是 WSGI 处理程序
        # AdminMediaHandler 是对 WSGIHandler 的封装
        # AdminMediaHandler 特殊处理媒体文件请求
        # AdminMediaHandler 非媒体文件的 HTTP 请求，直接返回 WSGIHandler
        handler = AdminMediaHandler(WSGIHandler(), path)
        
        # 
        run(addr, int(port), handler)
        # run 在 django.core.servers.basehttp.run
        # run 定义如下
        # run 启动了 HTTP 服务，这个服务器只能用于开发调试
        def run(addr, port, wsgi_handler):
            # 绑定地址端口
            server_address = (addr, port)
            # 服务实例
            httpd = WSGIServer(server_address, WSGIRequestHandler)
            # 传入 WSGI 处理程序
            httpd.set_app(wsgi_handler)
            # 监听请求
            httpd.serve_forever()
    
    inner_run()
```