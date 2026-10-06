---
title: "Django setup 与 shell 初始化笔记"
date: "2023-02-07T00:01:23+08:00"
lastmod: "2023-02-07T00:01:23+08:00"
categories: ["django"]
slug: "django-setup-shell-notes"
draft: false
---

### Django4.0源码分析-1.8 关于shell命令的答疑

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firstDjango.settings')
os.environ.get('DJANGO_SETTINGS_MODULE')  # 这个似乎不能修改系统的环境变量，只改变python环境的变量
from django.apps import apps
from django.urls import set_script_prefix
from django.utils.log import configure_logging

configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
if set_prefix:
    set_script_prefix(
        "/" if settings.FORCE_SCRIPT_NAME is None else settings.FORCE_SCRIPT_NAME
    )
apps.populate(settings.INSTALLED_APPS)


```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firstDjango.settings')
from django.apps import apps
from django.conf import settings
apps.populate(settings.INSTALLED_APPS)
apps.apps_ready
```
这样也能执行数据库操作`from web.models import Room`

大致讲了django的setup做了啥