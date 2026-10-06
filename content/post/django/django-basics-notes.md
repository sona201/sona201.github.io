---
title: "Django 基础操作与请求响应对象笔记"
date: "2020-11-28T17:16:52+08:00"
lastmod: "2020-11-28T17:16:52+08:00"
categories: ["django"]
slug: "django-basics-notes"
draft: false
---

## Django基础

### 一、Django 基础操作

#### 创建Django项目

```bash
# 命令行方式创建项目
django-admin startproject devops
```

#### Django项目目录结构介绍

```
 |-- manage.py
  `-- devops
      |-- __init__.py 
      |-- settings.py
      |-- urls.py
      `-- wsgi.py
```

- 最外层的devops/目录只是你项目的一个容器
- `manage.py` 一个实用的命令行工具，可让你以各种方式与该 `Django` 项目进行交互
- 内层 `devops/` 目录是你项目中的实际Python包。通过它你可以导入它里面的任何东西
- `devops/__init__.py`: 一个空文件，告诉`Python`该目录是一个`Python`包
- `devops/settings.py`: 该`Django`项目的配置文件
- `devops/urls.py`: 该`Django`项目的 `URL` 声明
- `devops/wsgi.py`: 一个`WSGI`兼容的`Web`服务器的入口


#### 启动(运行)项目

- 起动服务

```bash
cd devops
python manage.py runserver
```

可以直接通过`python3 manage.py`查看命令

- 指定端口起动服务

```bash
python manage.py runserver 8000
```

- 指定ip与端口起动服务

```bash
python manage.py runserver 0.0.0.0:8000
```

#### 新建Django app

1. 新建一个名为dashboard的app

```bash
python manage.py startapp dashboard
```

2. 配置url

```python
from django.conf.urls import include, url
urlpatterns = [
    ... 
    url(r'^dashboard/', include("dashboard.urls")),
]
```

3. 激活app

```python
INSTALLED_APPS = (
    ...
    'dashboard',
)
```

####  Hello world

##### step 1: 编写视图

```python
from django.http import HttpResponse
def index(request):
    return HttpResponse("Hello world !!!")
```

##### step 2: 配置url

```python
from django.conf.urls import include, url
from . import views
urlpatterns = [
    url(r'^$', views.index, name='index'),
]
```

#### Django 之模板

> 加载模版

`django.template.loader` 这个模块提供了两种方法加载模板

```python
get_template(template_name, using=None)
```

加载指定模板并返回Template对象

```python
select_template(template_name_list, using=None)
```

它与get_template类似，它尝试每个名称并返回第一个存在的模板

> 从文件加载内容

```python
from django.template import Context, loader
def index(request):
    t = loader.get_template("test.html")
    context = {"name": "hello reboot !!!"}
    return HttpResponse(t.render(context, request))
```

> 快捷方式：render()

```python
from django.shortcuts import render
def index(request):
    context = {'name': "reboot"}
    return render(request, 'test.html', context)
```

### 二、`Django` 配置

#### 配置静态文件

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)
```

#### 配置时区

```python
TIME_ZONE = ’Asia/Shanghai’
```

#### 配置数据库

`opsweb/settings.py`是一个普通的`python`模块，每项配置都是一对`key/value`

数据库的配置是以dict的形式存放在这个模块中，key名为：DATABASES

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'django',
        'USER': 'root',
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', ''),
        'HOST': '127.0.0.1',
        'PORT': 3306,
    }
}
```

#### 日志配置

待续...

### 三、Django Http相关 对象

Django的对象流程，先获取url，创建wsgi对象，request

#### a. HttpRequest对象

由django创建

> 属性：

```python
HttpRequest.scheme
HttpRequest.body
HttpRequest.path
HttpRequest.method
HttpRequest.encoding
HttpRequest.GET
HttpRequest.POST
HttpRequest.META
```

> 方法：

```python
HttpRequest.get_host()
HttpRequest.get_port()
HttpRequest.get_full_path()
HttpRequest.is_secure()
HttpRequest.is_ajax()
```

#### b. HttpResponse对象

> 传递一个字符串作为页面的内容到 HttpResponse 构造函数

```python
>>> from django.http import HttpResponse
>>> response = HttpResponse("Here's the text of the Web page.")
>>> response = HttpResponse("Text only, please.", content_type="text/plain")
```

> 属性：

```python
HttpResponse.content
HttpResponse.charset
HttpResponse.status_code
HttpResponse.reason_phrase
```

> 方法：

```python
HttpResponse.__init__(content=”, content_type=None, status=200, reason=None, charset=None)
```

#### c. JsonResponse 对象

```python
JsonResponse(data, encoder=DjangoJSONEncoder, safe=True, json_dumps_params=None, **kwargs)
```

示例：

```python
>>> from django.http import JsonResponse
>>> response = JsonResponse({'foo': 'bar'})
>>> response.content
b'{"foo": "bar"}'
>>> response = JsonResponse([1, 2, 3], safe=False)
```

> GET与POST请求

- GET请求与传参
- POST请求与数据提交

#### QueryDIct对象

- 在HttpRequest 对象中，GET 和POST 属性是django.http.QueryDict 的实例，它是一个自定义的类似字典的类，用来处理同一个键带有多个值。这个类的需求来自某些HTML 表单元素传递多个值给同一个键
- request.POST 和request.GET 的QueryDict 在一个正常的请求/响应循环中是不可变的。若要获得可变的版本，需要使用.copy()。

实例化QueryDict

```python
QueryDict.__init__(query_string=None, mutable=False, encoding=None)
```

示例

```python
>>> QueryDict('a=1&a=2&c=3')
<QueryDict: {'a': ['1', '2'], 'c': ['3']}>
```

> 通过fromkeys实例化QueryDict

```python
classmethod QueryDict.fromkeys(iterable, value=”, mutable=False, encoding=None)
```

示例

```python
>>> QueryDict.fromkeys(['a', 'a', 'b'], value='val')
<QueryDict: {'a': ['val', 'val'], 'b': ['val']}>
```

> QueryDict方法：

```python
QueryDict.get(key, default=None)
QueryDict.setdefault(key, default=None)[source]
QueryDict.update(other_dict)
QueryDict.items()
QueryDict.values()
QueryDict.copy()
QueryDict.getlist(key, default=None)
QueryDict.setlist(key, list_)[source]
QueryDict.appendlist(key, item)
QueryDict.setlistdefault(key, default_list=None)
QueryDict.lists()
QueryDict.pop(key)
QueryDict.popitem()
QueryDict.dict()
QueryDict.urlencode(safe=None)
```

### 四、`Django`用户配置使用

1. 配置`django`数据库
2. 同步数据
3. `Django API` 创建用户
4. 执行用户登录
5. 深入解析用户登录过程

#### 同步数据

使用django的命令行工具同步数据库

```bash
python manage.py migrate
```

#### 创建用户

使用django shell 创建普通用户：创建users最直接的方法是使用create_user()辅助函数

```python
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_user('demo_user', 'demo@example.com', '<set-your-own-password>')
```

#### 创建管理员

```bash
python manage.py createsuperuser --username=user1 --email=user@example.com
```

#### 修改密码

Django不会在user模型上存储原始的（明文）密码，而只是一个哈希。因为这个原因，不要尝试直接操作user的password属性。这也是为什么创建一个user时要使用辅助函数。

```python
>>> from django.contrib.auth.models import User
>>> u = User.objects.get(username='user1')
>>> u.set_password('<set-your-own-password>')
>>> u.save()
```

#### 用户登陆

- 执行用户登陆
- 用户登陆过程详解