---
date: "2023-02-14T01:12:26+08:00"
lastmod: "2023-02-14T01:12:26+08:00"
categories: ["python"]
draft: false
title: 'python __new__'
tags: ['python', '__new__', '构造方法', '面向对象', '创建函数']
slug: "python-new-construction-notes"
---

[原文链接](https://mp.weixin.qq.com/s?__biz=Mzg5NTYyMDgyNg==&mid=2247489147&idx=1&sn=ebfcc0c8ddde7345cc79b224934d02f8&source=41#wechat_redirect)

```python
class Test:
    def __new__(cls):
        print('__new__')
        return object().__new__(cls)

    def __init__(self):
        print('__init__')


test = Test()


class SingletonObject:
    def __new__(cls, *args, **kwargs):
        if not hasattr(SingletonObject, "_instance"):
            SingletonObject._instance = object.__new__(cls)
        return SingletonObject._instance

    def __init__(self):
        pass


singleton = SingletonObject()
print(singleton.__dict__)


class NonZero(int):
    def __new__(cls, value):
        return super().__new__(cls, value) if value != 0 else None


res = NonZero(0)
print('res 0', res)
res1 = NonZero(1)
print('res 1', res1)
```



https://www.cnblogs.com/techflow/p/13156361.html

https://changchen.me/blog/20201122/metaclass-with-django-orm/

实战演示
https://segmentfault.com/a/1190000004426130

```python
sensitive_words_list = ['asshole', 'fuck', 'shit']


def detect_sensitive_words(string):
    """检测敏感词汇"""
    # words_detected = filter(lambda word: word in string.lower(), sensitive_words_list)
    words_detected = None
    for item in sensitive_words_list:
        if item in string.lower():
            words_detected = True

    if words_detected:
        raise NameError('Sensitive words {0} detected in the string "{1}".'.format(words_detected, string))


class CleanerMeta(type):

    def __new__(mcs, class_name, bases, attrs):
        detect_sensitive_words(class_name)  # 检查类名
        # map(detect_sensitive_words, attrs.iterkeys())  # 检查属性名

        print("Well done! You are a polite coder!")  # 如无异常，输出祝贺消息

        return super(CleanerMeta, mcs).__new__(mcs, class_name, bases, attrs)
        # 重要！这行一定不能漏！！这回调用内建的类构造器来构造类，否则定义好的类将会变成 None


class APIBase(metaclass=CleanerMeta):
    pass


class ImAGoodBoy(APIBase):
    a_polite_attribute = 1
class FuckMyBoss(APIBase):

    pass

# detect_sensitive_words('avc')

```