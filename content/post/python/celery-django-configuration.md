---
title: "Celery 与 Django 配置笔记"
date: "2026-01-14T20:41:39+08:00"
lastmod: "2026-01-14T20:41:39+08:00"
categories: ["python"]
slug: "celery-django-configuration"
draft: false
---

#python #celery

# celery 简介
celery 是一个分布式任务队列
```
Celery is a simple, flexible, and reliable distributed system to process vast amounts of messages, while providing operations with the tools required to maintain such a system.

It’s a task queue with focus on real-time processing, while also supporting task scheduling.

Celery has a large and diverse community of users and contributors, don’t hesitate to ask questions or [get involved](https://docs.celeryq.dev/en/stable/getting-started/resources.html#getting-help).

Celery is Open Source and licensed under the [BSD License](http://www.opensource.org/licenses/BSD-3-Clause).
```

## 当前使用 celery 版本
5.2.7

### 安装
```
celery==5.2.7
django_celery_results==2.6.0
django-celery-beat==2.8.1
```

### 注册应用
```
INSTALLED_APPS = [  
    ...
    'django_celery_beat',  
    'django_celery_results'
]
```


### 执行数据库迁移
```
python manage.py migrate django_celery_beat django_celery_results 
```

celery 配置
```python
# Celery 配置  
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'  
# RabbitMQ 特有优化  
CELERY_TASK_ACKS_LATE = True  # 任务执行完后再确认，防止 worker 崩溃导致任务丢失  
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # 每次只预取一个任务，防止长耗时任务导致负载不均  
CELERY_ACCEPT_CONTENT = ['json']  
CELERY_TASK_SERIALIZER = 'json'  
CELERY_RESULT_SERIALIZER = 'json'  
CELERY_TIMEZONE = 'Asia/Shanghai'  
CELERY_RESULT_EXPIRES = 86400 * 7
```

celery 相关命令
```
celery -A conf.celery_app worker --loglevel=info  # 启动worker，执行节点
celery -A conf.celery_app beat --loglevel=info  # 启动schedule，定时任务
celery -A conf.celery_app inspect conf | grep -i celery  # 查看相关启动参数，需要在celery启动的时候才能查看
celery -A conf.celery_app inspect registered  # 查看 celery 注册的任务
```
