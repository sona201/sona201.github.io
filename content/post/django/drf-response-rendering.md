---
title: "DRF finalize_response 与渲染器配置"
date: "2023-10-25T00:42:03+08:00"
lastmod: "2023-10-25T00:42:03+08:00"
categories: ["django"]
slug: "drf-response-rendering"
draft: false
---

## drf渲染模块源码分析

[原文链接](https://blog.51cto.com/u_15183212/2970460)

搜了好多源码文章，都只是简单介绍 drf 的 rest_framework.response.Response 方法，这块的源码虽然没有完全读懂，但是也看了大概，感觉没有讲到点子上
都没有跟 DEFAULT_RENDERER_CLASSES 这个关联起来。

前言
渲染模块的原理和解析模块是一样，drf默认的渲染有2种方式，一种是json格式，另一种是模板方式。

渲染模块源码入口
入口：APIView类中dispatch方法中的：self.response = self.finalize_response(request, response, *args, **kwargs)

渲染模块源码分析
我们首先点击finalize_response进入查看源码

```python
    def finalize_response(self, request, response, *args, **kwargs):
        """
        Returns the final response object.
        """
        # 断言是否是HttpResponseBase对象
        # Make the error obvious if a proper response is not returned
        assert isinstance(response, HttpResponseBase), (
            'Expected a `Response`, `HttpResponse` or `HttpStreamingResponse` '
            'to be returned from the view, but received a `%s`'
            % type(response)
        )
        # 判断是否是Response对象
        if isinstance(response, Response):
            if not getattr(request, 'accepted_renderer', None):
                neg = self.perform_content_negotiation(request, force=True)
                request.accepted_renderer, request.accepted_media_type = neg

            response.accepted_renderer = request.accepted_renderer
            response.accepted_media_type = request.accepted_media_type
            response.renderer_context = self.get_renderer_context()

        # Add new vary headers to the response instead of overwriting.
        vary_headers = self.headers.pop('Vary', None)
        if vary_headers is not None:
            patch_vary_headers(response, cc_delim_re.split(vary_headers))

        for key, value in self.headers.items():
            response[key] = value

        return response
```

上述代码是响应模块的源码，该源码中包含了渲染模块的源码，就是这句neg = self.perform_content_negotiation(request, force=True)，我们可以点击查看

```python
    def perform_content_negotiation(self, request, force=False):
        """
        Determine which renderer and media type to use render the response.
        """
        # 确定使用哪种渲染器和媒体类型来渲染响应。
        # 渲染器列表
        renderers = self.get_renderers()
        conneg = self.get_content_negotiator()

        try:
            return conneg.select_renderer(request, renderers, self.format_kwarg)
        except Exception:
            if force:
                return (renderers[0], renderers[0].media_type)
            raise
```

代码中有个get_renderers就是渲染器列表，点击查看

```python
    def get_renderers(self):
        """
        Instantiates and returns the list of renderers that this view can use.
        """
        return [renderer() for renderer in self.renderer_classes]
```

这就是渲染器列表的源码，跟解析器列表的源码大同小异，接着再点击renderer_classer查看

```python
renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
```

到这里我们就知道了，drf默认的渲染器在settings下的DEFAUIT_RENDERER_CLASSES中，配置如下

```python
DEFAULTS = {
    # Base API policies
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ],
}
```

如果我们想局部配置渲染器，只需在自己定义的视图类中添加render_classes 即可，一般也不用做修改，以上分析只是让大家知道drf是怎么配置渲染器的，这样以后我们自定义渲染器也就十分简单了

参考
https://cloud.tencent.com/developer/article/2114529