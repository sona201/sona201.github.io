---
date: "2023-01-16T14:03:35+08:00"
lastmod: "2023-01-16T14:03:35+08:00"
categories: ["python"]
draft: false
title: 'JSONEncoder'
tags: ['python', 'json', 'serialize', 'python-serialize-datetime-into-json']
slug: "jsonencoder-datetime-notes"
---

## json dumps date类型数据

[原文参考](https://pynative.com/python-serialize-datetime-into-json/#:~:text=As%20per%20ISO%208601%2C%20It,dump()%20and%20json.)

> `json` 默认只支持6种数据格式转换，遇到特殊的类型，需要自己定制化, `json`提供了`json.JSONEncoder` 类来定制化解决这个问题\
> Python json module provides a json.JSONEncoder Class. We can extend it If we want more customized output. i.e., To serialize the DateTime instance into JSON, we need to subclass JSONEncoder so we can implement our custom serialization.

### 事情背景
网上找到一个抓取节假日的脚本，发现使用了`dumps`方法，这种方式没有用过，了解后发现是json模块dump 日期类型。\
[脚本链接](https://github.com/NateScarlet/holiday-cn/blob/master/scripts/fetch.py)

### 代码分析
#### 1. dump原理

在`json.dumps`方法中，本质还是执行序列化类cls, 默认这个类为`JSONEncoder`，可以根据自己的情况定制。\
python的`json`模块里，源码如下
```python
def dumps(obj, *, skipkeys=False, ensure_ascii=True, check_circular=True,
        allow_nan=True, cls=None, indent=None, separators=None,
        default=None, sort_keys=False, **kw):
    """Serialize ``obj`` to a JSON formatted ``str``.

    If ``skipkeys`` is true then ``dict`` keys that are not basic types
    (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped
    instead of raising a ``TypeError``.

    If ``ensure_ascii`` is false, then the return value can contain non-ASCII
    characters if they appear in strings contained in ``obj``. Otherwise, all
    such characters are escaped in JSON strings.

    If ``check_circular`` is false, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    If ``allow_nan`` is false, then it will be a ``ValueError`` to
    serialize out of range ``float`` values (``nan``, ``inf``, ``-inf``) in
    strict compliance of the JSON specification, instead of using the
    JavaScript equivalents (``NaN``, ``Infinity``, ``-Infinity``).

    If ``indent`` is a non-negative integer, then JSON array elements and
    object members will be pretty-printed with that indent level. An indent
    level of 0 will only insert newlines. ``None`` is the most compact
    representation.

    If specified, ``separators`` should be an ``(item_separator, key_separator)``
    tuple.  The default is ``(', ', ': ')`` if *indent* is ``None`` and
    ``(',', ': ')`` otherwise.  To get the most compact JSON representation,
    you should specify ``(',', ':')`` to eliminate whitespace.

    ``default(obj)`` is a function that should return a serializable version
    of obj or raise TypeError. The default simply raises TypeError.

    If *sort_keys* is true (default: ``False``), then the output of
    dictionaries will be sorted by key.

    To use a custom ``JSONEncoder`` subclass (e.g. one that overrides the
    ``.default()`` method to serialize additional types), specify it with
    the ``cls`` kwarg; otherwise ``JSONEncoder`` is used.

    """
    # cached encoder
    if (not skipkeys and ensure_ascii and
        check_circular and allow_nan and
        cls is None and indent is None and separators is None and
        default is None and not sort_keys and not kw):
        return _default_encoder.encode(obj)
    if cls is None:
        cls = JSONEncoder
    return cls(
        skipkeys=skipkeys, ensure_ascii=ensure_ascii,
        check_circular=check_circular, allow_nan=allow_nan, indent=indent,
        separators=separators, default=default, sort_keys=sort_keys,
        **kw).encode(obj)
```

#### JSONEncoder的方法使用
在`JSONEncoder`模块中，关键点如下
```
class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str               | string        |
    +-------------------+---------------+
    | int, float        | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """
    item_separator = ', '
    key_separator = ': '
    def __init__(self, *, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, default=None):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is false, then it is a TypeError to attempt
        encoding of keys that are not str, int, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is true, the output is guaranteed to be str
        objects with all incoming non-ASCII characters escaped.  If
        ensure_ascii is false, the output can contain non-ASCII characters.

        If check_circular is true, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is true, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is true, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be an (item_separator, key_separator)
        tuple.  The default is (', ', ': ') if *indent* is ``None`` and
        (',', ': ') otherwise.  To get the most compact JSON representation,
        you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        elif indent is not None:
            self.item_separator = ','
        if default is not None:
            self.default = default

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                # Let the base class default method raise the TypeError
                return JSONEncoder.default(self, o)

        """
        raise TypeError(f'Object of type {o.__class__.__name__} '
                        f'is not JSON serializable')
```

### 使用案例

#### 默认方式执行
直接使用`json.dumps`会报错没有对应的类型，`JSONEncoder`只支持6种基础类型转换
```python
import json
import datetime
from json import JSONEncoder

employee = {
    "id": 456,
    "name": "William Smith",
    "salary": 8000,
    "joindate": datetime.datetime.now()
}

employeeJSONData = json.dumps(employee)
print(employeeJSONData)
```

output
```
employeeJSONData = json.dumps(employee)
print(employeeJSONData)
Encode DateTime Object into JSON using custom JSONEncoder
Traceback (most recent call last):
  File "/usr/local/var/pyenv/versions/3.8.15/lib/python3.8/code.py", line 90, in runcode
    exec(code, self.locals)
  File "<input>", line 2, in <module>
  File "/usr/local/var/pyenv/versions/3.8.15/lib/python3.8/json/__init__.py", line 231, in dumps
    return _default_encoder.encode(obj)
  File "/usr/local/var/pyenv/versions/3.8.15/lib/python3.8/json/encoder.py", line 199, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "/usr/local/var/pyenv/versions/3.8.15/lib/python3.8/json/encoder.py", line 257, in iterencode
    return _iterencode(o, 0)
  File "/usr/local/var/pyenv/versions/3.8.15/lib/python3.8/json/encoder.py", line 179, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
TypeError: Object of type datetime is not JSON serializable
```

#### 使用自定义`DateTimeEncoder`序列化

```python
import json
import datetime
from json import JSONEncoder

employee = {
    "id": 456,
    "name": "William Smith",
    "salary": 8000,
    "joindate": datetime.datetime.now()
}

# subclass JSONEncoder
class DateTimeEncoder(JSONEncoder):
        #Override the default method
        def default(self, obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()

print("Printing to check how it will look like")
print(DateTimeEncoder().encode(employee))

print("Encode DateTime Object into JSON using custom JSONEncoder")
employeeJSONData = json.dumps(employee, indent=4, cls=DateTimeEncoder)
# indent=4 缩进为4个空格
# DateTimeEncoder 自定义转换，可以做更多自定义格式
print(employeeJSONData)
```

output
```
Printing to check how it will look like
{"id": 456, "name": "William Smith", "salary": 8000, "joindate": "2023-01-16T13:28:19.018879"}
Encode DateTime Object into JSON using custom JSONEncoder
{
    "id": 456,
    "name": "William Smith",
    "salary": 8000,
    "joindate": "2023-01-16T13:28:19.018879"
}
```

#### 使用自定义`DateTimeEncoder`序列化，更改缩进，序列化值优化

```python
import json
import datetime
from json import JSONEncoder

employee = {
    "id": 456,
    "name": "William Smith",
    "salary": 8000,
    "joindate": datetime.datetime.now()
}

# subclass JSONEncoder
class DateTimeEncoder(JSONEncoder):
    #Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            res = obj.isoformat()
            return res[:10]

print("Printing to check how it will look like")
print(DateTimeEncoder().encode(employee))

print("Encode DateTime Object into JSON using custom JSONEncoder")
employeeJSONData = json.dumps(employee, indent=0, cls=DateTimeEncoder)
# indent=4 缩进为4个空格
# DateTimeEncoder 自定义转换，可以做更多自定义格式
print(employeeJSONData)
```

output
```
Printing to check how it will look like
{"id": 456, "name": "William Smith", "salary": 8000, "joindate": "2023-01-16T13:28:19.018879"}
Encode DateTime Object into JSON using custom JSONEncoder
Encode DateTime Object into JSON using custom JSONEncoder
{
"id": 456,
"name": "William Smith",
"salary": 8000,
"joindate": "2023-01-16"
}
```