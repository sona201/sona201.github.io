---
title: "DRF 视图从 APIView 到通用视图的封装"
date: "2020-11-28T17:16:52+08:00"
lastmod: "2020-11-28T17:16:52+08:00"
categories: ["django"]
slug: "drf-generic-view-refactoring-notes"
draft: false
---

### restful view 视图处理

第一次封装

```python

"""
APIView视图
使用 APIView 的写法
两个类，5个视图函数

get(所有的数据)
create 创建数据
get(单条数据)
patch/put(修改单条数据)
delete(删除单条数据)

"""
class BookView(APIView):

    def get(self, request):
        query_set = Book.objects.all()
        book_ser = BookSerializer(query_set, many=True)
        return Response(book_ser.data)

    def post(self, request):
        query_set = request.data
        book_ser = BookSerializer(data=query_set)
        if book_ser.is_valid():
            book_ser.save()
            return Response(book_ser.validated_data)
        else:
            return Response(book_ser.errors)


class BookEditView(APIView):

    def get(self, request, id):
        query_set = Book.objects.filter(id=id).first()
        book_ser = BookSerializer(query_set)
        return Response(book_ser.data)

    def patch(self, request, id):
        query_set = Book.objects.filter(id=id).first()
        book_ser = BookSerializer(query_set, data=request.data, partial=True)
        if book_ser.is_valid():
            book_ser.save()
            return Response(book_ser.validated_data)
        else:
            return Response(book_ser.errors)

    def delete(self, request, id):
        query_set = Book.objects.filter(id=id).first()
        if query_set:
            query_set.delete()
            return Response("")
        else:
            return Response("删除的书籍不存在")


```


```python
"""
根据上面的，提取两个类方法中的公共内容，然后将几个方法各自抽出
两个类，5个视图函数中，都有queryset和serializer，所以可以提取出来
然后5个对应的方法单独写自己的功能

get -> ListModelMixin
create -> CreateModelMixin
get -> RetrieveModelMixin
patch/put -> UpdateModelMixin
delete -> DestroyModelMixin
"""
class GenericAPIView(APIView):
    queryset = None
    serializer_class = None

    def get_queryset(self):
        return self.queryset.all()

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)


class ListModelMixin(object):
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CreateModelMixin(object):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.validated_data)
        else:
            return Response(serializer.errors)


class RetrieveModelMixin(object):
    def retrieve(self, request, id, *args, **kwargs):
        book_obj = self.get_queryset().filter(pk=id).first()
        book_ser = self.get_serializer(book_obj)
        return Response(book_ser.data)


class UpdateModelMixin(object):
    def update(self, request, id, *args, **kwargs):
        book_obj = self.get_queryset().filter(pk=id).first()
        book_ser = self.get_serializer(book_obj, data=request.data, partial=True)
        if book_ser.is_valid():
            book_ser.save()
            return Response(book_ser.validated_data)
        else:
            return Response(book_ser.errors)


class DestroyModelMixin(object):
    def destroy(self, request, id, *args, **kwargs):
        queryset = self.get_queryset()
        try:
            queryset.get(pk=id).delete()
            return Response("")
        except Exception as e:
            return Response("信息有误")

```


```
# 我们把公共的部分抽出来 这样不管写多少表的增删改查都变的很简单
# 这样封装后我们的视图会变成这样

"""
需要自己写get post 等方法，没有太大意义，且有点繁琐
"""
class BookView(GenericAPIView, ListModelMixin, CreateModelMixin):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class BookEditView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get(self, request, id, *args, **kwargs):
        return self.retrieve(request, id, *args, **kwargs)

    def patch(self, request, id, *args, **kwargs):
        return self.update(request, id, *args, **kwargs)

    def destroy(self, request, id, *args, **kwargs):
        return self.delete(request, id, *args, **kwargs)
```


所以再加一层封装， 把这几个get post patch 方法帮你写好，就是普通的返回，免去无意义的 CV

在 generics.py 模块下面的 xxxAPIView,都有写好，直接继承即可

下面是源码中的几个模块，复制过来看看，就是帮你写了return


```python
class CreateAPIView(mixins.CreateModelMixin,
                    GenericAPIView):
    """
    Concrete view for creating a model instance.
    """
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class ListAPIView(mixins.ListModelMixin,
                  GenericAPIView):
    """
    Concrete view for listing a queryset.
    """
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RetrieveAPIView(mixins.RetrieveModelMixin,
                      GenericAPIView):
    """
    Concrete view for retrieving a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class DestroyAPIView(mixins.DestroyModelMixin,
                     GenericAPIView):
    """
    Concrete view for deleting a model instance.
    """
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class UpdateAPIView(mixins.UpdateModelMixin,
                    GenericAPIView):
    """
    Concrete view for updating a model instance.
    """
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class ListCreateAPIView(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        GenericAPIView):
    """
    Concrete view for listing a queryset or creating a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class RetrieveUpdateAPIView(mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            GenericAPIView):
    """
    Concrete view for retrieving, updating a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
```

最后的封装，就是讲url再高度集成，但大多情况不需要，除非无脑的 CRUD ,要加上业务逻辑只能自己写

##### 所以个人角度总结

```
CreateAPIView
ListAPIView
RetrieveAPIView
DestroyAPIView
UpdateAPIView
ListCreateAPIView
RetrieveUpdateAPIView
RetrieveDestroyAPIView
RetrieveUpdateDestroyAPIView
```

然后根据业务逻辑自己再重写相应的方法