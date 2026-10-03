---
title: "Python logging 模块分析及使用"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["python"]
tags: ["python", "logging"]
draft: false
---

# Python 日志模块logging分析及使用-1

[掘金原文](https://juejin.cn/user/4248168662050013/posts)

开发部署项目时，不可能将所有的信息都输出到控制台中，因此我们将这些信息记录到日志文件中，不仅方便查看程序运行的情况，也可以在项目出现故障时根据该运行时产生的日志快速定位问题。

`Python`中提供了日志模块`logging`，可以方便的记录日志信息。

> 本文主要分析了`logging`模块的相关知识及具体使用。  
> 当前介绍该日志模块的文章有很多，之所以还要进行记录，一方面是因为没有看到系统的介绍，二是通过梳理此部分内容，做到不止会用，还明白内部函数调用。

## 一、日志级别

`Python`标准库`logging`用做记录日志，默认分为五种日志级别：

- `DEBUG(10)`：详细信息，调试问题时所需
- `INFO(20)`：证明事情可按预期工作
- `WARNING(30)`：有意外，将来可能发生问题，但依然可用
- `ERROR(40)`：严重问题，程序不能执行一些功能
- `CRITICAL(50)`：严重错误

我们自定义日志级别时注意不要和默认的日志级别数值型相同（这是什么意思呢？），`logging`执行时输出**大于等于**设置的值日级别的日志信息，如设置级别为INFO，则INFO, WARNING, ERROR, CRITICAL级别的日志都会输出。  
5种等级分别对应5种日志打印方法：`debug, info, warning, error, critical`。  
默认的是`WARNING`，即当等级大于等于`WARNING`才被跟踪。

## 二、logging流程

官方的`logging`模块工作流程图如下：  

![logging流程图](/images/python-logging-flow.png)

logging流程图

**logging流程图**

从上图中可以看到这几种python类型，`Logger, LogRecord, Filter, Handler, Formatter`。  
**类型说明**

- `Logger`：**日志**，暴露函数给应用程序，基于日志记录器和过滤器级别决定哪些日志有效。
- `LogRecord`：**日志记录器**，将日志传到相应的处理器处理。
- `Handler`：**处理器**，将（日志记录器产生的）日志记录发送至合适的目的地。
- `Filter`：**过滤器**，提供了更好的粒度控制，它可以决定输出哪些日志记录。
- `Formatter`：**格式化器**，指明了最终输出中日志记录的布局。

**基本流程**:

- 判断`Logger`对象对于设置的级别是否可用，如果可用，则往下执行，否则，流程结束。
- 创建`LogRecord`对象，如果注册到`Logger`对象中的`Filter`对象过滤后返回False， 则不记录日志，流程结束，否则，向下执行。
- `LogRecord`对象将`Handler`对象传入当前的`Logger`对象，（图中子流程）如果`Handler`对象的日志级别大于设置的日记级别，再判断注册到`Handler`对象中的`Filter`对象过滤后是否返回True而放行输出日志信息，否则不放行，流程结束。
- 如果传入的`Handler`大于`Logger`中设置的级别，也即`Handler`有效，则往下执行，否则，流程结束。
- 判断这个`Logger`对象是否还有父`Logger`对象，如果没有（代表当前`Logger`对象是最顶层的`Logger`对象`root Logger`），流程结束。否则将`Logger`对象设置为它的父`Logger`对象，重复上面3,4两步，输出父类`Logger`对象中的日志输出，直到是`root Logger`对象。

## 三、几个重要的类

前面讲`logging`流程的时候，提到几个概念：`Logger`，`Handler`，`Filter`，`Formatter`。

### 3.1 Logger类

`Logger`对象有3个任务要做：

- 向应用程序代码暴露`info, debug`等方法，使应用程序可以在运行时记录日志消息
- 基于日志级别（默认的过滤设施）或`Filter`对象来决定要对哪些日志进行后续处理
- 将日志消息传送给所有感兴趣的日志`handlers`

一个系统只有一个根`Logger`对象，并且**该对象不能被直接实例化**。

> 通过调用`logging.getLogger(name)`函数创建`Logger`类对象。

`Logger`对象最常用的方法有两类：（1）配置方法，（2）消息发送方法

`Logger`对象可以设置多个`Handler`对象和`Filter`对象，`Handler`对象可以设置`Formatter`对象。  
`Formatter`对象用来设置消息的具体输出格式。

#### 3.1.1 最常用的配置方法

|方法|描述|
|---|---|
|`Logger.setLevel`|设置日志器将会处理的日志消息的最低严重级别|
|`Logger.addHandler()`|为该`Logger`对象添加一个`handler`对象|
|`Logger.removeHandler`|为该`Logger`对象移除一个`handler`对象|
|`Logger.addFilter()和Logger.removeFilter()`|为该`Logger`对象添加 和 移除一个`filter`对象|

`logger`对象配置完成后，可使用下面的方法来创建日志记录：

- `Logger.debug(), Logger.info(), Logger.warning(), Logger.error(), Logger.critical()`：创建一个与他们的方法名对应等级的日志记录
- `Logger.exception()`：创建一个类似于`Logger.error()`的日志消息
- `Logger.log()`：需要获取一个明确的日志level参数来创建一个日志记录

**1. 获取`Logger`对象**  
通常是通过`--logging.getLogger()`的方法。该方法有一个可选参数`name`,该参数表示将要返回的日志器的名称标识，如果不提供该参数，则其值为`root`。  
若以相同的`name`参数值多次调用`getLogger()`方法，将会返回指向同一个`Logger`对象的引用。

**2. logger的层级结构与有效等级**

- `logger`的名称是一个以 `'.'` 分割的层级结构，每个`'.'`后面的`logger`都是`'.'`前面的`logger`的`children`，例如，有一个名称为 `foo` 的`logger`，其它名称分别为`foo.bar, foo.bar.baz`和 `foo.bam`都是 `foo` 的后代。
    
- `logger`有一个"**有效等级（`effective level`）**"的概念。**如果一个logger上没有被明确设置一个level，那么该logger就是使用它parent的level**;如果它的`parent`也没有明确设置`level`则继续向上查找`parent`的`parent`的有效`level`，依次类推，直到找到个一个明确设置了`level`的祖先为止。需要说明的是，**`root logger`总是会有一个明确的`level`设置（默认为 `WARNING`）**。当决定是否去处理一个已发生的事件时，`logger`的有效等级将会被用来决定是否将该事件传递给该`logger`的`handlers`进行处理。
    
- `child loggers`在完成对日志消息的处理后，默认会将日志消息传递给与它们的祖先`loggers`相关的`handlers`。因此，我们不必为一个应用程序中所使用的所有loggers定义和配置handlers，**只需要为一个顶层的`logger`配置`handlers`**，然后按照需要创建`child loggers`就可足够了。我们也可以通过将一个logger的`propagate`属性设置为False来关闭这种传递机制。
    

#### 3.1.2 创建Logger对象logging.getLogger([name])

日志记录的工作主要由`Logger`对象来完成。前面讲到一个系统只有一个根`Logger`对象，并且**该对象不能被直接实例化**。

需要通过`logging.getLogger([name])`来获取`Logger`对象。  
在调用`getLogger`时要提供`Logger`的名称（**多次使用相同名称来调用getLogger，返回的是同一个对象的引用。**），`Logger`实例之间有层次关系，这些关系通过`Logger`名称来体现。

py

复制代码

```python
p = logging.getLogger("root")  
c1 = logging.getLogger("root.c1")  
c2 = logging.getLogger("root.c2")
```

例子中，`p`是`父logger`, `c1,c2`分别是p的`子logger`。`c1, c2`将继承`p`的设置。如果省略了`name`参数, `getLogger`将返回日志对象层次关系中的`根Logger`。

每个`Logger`对象都可以设置一个名字，如果设置`logger = logging.getLogger(__name__)`，`__name__`是`Python`中的一个特殊内置变量，他代表当前模块的名称（默认为`__main__`）。

该函数内部根据是否指定名称返回对应的**Logger对象**。

```python
root = RootLogger(WARNING)  
Logger.root = root  
Logger.manager = Manager(Logger.root)  
  
def getLogger(name=None):  
    """  
    Return a logger with the specified name, creating it if necessary.  
    If no name is specified, return the root logger.  
    """  
    if name:  
        return Logger.manager.getLogger(name)  
    else:  
        return root
```


**示例：**


`1import logging   2logger = logging.getLogger('test')   3logger.warning('this is a warning info')   4# 输出   5WARNING:test:this is a warning info`

```python
import logging  
logger = logging.getLogger('test')  
logger.warning('this is a warning info')  
# 输出  
WARNING:test:this is a warning info
```

### 3.2 Handler类

`Handler`对象的作用是（基于日志消息的等级）将消息分发到`handler`指定的位置（文件、网络、邮件等）。`Logger`对象可以通过`addHandler()`方法为自己添加`handler`对象。

> 应用程序代码不应该直接实例化和使用`Handler`实例。因为`Handler`是一个基类，只**定义了所有`handlers`都应该有的接口**，同时提供了一些子类可以直接使用或覆盖的默认行为。
> 
> **常用接口**有：
> 
> - `setLevel()`
> - `setFormatter()`
> - `set_name()`

常用的`Handler`：

|Handler|描述|
|---|---|
|`logging.StreamHandler`|将日志消息发送到输出到`Stream`，如`std.out, std.err`或任何`file-like`对象。|
|`logging.FileHandler`|将日志消息发送到**磁盘文件**，默认情况下**文件大小会无限增长**|
|`logging.handlers.RotatingFileHandler`|将日志消息发送到**磁盘文件**，并支持日志文件**按大小切割**|
|`logging.hanlders.TimedRotatingFileHandler`|将日志消息发送到**磁盘文件**，并支持日志文件**按时间切割**|
|`logging.handlers.HTTPHandler`|将日志消息以`GET`或`POST`的方式发送给一个`HTTP`服务器|
|`logging.handlers.SMTPHandler`|将日志消息发送给一个**指定的email地址**|
|`logging.NullHandler`|该`Handler`实例会忽略`error messages`，通常被想使用`logging`的`library`开发者使用来避免`'No handlers could be found for logger XXX'`信息的出现。|

**类之间的继承关系**如下：  

![在这里插入图片描述](https://p1-jj.byteimg.com/tos-cn-i-t2oaga2asx/gold-user-assets/2020/1/2/16f658205cad6626~tplv-t2oaga2asx-jj-mark:3024:0:0:0:q75.png "在这里插入图片描述")

在这里插入图片描述

示例：

```python
import logging  
  
logger = logging.getLogger()  # 获取Logger对象  
handler = logging.FileHandler('output.log', mode='a', encoding=None, delay=False)  
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', style='%')  
handler.setFormatter(formatter)  # handler对象设置格式  
handler.setLevel(logging.DEBUG)  # handler设置日志级别  
  
logger.addHandler(handler)  # 添加handler对象
```

### 3.3 Filter类

`Filter`实例用于执行日志记录的任意筛选。  
`Loggers`和`Handlers`可以根据需要使用筛选器实例筛选记录.  
`logging`标准库只提供了一个`base filter`，其构造函数`__init__`接收`name`，默认的行为是名为`name`的`logger`及其子`logger`的消息能通过过滤器，其余的被过滤掉。

```python
class Filter(object):  
    """  
    Filter instances are used to perform arbitrary filtering of LogRecords.  
    """  
    def __init__(self, name=''):  
        """  
        Initialize a filter.  
  
        Initialize with the name of the logger which, together with its  
        children, will have its events allowed through the filter. If no  
        name is specified, allow every event.  
        """  
        self.name = name  
        self.nlen = len(name)
```

### 3.4 Formatter类

`Formatter`对象用于配置日志信息的最终顺序、结构和内容。与`logging.Handler`基类不同的是，应用代码可以直接实例化`Formatter`类。

`Formatter`类的构造方法定义如下：  
`logging.Formatter.__init__(fmt=None, datefmt=None, style='%')`

该方法可接收3个可选参数：

- `fmt`：指定消息格式化字符串，如果不指定该参数则默认使用`message`的原始值
- `datefmt`：指定日期格式字符串，如果不指定，则默认使用`"%Y-%m-%d %H:%M:%S"`
- `style`：可取值为`'%', '{'和'$'`，如果不指定，则默认使用`'%'`

|格式|含义|
|---|---|
|`%(levelno)s`|打印日志级别的数值|
|`%(levelname)s`|打印日志级别名称|
|`%(pathname)s`|打印当前执行程序的路径|
|`%(filename)s`|打印当前执行程序名|
|`%(funcName)s`|打印日志的当前函数|
|`%(lineno)d`|打印日志的当前行号|
|`%(asctime)s`|打印日志的时间|
|`%(thread)d`|打印线程ID|
|`%(message)s`|打印日志信息|
|`%(process)s`|当前进程，进程ID|
|`%(module)s`|调用日志输出函数的模块名，`filename`的名称部分，不包含后缀|
|`%(msecs)d`|日志事件发生事件的毫秒部分。`logging.basicConfig()`中用参数`datefmt`将会去掉`asctime`中产生的毫秒部分，可以用这个加上。|

一般直接使用`logging.Formatter(fmt, datefmt)`

```python
import logging

fmt = "%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s: %(message)s"  
datefmt="%Y-%m-%d %H:%M:%S"  
logFormatter = logging.Formatter(fmt, datefmt)
```

## 四、使用示例

> 该部分主要展示如何使用`logging`模块记录日志信息的使用方法。

**默认的输出格式**如下：  

![在这里插入图片描述](https://p1-jj.byteimg.com/tos-cn-i-t2oaga2asx/gold-user-assets/2020/1/2/16f658205d929fc1~tplv-t2oaga2asx-jj-mark:3024:0:0:0:q75.png "在这里插入图片描述")

在这里插入图片描述

  
**示例：**  

![在这里插入图片描述](https://p1-jj.byteimg.com/tos-cn-i-t2oaga2asx/gold-user-assets/2020/1/2/16f658205e8b09c6~tplv-t2oaga2asx-jj-mark:3024:0:0:0:q75.png "在这里插入图片描述")

在这里插入图片描述

`logging`模块如何使用呢？下面介绍几种常用的使用方式：

一是使用`logging`的对外函数接口；二是使用`basicConfig()`方法，该方法能够满足基本的使用需求；三是通过创建`Logger`对象，可以进行更加复杂的处理。

### 4.1 直接调用logging接口

最简单的使用方法，就是直接调用`logging`标准库的接口，如`logging.debug()`，`logging.info()`等函数。  
默认的日志级别是`WARNING`，当等级大于等于`WARNING`才被跟踪。

> 内部默认调用的是`root.log(level, mas)`函数

接口函数如下：

- `debug()`
- `info()`
- `warning()`
- `error()`
- `critical()`

也可以直接使用同一接口`logging.log()`，输入级别及具体信息。

- `log(level, msg)`：`level`表示日志级别，输入日志级别对应的整数或代码，如下：

```python
CRITICAL = 50  
FATAL = CRITICAL  
ERROR = 40  
WARNING = 30  
WARN = WARNING  
INFO = 20  
DEBUG = 10  
NOTSET = 0
```

这些接口函数内部**实际调用的都是`Logger`类的对应函数**。如果`logger`没有`handler`时，可默认调用`basicConfig()`添加控制台`handler`。  
如，`logging.info()`函数内部调用`root.info()`函数，如下

```python
def info(msg, *args, **kwargs):  
    """  
    Log a message with severity 'INFO' on the root logger. If the logger has  
    no handlers, call basicConfig() to add a console handler with a pre-defined  
    format.  
    """  
    if len(root.handlers) == 0:  
        basicConfig()  
    root.info(msg, *args, **kwargs)
```

示例如下：
```python
import logging  
logging.warning('this is a warning info.')  
logging.error('this is a error info.')  
logging.debug('this is a debuginfo.')  
# 输出  
WARNING:root:this is a warning info.  
ERROR:root:this is a error info.  

logging.log(20, 'this is a info msg.')  
logging.log(30, 'this is a warn msg.')  
# 输出：  
WARNING:root:this is a warn msg.
```

**记录具体异常信息**

当发生异常时，直接使用无参数的`debug(), info(), warning(), error(), critical()`方法并不能记录异常信息。

**我们看一下各个接口的定义及参数：**
```python
# 普通接口  
def warning(msg, *args, **kwargs)  
# 内部调用如下函数：  
self._log(WARNING, msg, args, **kwargs)  

# 统一接口  
def log(level, msg, *args, **kwargs)  
# 内部调用如下函数：
self._log(level, msg, args, **kwargs)  

# exception函数，参数中默认exc_info为True  
def exception(msg, *args, exc_info=True, **kwargs):  
   error(msg, *args, exc_info=exc_info, **kwargs)  
# 内部调用如下函数：
self._log(ERROR, msg, args, **kwargs)
```

由上面代码可见，其内部都是调用函数`Logger._log(level, msg, args, **kwargs)`。不同的是参数，如`level`日志级别。  
函数`Logger._log()`的定义如下：
```python
def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False)
    pass
```


可见，其除了`level`， `msg`以外，还有参数`exc_info`。该参数用来控制是否打印具体信息。

**函数`exception()`就等于`error(msg, exc_info=True)`**

因此：  
**记录异常信息的方法**：

- 设置`exc_info`参数为`True`，指示是否打印执行信息
- 或者使用`exception()`方法，同时记录当前的堆栈追踪（仅从异常处理程度调用此方法）
- 还可以使用`log()`方法，但是要设置日志级别和`exce_info`参数。

`logger.log(level, msg, exc_info=True)`是各个接口函数的统一调用方式。

**示例代码：**
```python
import logging  
  
logging.basicConfig(filename="test.log", filemode="w", format="%(asctime)s    %(name)s:%(levelname)s:%(message)s",  
                    datefmt="%d-%M-%Y %H:%M:%S", level=logging.DEBUG)  
a = 5  
b = 0  
try:  
    c = a / b  
except Exception as e:  
    # 下面三种方式三选一，推荐使用第一种     
logging.exception("Exception occurred")  
    logging.error("Exception occurred", exc_info=True)  
    logging.log(level=logging.DEBUG, msg="Exception occurred", exc_info=True)
```

```

py

复制代码

 `1import logging    2    3logging.basicConfig(filename="test.log", filemode="w", format="%(asctime)s %(name)s:%(levelname)s:%(message)s", datefmt="%d-%M-%Y %H:%M:%S", level=logging.DEBUG)    4a = 5    5b = 0    6try:    7    c = a / b    8except Exception as e:    9    # 下面三种方式三选一，推荐使用第一种   10    logging.exception("Exception occurred")   11    logging.error("Exception occurred", exc_info=True)   12    logging.log(level=logging.DEBUG, msg="Exception occurred", exc_info=True)`

输出文件`test.log`的内容:  

![在这里插入图片描述](https://p1-jj.byteimg.com/tos-cn-i-t2oaga2asx/gold-user-assets/2020/1/2/16f658205f087401~tplv-t2oaga2asx-jj-mark:3024:0:0:0:q75.png "在这里插入图片描述")

在这里插入图片描述

### 4.2 使用basicConfig()函数

使用`basicConfig()`方法就能够满足基本的使用需要，如果方法没有传入参数，会根据默认的配置创建`Logger`对象，默认的日志级别被设置为**WARNING**。  
默认的日志输出格式：

|WARNING|root|message|
|---|---|---|
|日志级别|`Logger`实例|日志信息|

**函数定义：**  
`def basicConfig(**kwargs)`

该函数**可选的参数**如下表所示：

|参数名称|参数描述|
|---|---|
|`filename`|日志输出到文件的文件名|
|`filemode`|文件模式，`r[+]`、`w[+]`、`a[+]`|
|`format`|日志输出的格式|
|`datefmt`|日志附带日期时间的格式|
|`style`|格式占位符，默认为`“%”`和`“{}”`|
|`level`|设置日志输出级别|
|`stream`|定义输出流，用来初始化 `StreamHandler`对象，不能和 `filename`参数一起使用，否则会`ValueError`异常|
|`handles`|定义处理器，用来创建`Handler`对象，不能和`filename，stream`参数一起使用，否则也会抛出`ValueError`异常|

> - `stream`输出流不与`filename`输出文件一起使用
> - `handler`处理器不与`stream`输出流或`filename`输出文件一起用
> - 即`stream`、`filename`和`handler`互相排斥
> - 若想将日志信息同时输出到文件和控制台，则需要使用`Logger`处理器增加对应的处理方法。

`basicConfig()`方法可以实现将日志信息输出到文件中**或者**输出到定义的输出流中。

- **输出到文件中**，可以通过`filename`参数，或者通过`handler`处理器创建相应文件对象实现
    - 内部创建`FileHandle()`对象
- **打印到输出流**中，使用默认参数即可
    - 内部创建`StreamHandler()`对象

其中，`format`指定输出的格式和内容，`format`可以输出很多有用信息，具体格式见`Formatter类`。

该方法相当于显示调用`basicConfig()`进行参数的配置，而直接调用`logging.info()`接口函数，若没有`handler`时，是隐式调用`basicConfig()`的默认参数形式。

**1）日志信息打印到输出流**

py

复制代码

 `1import logging    2# 直接调用basicConfig()函数，使用默认参数    3logging.basicConfig()    4logging.debug('This is a debug message')    5logging.info('This is an info message')    6logging.warning('This is a warning message')    7logging.error('This is an error message')    8logging.critical('This is a critical message')    9   10# 输出：(默认级别是WARNING)   11WARNING:root:This is a warning message   12ERROR:root:This is an error message   13CRITICAL:root:This is a critical message`

**2）格式化输出**

**格式化输出时间：**  
通过`datefmt`参数可以格式化输出`log`的时间。

**常用的输出格式**如下：  
`format = '%(asctime)s - %(filename)s[line:%(lineno)d]- %(levelname)s: %(message)s'`  
该格式可以输出日志的打印时间，输出模块及行号，日志级别和输出的日志内容。

py

复制代码

`1import logging   2logging.basicConfig(format='%(asctime)s %(message)s', datefmt = '%Y-%m-%d %I:%M:%S %p')   3logging.warning('is when this event was occurred.')   4   5# 输出结果   62019-10-15 04:03:17 PM is when this event was occurred.`

**3） 将日志输出到指定文件**  
指定`filename`， `filemode`参数，可将日志内容输出到指定文件，示例代码如下：

py

复制代码

`1import logging   2   3logging.basicConfig(filename='test.log', filemode='w', format="%(asctime)s %(name)s:%(levelname)s:%(message)s", datefmt="%d-%M-%Y %H:%M:%S", level=logging.DEBUG)   4logging.debug('This is a debug message')   5logging.info('This is an info message')   6logging.warning('This is a warning message')   7logging.error('This is an error message')`

生成的日志文件`test.log`，内容如下：  

![在这里插入图片描述](https://p1-jj.byteimg.com/tos-cn-i-t2oaga2asx/gold-user-assets/2020/1/2/16f658205ef08685~tplv-t2oaga2asx-jj-mark:3024:0:0:0:q75.png "在这里插入图片描述")

在这里插入图片描述

### 4.3 一步步配置Logger

`basicConfig`函数提供了一种较为简便的使用日志的方式，如果想要获取更加复杂的使用，则需要自己一步步配置来实现。

**配置逻辑：**

- 一个`logger`对象可以添加多个`handler`对象，通过`addHandler()`函数
- 每个`handler`对象可以有一个`Formatter`对象来指定格式，通过`setFormatter()`函数
- `handler`和`logger`对象都需要设置一个日志等级，通过`setLevel()`函数
- 根据需要`logger`和`handler`对象可以添加多个`Filter`对象，通过`addFilter()`函数

**示例：**

py

复制代码

 `1import logging    2    3logger = logging.getLogger(__name__)    4logger.setLevel(level=logging.INFO)    5    6handler = logging.FileHandler('output.log', mode='a', encoding=None, delay=False)    7formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',    8                                datefmt='%Y-%m-%d %H:%M:%S',    9                                style='%')   10handler.setFormatter(formatter)   11handler.setLevel(logging.DEBUG)   12handler.set_name('output-log')   13   14logger.addHandler(handler)   15   16a=0   17try:   18    res = 100 / a   19except:   20    logger.error('Divisor is equal to 0.', exc_info=True)`

**将日志同时输出到屏幕和文件**

py

复制代码

 `1import logging    2logger = logging.getLogger(__name__)    3logger.setLevel(level = logging.DEBUG)    4handler = logging.FileHandler("log.txt")    5handler.setLevel(logging.INFO)    6formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')    7handler.setFormatter(formatter)    8    9console = logging.StreamHandler()   10console.setLevel(logging.INFO)   11   12logger.addHandler(handler)   13logger.addHandler(console)   14   15logger.info("Start print log")   16logger.debug("Do something")   17logger.warning("Something maybe fail.")   18logger.info("Finish")`

在`log.txt`文件和控制台均可看到输出，控制台的输出，其中文件中内容（有格式）如下：  

![在这里插入图片描述](https://p1-jj.byteimg.com/tos-cn-i-t2oaga2asx/gold-user-assets/2020/1/2/16f658207e6eee73~tplv-t2oaga2asx-jj-mark:3024:0:0:0:q75.png "在这里插入图片描述")

在这里插入图片描述

  
通过这段代码可以看出，`logging`有一个日志处理的主对象(`logger=logging.getLogger()`)，其他的处理方法均是通过`addHandler`添加进去。

### 4.4 通过dictConfig配置

通过`dictConfig`配置方法是通过python代码构建一个`dict`对象，也可以通过`JSON`或`yaml`文件来进行配置。  
这种方式使用起来更加灵活，强大。我们可以把很多的数据转换成自字典形式，然后将他们填充到一个配置字典中。

具体如何转换可以参考`logging.config.py`文件。

#### 4.4.1 dictConfig()

该函数可以从一个字典对象中获取日志配置信息，`config`参数就是这个字典对象。

定义如下：

py

复制代码

`1def dictConfig(config):   2    """Configure logging using a dictionary."""   3    dictConfigClass(config).configure()`

如使用`YAML`格式的文件类配置(配置内容见下方示例)，则使用示例：

py

复制代码

 `1import logging    2import logging.config    3import yaml    4    5with open('logging.yml', 'r') as f_config:    6    dict_cfg = yaml.load(f_config)    7logging.config.dictConfig(dict_cfg)    8    9logger = logging.getLogger('console')   10logger.debug('debug msg')`

#### 4.4.2 配置规则

|key名称|描述|
|---|---|
|`version`|必选项，整数值，表示配置格式版本，当前唯一可用值是`1`|
|`formatters`|可选项，其值是字典对象，该字典对象每个元素的`key`为要定义的格式器名称，`value`为格式器的配置信息组成的`dict`。一般会配置`format`，用于指定输出字符串的格式，`datefmt`用于指定输出的时间字符串格式，默认为`%Y-%m-%d %H:%M:%S`。|
|`filters`|可选项，其值是字典对象，该字典对象每个元素的`key`为要定义的过滤器名称，`value`为过滤器的配置信息组成的`dict`。|
|`handlers`|可选项，其值是字典对象，该字典对象每个元素的`key`为要定义的处理器名称，`value`为处理器的配置信息组成的`dict`。如`class`（必选项）, `formatter`, `filters`。其他配置信息将会传递给`class`所指定的处理器类的构造函数。如使用`logging.handlers.RotatingFileHandler`，使用`maxBytes`, `backupCount`等参数。|
|`loggers`|可选项，其值是字典对象，该字典对象每个元素的`key`为要定义的日志器名称，`value`为日志器的配置信息组成的`dict`。如`level, handler, filter`等|
|`root`|可选项，这是`root logger`的配置项，其值是字典对象。除非在定义其它`logger`时明确指定`propagate`值为no，否则`root logger`定义的`handlers`都会被作用到其它`logger`上。|
|`incremental`|可选项，默认值为`False`。该选项的意义在于，如果这里定义的对象已经存在，那么这里对这些对象的定义是否应用到已存在的对象上。值为`False`表示，已存在的对象将会被重新定义。|

**具体配置结构如下所示：**

- `version`： 必要参数，必须为`1`
    
- `incremental`：是否将此配置文件解释为现有配置的增量, 默认为`False`
    
- `disable_existing_loggers`：是否要禁用现有的非 `root logger`，默认为`True`
    
- `handlers`：字典形式
    
    - `class`：必须有，所使用的`handler`类，如`logging.handlers.RotatingFileHandler`
    - `level`：（可选），`handler`的等级
    - `formatter`：（可选），当前`handler`的`formatter`的`id`
    - `filters`：（可选），当前`handler`的`filters`的`id`列表
- `loggers`：字典形式
    
    - `level`：（可选），`logger`的等级
    - `propagate`：（可选）：默认值为1，表示将消息传递给父`logger`的`handler`进行处理。
    - `filters`：（可选）
    - `handlers`：（可选） ，当前`logger`的`handlers`的`id`列表
    - `qualname`：代码中使用`logging.getLogger()`时，读取的就是`qualname`这个选项。
- `root`：这是`root logger`的配置项
    
    - `level`：日志等级
    - `handlers` ：当前`root logger`的`handlers`的`id`列表

#### 4.4.3 配置示例

yaml

复制代码

 `1version:1    2root:    3    level:DEBUG    4    handlers:[filehandler, ]    5loggers:    6    console:    7        level:WARNING    8        handlers:[consolehandler,]    9        propagate:1   10handlers:   11    filehandler:   12        class:logging.FileHandler   13        filename:logs/sys.log   14        level:WARNING   15        formatter:fileformatter   16    consolehandler:   17        class:logging.StreamHandler   18        stream:ext://sys.stdout   19        level:DEBUG   20        formatter:consoleformatter   21formatters:   22    fileformatter:   23        format:'%(asctime)s [%(name)s][%(levelname)s]：%(message)s'   24    consoleformatter:   25        format:'%(asctime)s[%(levelname)s]:%(message)s'`

> 外部对象访问：外部对象是指不能直接进行访问，需要`import`导入的对象，这时候需要加一个`ext://`前缀以便识别，然后系统就会`import`这个前缀后面的内容。

**参考资料：**  
[Python日志库logging总结-可能是目前为止将logging库总结的最好的一篇文章](https://cloud.tencent.com/developer/article/1354396)  
[python基础学习十 logging模块详细使用【转载】 - louis_w - 博客园](https://www.cnblogs.com/louis-w/p/8567434.html)  
[Python之路(第十七篇)logging模块 - Nicholas- - 博客园](https://www.cnblogs.com/Nicholas0707/p/9021672.html)