---
title: "使用 STS 临时授权直接上传 OSS"
date: "2023-11-12T16:13:51+08:00"
lastmod: "2023-11-12T16:13:51+08:00"
categories: ["python"]
slug: "oss-sts-direct-upload"
draft: false
---

## oss 文件上传

## oss 本地文件上传方案

### 背景

自己写了一个服务需要文件上传功能，但会遇到文件很大的情况，也经常遇到文件上传到一半突然断掉，这让我很烦恼，服务器很难排查问题，甚至远程用户的电脑完全复现却还是不能定位问题，于是想到 oss 本地文件直接上传到阿里云的 oss 服务器，能节保证文件上传的稳定性。

下面是阿里云提供的方案调用图

这个方案的实施背景依赖阿里云的API，阿里云提供了一个sts token方案。可以做临时授权，这样才能做到前端上传，且不用把账号密码写到前端代码里

![oss_token](/images/oss_token.jpeg)

[使用STS临时访问凭证访问OSS官方文档链接](https://help.aliyun.com/zh/oss/developer-reference/use-temporary-access-credentials-provided-by-sts-to-access-oss?spm=a2c4g.11174283.0.i8#p-osc-r0m-u63)

> 流程分析

1. 步骤一：创建RAM用户
2. 步骤二：为RAM用户授予请求AssumeRole的权限
3. 步骤三：创建用于获取临时访问凭证的角色
4. 步骤四：为角色授予上传文件的权限
5. 步骤五：获取临时访问凭证
6. 步骤六：使用临时访问凭证上传文件至OSS


### sts生成本地临时token

> 通过阿里云sts sdk获取临时token，附加时效、文件名限制

[获取扮演角色的临时身份凭证 通过调用AssumeRole接口，获取一个扮演RAM角色的临时身份凭证（STS Token）](https://next.api.aliyun.com/api/Sts/2015-04-01/AssumeRole?spm=a2c4g.11186623.0.0.2f04497bbVcwVB&sdkStyle=dara&tab=DEMO&lang=PYTHON)

下面是我自己封装的代码

```python
import logging

from alibabacloud_sts20150401.client import Client as Sts20150401Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_sts20150401 import models as sts_20150401_models
from alibabacloud_tea_util import models as util_models

logger = logging.getLogger(__name__)


class StsTokenGenerate:
    """
    aliyun sts 接口，通用封装
    endpoint 默认为北京
    duration_seconds 最低值为15min/1hr
    policy='{"Statement": [{"Action": ["*"],"Effect": "Allow","Resource": ["*"]}],"Version":"1"}'
    """

    @staticmethod
    def get_sts_token(access_key_id, access_key_secret, role_arn, session_name, sts_policy=None, duration_seconds=900,
                      endpoint='sts.cn-beijing.aliyuncs.com'):
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret
        )
        config.endpoint = endpoint
        client = Sts20150401Client(config)
        request_params = {
            'role_arn': role_arn,
            'role_session_name': session_name,
            'duration_seconds': duration_seconds
        }
        if sts_policy:
            request_params['policy'] = sts_policy
        assume_role_request = sts_20150401_models.AssumeRoleRequest(**request_params)
        runtime = util_models.RuntimeOptions()
        return client.assume_role_with_options(assume_role_request, runtime).to_map().get('body')

```

[RAM角色和STS Token常见问题](https://help.aliyun.com/zh/ram/support/faq-about-ram-roles-and-sts-tokens)

### 前端使用oss sdk上传

> 通过阿里云sts sdk获取临时token，附加时效、文件名限制

[Node.js oss 文件 分片上传](https://help.aliyun.com/zh/oss/developer-reference/multipart-upload-3?spm=a2c4g.11186623.0.0.2d0c71bfp10eKx)

下面是使用 vue 封装代码，包括自动生成 MD5 码，异步逻辑处理，回调等问题

```vue
    importFile(file, fileList) {
      // 由于文件过大时会导致页面崩溃，放弃改方案
      // https://github.com/forsigner/browser-md5-file
      // 浏览器获取文件 md5 值
      // https://juejin.cn/post/7023763648833126408
      // MD5的实现方式
      var objFile = file.raw
      const bmf = new BMF()
      //  const el = document.getElementById('upload');
      //  el.addEventListener('change', handle, false);//VUE使用这个会报错
      bmf.md5(
        objFile,
        (err, md5) => {
          if (err) {
            console.log('err:', err)
          }
          this.uploadForm.file_md5 = md5
        },
        progress => {
          if (progress === 1) {
            console.log('md5 生成完成')
          }
        }
      )
    },
    async uploadFile(file) {
      if (!(this.uploadForm.remote_ip && this.uploadForm.file_desc)) {
        this.$message({
          message: '请选择服务器ip或备注信息',
          type: 'warning'
        })
        return
      }
      const now = new Date()
      const currentTime = now.getFullYear().toString() + (now.getMonth() + 1) + now.getDate() + now.getMinutes() + now.getHours() + now.getSeconds()
      this.uploadForm.file_path = 'file/' + currentTime + '_' + file.file.name

      // 获取oss文件上传token
      let res
      try {
        res = await getUploadStsToken({
          'file_path': this.uploadForm.file_path
        })
        this.loading = true
        this.Loading = true
      } catch (error) {
        console.log('upload', error)
        this.$message({
          message: '文件大小超出限制,请重新选择',
          type: 'warning'
        })
        return
      }
      const credentials = res.data
      // 如需保存应用元数据，可在上传成功后单独处理。

      const OSS = require('ali-oss')
      const client = new OSS({
        region: 'oss-' + credentials.region,
        accessKeyId: credentials.AccessKeyId,
        accessKeySecret: credentials.AccessKeySecret,
        stsToken: credentials.SecurityToken,
        bucket: credentials.bucket
      })

      const progress = async(p, _checkpoint) => {
        this.percentage = Math.floor(p * 100)
        console.log(this.percentage)
        if (this.percentage === 100) {
          this.fileList = []
          this.loading = false
          this.Loading = false
        }
      }

      try {
        this.uploadForm.file_name = file.file.name
        this.uploadForm.file_size = file.file.size
        client.multipartUpload(this.uploadForm.file_path, file.file, { progress }).catch(e => {
          this.loading = false
          this.Loading = false
          console.log('文件上传oss异常 multipartUpload' + e)
          this.$notify.error({
            title: '错误',
            message: '文件上传oss异常'
          })
        })
      } catch (e) {
        console.log('文件上传oss异常' + e)
        this.loading = false
        this.Loading = false
        this.$notify.error({
          title: '错误',
          message: '文件上传oss异常'
        })
      }
    },
```

