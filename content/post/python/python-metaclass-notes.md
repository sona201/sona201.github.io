---
date: "2023-02-13T00:53:26+08:00"
lastmod: "2023-02-13T00:53:26+08:00"
categories: ["python"]
draft: false
title: 'metaclass学习'
tags: ['metaclass', 'python', '继承', '面向对象']
slug: "python-metaclass-notes"
---

本文主要介绍Python的MetaClass的用法。

MetaClass也是一个class，这个class继承自type，它用于生产新的class对象。定义class的时候，就会执行到MetaClass的__new__()代码。

从这里出发，我们需要一个新的class的时候，就可以使用MetaClass定义它的行为。本文介绍MetaClass的三种用法：

- 定义新的class的时候，执行一些检查操作
- 定义新的class的时候，将新class进行注册动作
- 定义新的class的时候，自动修改class的属性

MetaClass可以读取和修改class的属性。

```python
class Meta(type):
    def __new__(meta, name, bases, class_dict):
        print('meta => ', meta)
        print('name => ', name)
        print('bases => ', bases)
        print('class_dict => ', class_dict)
        return type.__new__(meta, name, bases, class_dict)


class MyClass(metaclass=Meta):
    stuff = 123

    def __init__(self):
        self.foo()

    def foo(self):
        print('MyClass => foo')
        pass


obj = MyClass()  # 这里就会执行 __new__ 方法
print(dir(obj))
# print('__dict__', help(obj))  # 看看python方法
"""
在继承的时候就会触发metaclass的__new__方法调用，new
meta =>  <class '__main__.Meta'>
name =>  MyClass
bases =>  ()
class_dict =>  {'__module__': '__main__', '__qualname__': 'MyClass', 'stuff': 123, '__init__': <function MyClass.__init__ at 0x105002cb0>, 'foo': <function MyClass.foo at 0x105002c20>}
MyClass => foo
['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'foo', 'stuff']
"""
```

关于__new__方法讲解文章： [一文详解Python中__new__方法的作用](https://www.51cto.com/article/711136.html)

## 用MetaClass验证

定义一个新的class相当于调用type创建一个新的class对象，所以覆盖__new__()方法可以实现一些验证的动作。

下面的代码定义了一个多边形的MetaClass，在定义新的class的时候，验证边数是否小于3，如果小于3，这不科学。

```python
class ValidatePolygon(type):
    def __new__(meta, name, bases, class_dict):
        # Don’t validate the abstract Polygon class
        # if bases != (object,):
        # if class_dict['sides']:
        if class_dict['sides'] < 3:
            raise ValueError('Polygons need 3+ sides')
        return type.__new__(meta, name, bases, class_dict)


class Polygon(metaclass=ValidatePolygon):
    # sides = None  # Specified by subclasses

    @classmethod
    def interior_angles(cls):
        return (cls.sides - 2) * 180


class Triangle(Polygon):
    sides = 3


# obj = Triangle()
"""
这里执行会有问题，因为python会先创建类 Polygon ，在元类中 Polygon 的属性 sides 不满足条件，会导致报错
因为继承了元类 ValidatePolygon ，所以每次创建类的时候都会触发逻辑
"""
```
这一段有问题，会触发sides=None的报错，应该是执行顺序问题

[realpython metaclass](https://realpython.com/python-metaclasses/)

## 修改class的属性
假设我们想要实现一个Python对象到数据库字段的对应（也就是ORM），我们可以使用前面博客提到的Descriptor，如下。

```python
class Field(object):
       def __init__(self, name):
           self.name = name
           self.internal_name = ‘_’ + self.name
       def __get__(self, instance, instance_type):
           if instance is None: return self
           return getattr(instance, self.internal_name, ”)
       def __set__(self, instance, value):
           setattr(instance, self.internal_name, value)
 
class Customer(object):
       # Class attributes
       first_name = Field(‘first_name’)
       last_name = Field(‘last_name’)
       prefix = Field(‘prefix’)
       suffix = Field(‘suffix’)
```

但是这里存在的问题是，first_name已经写了一次了，还要在创建Field的时候再写一次，不是有些多余吗？Field应该自动根据引用它的变量名自动命名。这可以通过MetaClass来做到。

```python
class Meta(type):
    def __new__(meta, name, bases, class_dict):
        for key, value in class_dict.items():
            if isinstance(value, Field):
                value.name = key
                value.internal_name = '_' + key
        cls = type.__new__(meta, name, bases, class_dict)
        return cls


# Field不需要在接受参数创建实例了
class Field():
    def __init__(self):
        # These will be assigned by the metaclass.
        self.name = None
        self.internal_name = None


# 这里由MetaClass代劳
class BetterCustomer(metaclass=Meta):
    first_name = Field()  # 类中类，绑定类对象的地址
    last_name = Field()
    prefix = Field()
    suffix = Field()


print(help(BetterCustomer))
# print(help(BetterCustomer.first_name))
print(dir(BetterCustomer.first_name))
print(BetterCustomer.first_name.name, BetterCustomer.first_name.internal_name)
print(BetterCustomer.last_name)
print(BetterCustomer.prefix)
print(BetterCustomer.suffix)
"""
Help on class BetterCustomer in module __main__:

class BetterCustomer(builtins.object)
 |  # 这里由MetaClass代劳
 |  
 |  Data descriptors defined here:
 |  
 |  __dict__
 |      dictionary for instance variables (if defined)
 |  
 |  __weakref__
 |      list of weak references to the object (if defined)
 |  
 |  ----------------------------------------------------------------------
 |  Data and other attributes defined here:
 |  
 |  first_name = <__main__.Field object>
 |  
 |  last_name = <__main__.Field object>
 |  
 |  prefix = <__main__.Field object>
 |  
 |  suffix = <__main__.Field object>

None
['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'internal_name', 'name']
first_name _first_name
<__main__.Field object at 0x102bff0d0>
<__main__.Field object at 0x102bfeb60>
<__main__.Field object at 0x102bfdd20>
"""
```
综上，MetaClass是非常实用的，可以帮我们减少很多需要重复复制粘贴的代码。

python learning website \
[Python __new__](https://www.pythontutorial.net/python-oop/python-__new__/) \
[Python type Class](https://www.pythontutorial.net/python-oop/python-type-class/) \
[Python Metaclass](https://www.pythontutorial.net/python-oop/python-metaclass/) \
[Python Metaclass Example](https://www.pythontutorial.net/python-oop/python-metaclass-example/) 
