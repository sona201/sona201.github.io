---
title: "Django as_view 方法实现分析"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["django"]
tags: ["django", "CBV", "as_view"]
draft: false
---

# django的as_view方法实现分析

## 框架概念 MVC/MTV
django 是一个MVC(MTV)框架，官方定义是 MTV，但本质上其实是一样的，[官方解释](https://docs.djangoproject.com/en/4.2/faq/general/#django-appears-to-be-a-mvc-framework-but-you-call-the-controller-the-view-and-the-view-the-template-how-come-you-don-t-use-the-standard-names)

了解下 MTV/MVC 不同的含义
MVC 是 Model-View-Controller 的缩写，其中每个单词都有其不同的含义：
- Modle 代表数据存储层，是对数据表的定义和数据的增删改查；
- View 代表视图层，是系统前端显示部分，它负责显示什么和如何进行显示；
- Controller 代表控制层，负责根据从 View 层输入的指令来检索 Model 层的数据，并在该层编写代码产生结果并输出。

Django 借鉴了经典的 MVC 模式，它也将交互的过程分为了 3 个层次，也就是 MTV 设计模式；
- Model：数据存储层，处理所有数据相关的业务，和数据库进行交互，并提供数据的增删改查；
- Template：模板层（也叫表现层）具体来处理页面的显示；
- View：业务逻辑层，处理具体的业务逻辑，它的作用是连通Model 层和 Template 。

## 框架使用方式 CBV/FBV
Django有两种视图方式CBV以及FBV
- FBV 基于函数的视图 Function Based Views
- CBV 基于类的视图 Class Based Views

[class-based-views](https://docs.djangoproject.com/en/4.2/ref/class-based-views/) \
[相关名词解释链接](https://medium.com/@ksarthak4ever/django-class-based-views-vs-function-based-view-e74b47b2e41b) \
[class-based-views/base](https://docs.djangoproject.com/en/4.2/ref/class-based-views/base/)

### FBV视图样例

```python
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Choice, Question


# ...
def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(
            request,
            "polls/detail.html",
            {
                "question": question,
                "error_message": "You didn't select a choice.",
            },
        )
    else:
        selected_choice.votes += 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse("polls:results", args=(question.id,)))
```
这种方式非常简单，感觉就像初学者在那里学习python，糊弄下搞个函数处理，所以感觉没有成就感，CBV 虽然本质上跟FBV一样，但看起来高大上

### CBV视图样例

```python
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

from .models import Choice, Question


class IndexView(generic.ListView):
    template_name = "polls/index.html"
    context_object_name = "latest_question_list"

    def get_queryset(self):
        """Return the last five published questions."""
        return Question.objects.order_by("-pub_date")[:5]


class DetailView(generic.DetailView):
    model = Question
    template_name = "polls/detail.html"


class ResultsView(generic.DetailView):
    model = Question
    template_name = "polls/results.html"


def vote(request, question_id):
    ...  # same as above, no changes needed.
```

下面就是讲解django CBV的相关原理

django的类视图拥有自动查找指定方法的功能, 通过调用是通过as_view()方法实现

> urls.py

```python
from meduo_mall.demo import views

urlpatterns = [
    url(r'register/$', views.Demo.as_view())
]
```

> views.py

```python
from django.views.generic import View


class Demo(View):

    def get(self, request):
        return HttpResponse('get page')

    def post(self, request):
        return HttpResponse('post page')
```

为什么as_view能自动匹配指定的方法,

先看源码

```python
    @classonlymethod
    def as_view(cls, **initkwargs):  # 实际上是一个闭包  返回 view函数
        """
        Main entry point for a request-response process.
        """
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
              # path('test_class_view/', TestClassView.as_view(test_key='hh'), name='cbv')
              # 当as_view() 视图中有key值传递时，需要再类中定义属性，否则将启动报错
                raise TypeError("%s() received an invalid keyword %r. as_view "
                                "only accepts arguments that are already "
                                "attributes of the class." % (cls.__name__, key))

        def view(request, *args, **kwargs):  # 作用：增加属性， 调用dispatch方法 
            self = cls(**initkwargs)  # 创建一个 cls 的实例对象， cls 是调用这个方法的 类（Demo）
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request  # 为对象增加 request， args， kwargs 三个属性
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)  # 找到指定的请求方法， 并调用它
        view.view_class = cls  # 在函数体内部不能给函数增加属性，在函数定义完成之后，可以给函数增加属性
        view.view_initkwargs = initkwargs

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        if request.method.lower() in self.http_method_names:  # 判断请求的方法类视图是否拥有， http_method_names=['get', 'post']
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)  # 如果存在 取出该方法
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)  # 执行该方法
```

简化版
```python
    @classonlymethod
    def as_view(cls, **initkwargs):  # 实际上是一个闭包  返回 view函数
        """
        Main entry point for a request-response process.
        """
        def view(request, *args, **kwargs):  # 作用：增加属性， 调用dispatch方法 
            self = cls(**initkwargs)  # 创建一个 cls 的实例对象， cls 是调用这个方法的 类（Demo）
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request  # 为对象增加 request， args， kwargs 三个属性
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)  # 找到指定的请求方法， 并调用它

        return view

    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        if request.method.lower() in self.http_method_names:  # 判断请求的方法类视图是否拥有， http_method_names=['get', 'post']
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)  # 如果存在 取出该方法
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)  # 返回该请求方法执行的结果
```

再简化

```python
def as_view(): # 校验 + 返回view方法
    # 一些校验
    ...
    def view(): # 执行视图
        # 增加 为对象request, args, kwargs 属性
        ...
        return dispatch() # 调用指定的请求方法
    return view

def dispatch(): # 真正的查找指定的方法, 并调用该方法
    ...
    return handler()
```

调用顺序: as_view --> view --> dispatch
- 可以看出as_view实际上是一个闭包, 它的作用做一些校验工作, 再返回view方法.
- 而view方法的作用是给请求对象补充三个参数, 并调用 dispatch方法处理
- dispatch方法查找到指定的请求方法, 并执行

可以得出结论: 实际上真正实现查找的方法是 dispatch方法

### 参考链接
[django的as_view方法实现分析](https://www.cnblogs.com/ellisonzhang/p/10668486.html)

[functools](https://docs.python.org/zh-tw/3.9/library/functools.html)

我们django中写CBV的时候继承的是View，rest_framework继承的是APIView
我们django中写CBV的时候继承的是View，rest_framework继承的是APIView，那么他们两个有什么不同呢~~~

urlpatterns = [
    url(r'^book$', BookView.as_view()),
    url(r'^book/(?P<id>\d+)$', BookEditView.as_view()),
]
我们可以看到，不管是View还是APIView最开始调用的都是as_view()方法 那我们走进源码看看

我们能看到，APIView继承了View, 并且执行了View中的as_view()方法，最后把view返回了，用csrf_exempt()方法包裹后去掉了csrf的认证。

那我们看看View中的as_view()方法做了什么

我们看到了~在View中的as_view方法返回了view函数，而view函数执行了self.dispatch()方法~~但是这里的dispatch方法应该是我们APIView中的

我们去initialize_request中看下把什么赋值给了request，并且赋值给了self.request, 也就是我们在视图中用的request.xxx到底是什么

我们看到，这个方法返回的是Request这个类的实例对象~~我们注意我们看下这个Request类中的第一个参数request，是我们走我们django的时候的原来的request~

我们看到了，这个Request类把原来的request赋值给了self._request, 也就是说以后_request是我们老的request，新的request是我们这个Request类~~

那我们继承APIView之后请求来的数据都在哪呢~~