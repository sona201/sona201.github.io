---
title: "Django MigrationGraph 交互实验"
date: "2023-02-08T01:06:45+08:00"
lastmod: "2023-02-08T01:06:45+08:00"
categories: ["django"]
slug: "django-migration-graph-notes"
draft: false
---

Django4.0源码分析-1.10 关于MigrationGraph类的解读与实战

为了迁移文件之间的校验，然后有这个类。 \
也不清楚这个类是干嘛的，好像是画图的，但涉及算法深度优先，链表

弹幕有说，这段代码是在makemigrations后，生成migrations文件，盲猜是分析那些文件关系用的。。。

跟着操作下
```
(venv) clin:firstDjango/ $ python3 manage.py shell
Python 3.10.5 (main, Jul 22 2022, 15:13:07) [Clang 12.0.5 (clang-1205.0.22.11)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> from django.db.migrations.graph import Node,DummyNode, MigrationGraph
>>> graph = MigrationGraph()
>>> graph.add_node('k1', 'm1')
>>> graph.add_node('k2', 'm2')
>>> graph.add_node('k3', 'm3')
>>> graph.add_node('k4', 'm4')
>>> graph.add_node('k5', 'm5')
>>> graph.add_node('k6', 'm6')
>>> graph.add_dependency('m1', 'k1', 'k2')
>>> graph.add_dependency('m2', 'k2', 'k3')
>>> graph.add_dependency('m3', 'k3', 'k4')
>>> graph.add_dependency('m5', 'k5', 'k6')
>>> k1 -> k2 -> k3 -> k4  k5 -> k6
KeyboardInterrupt
>>> graph.validate_consistency()
>>> graph.forwards_plan('k3')
['k4', 'k3']
>>> graph.forwards_plan('k1')
['k4', 'k3', 'k2', 'k1']
>>> graph.forwards_plan('k5')
['k6', 'k5']
>>> graph.backwards_plan('k5')
['k5']
>>> graph.backwards_plan('k6')
['k5', 'k6']
>>> graph.backwards_plan('k3')
['k1', 'k2', 'k3']
>>> graph.add_dependency('m3', 'k3', k6')
  File "<console>", line 1
    graph.add_dependency('m3', 'k3', k6')
                                       ^
SyntaxError: unterminated string literal (detected at line 1)
>>> graph.add_dependency('m3', 'k3', 'k6')
>>> graph.backwards_plan('k3')
['k1', 'k2', 'k3']
>>> graph.forwards_plan('k3')
['k6', 'k4', 'k3']
>>> graph.node_map['k6'].chilren
Traceback (most recent call last):
  File "<console>", line 1, in <module>
AttributeError: 'Node' object has no attribute 'chilren'
>>> graph.node_map['k6'].children
{<Node: ('k', '5')>, <Node: ('k', '3')>}
>>> graph.node_map['k3'].parent
Traceback (most recent call last):
  File "<console>", line 1, in <module>
AttributeError: 'Node' object has no attribute 'parent'
>>> graph.node_map['k3'].parents
{<Node: ('k', '4')>, <Node: ('k', '6')>}
>>> graph.ensure_not_cyclic()
>>> graph.remove_replaced_nodes('k1', ['k6'])
>>> graph.node_map['k1'].parents
{<Node: ('k', '2')>}
>>> graph.node_map['k1'].children
{<Node: ('k', '5')>, <Node: ('k', '3')>}
>>> graph.ensure_not_cyclic()
Traceback (most recent call last):
  File "<console>", line 1, in <module>
  File "/Users/example/File/Project/firstDjango/venv/lib/python3.10/site-packages/django/db/migrations/graph.py", line 285, in ensure_not_cyclic
    ", ".join("%s.%s" % n for n in cycle)
  File "/Users/example/File/Project/firstDjango/venv/lib/python3.10/site-packages/django/db/migrations/graph.py", line 285, in <genexpr>
    ", ".join("%s.%s" % n for n in cycle)
TypeError: not enough arguments for format string
```