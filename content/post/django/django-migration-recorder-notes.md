---
title: "Django MigrationRecorder 源码与交互实验"
date: "2023-02-08T01:06:45+08:00"
lastmod: "2023-02-08T01:06:45+08:00"
categories: ["django"]
slug: "django-migration-recorder-notes"
draft: false
---

### Django4.0源码分析-1.9 关于MigrationRecorder类的解读

在了解 `makemigrations` `migrate` 这两个命令前需要看下db目录下的文件

先了解`MigrationRecorder`这个类

关键方法
```python
class MigrationRecorder:
    """
    Deal with storing migration records in the database.

    Because this table is actually itself used for dealing with model
    creation, it's the one thing we can't do normally via migrations.
    We manually handle table creation/schema updating (using schema backend)
    and then have a floating model to do queries with.

    If a migration is unapplied its row is removed from the table. Having
    a row in the table always means a migration is applied.
    """

    _migration_class = None

    @classproperty
    def Migration(cls):
        """
        Lazy load to avoid AppRegistryNotReady if installed apps import
        MigrationRecorder.
        """
        if cls._migration_class is None:

            class Migration(models.Model):                   # 定义迁移模型类
                app = models.CharField(max_length=255)       # 应用名称
                name = models.CharField(max_length=255)      # 迁移文件名
                applied = models.DateTimeField(default=now)  # 操作时间

                class Meta:
                    apps = Apps()                   # App对象
                    app_label = "migrations"        # 应用标签
                    db_table = "django_migrations"  # 表名

                def __str__(self):
                    return "Migration %s for %s" % (self.name, self.app)

            cls._migration_class = Migration
        return cls._migration_class  # 返回迁移类

    def __init__(self, connection):
        self.connection = connection
```

只有在调用的时候才会触发赋值，`_migration_class`，否则值为`None`

跟着执行操作
```python
(venv) clin:firstDjango/ $ python3 manage.py shell
Python 3.10.5 (main, Jul 22 2022, 15:13:07) [Clang 12.0.5 (clang-1205.0.22.11)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> from django.db import connection
>>> from django.db.migrations.recorder import MigrationRecorder
>>> recorder = MigrationRecorder(connection)
>>> recorder._migration_class
>>> recorder.Migration()
<Migration: Migration  for >
>>> recorder._migration_class
<class 'django.db.migrations.recorder.MigrationRecorder.Migration.<locals>.Migration'>
>>> recorder.Migration
<class 'django.db.migrations.recorder.MigrationRecorder.Migration.<locals>.Migration'>
>>> recorder._migration_class.objects.all()
<QuerySet [<Migration: Migration 0001_initial for contenttypes>]>
>>> recorder.migration_qs
<QuerySet [<Migration: Migration 0001_initial for contenttypes>]>
>>> recorder.has_table()
True
>>> recorder.applied_migrations()
{('contenttypes', '0001_initial'): <Migration: Migration 0001_initial for contenttypes>}
>>> recorder.record_applied('xxx', '0002.xxx')
>>> recorder.record_unapplied('xxx', '0002.xxx')
>>> recorder.flush()
```

相关的类方法解释
```python
    def applied_migrations(self):
        """
        Return a dict mapping (app_name, migration_name) to Migration instances
        for all applied migrations.
        """
        if self.has_table():
            return {
              # 用元组表示key，用迁移记录表示value
                (migration.app, migration.name): migration
                for migration in self.migration_qs
            }
        else:
            # If the django_migrations table doesn't exist, then no migrations
            # are applied.
            return {}
```

相关的类方法解释
```python
    def record_applied(self, app, name):
        """Record that a migration was applied."""
        self.ensure_schema()
        self.migration_qs.create(app=app, name=name)  # 数据库生成一条migrations记录

    def record_unapplied(self, app, name):
        """Record that a migration was unapplied."""
        self.ensure_schema()
        self.migration_qs.filter(app=app, name=name).delete()  # 数据库删除一条migrations记录

    def flush(self):
        """Delete all migration records. Useful for testing migrations."""
        self.migration_qs.all().delete()    # 数据库清空migrations记录
```