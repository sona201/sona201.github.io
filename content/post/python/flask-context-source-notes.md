---
title: "Flask 上下文与 LocalProxy 学习笔记"
date: "2021-01-10T00:51:58+08:00"
lastmod: "2021-01-10T00:51:58+08:00"
categories: ["python"]
slug: "flask-context-source-notes"
draft: false
---

#### Flask 上下文管理

内容回顾:

		1. Linux命令
  		2. 面向对象： 特殊方法
         		
         		1. `obj['x'] = 123`
         		2. `obj.x = 123`
         		3. `obj + 123`

3. functools

   ```python
   def func(a1, a2, a3):
   		return a1 + a2 + a3
   
   v1 = func(1, 2, 3)
   
   new_func = functions.partial(func, 111, 2)
   new_func(3)
   ```

4. 你认识的装饰器？应用场景？

   - 应用：
     - flask：路由、before_request
     - django： csrf、缓存、用户登录

5. Flask









1. threading.local(跟flask 没有关系)
   1. 
2. 上下文管理
3. 数据库连接池



\r\n

请求分开

把 \r\n 分开

request  wsgi  把原生字符串进行分割



![wsgi](/images/wsgi%E8%AF%B7%E6%B1%82.png)



 

2. 在源码中分析上下文管理
   1. 第一阶段:  将ctx(request, session)放到地上（local对象）
   2. 第二阶段:  视图函数导入:  request/session
   3. 第三阶段:  请求处理完毕
      - 获取session并保存到cookies
      - 将ctx删除



![requestContext](/images/requestContext1.png)



![requestContext2](/images/requestContext2.png)

1. 在LocalProxy 中有各种python 双下划线用法

2.   

   ```python
   request = LocalProxy(partial(_lookup_req_object, "request"))
   session = LocalProxy(partial(_lookup_req_object, "session"))
   # partial 表示简约传参的方式，省略传参，不需要传入所有值
   # _lookup_req_object 对象方法，反射  getattr 方法
   ```



![requestContext3](/images/requestContext3.png)



> 视图函数引入包，LocalProxy代理，_loopup_req_object 反代，最后到localstack中的local找到对应的内容进行操作



