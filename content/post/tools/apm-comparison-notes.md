---
title: "APM 监控方案比较笔记"
date: "2024-01-14T17:50:26+08:00"
lastmod: "2024-01-14T17:50:26+08:00"
categories: ["tools"]
slug: "apm-comparison-notes"
draft: false
---

## APM监控



### 一、概念

应用性能管理（Application Performance Management）是一个比较新的网络管理方向，主要指对企业的关键业务应用进行监测、优化，提高企业应用的可靠性和质量，保证用户得到良好的服务，降低IT总拥有成本(TCO)。使用全业务链的敏捷APM监控，可使一个企业的关键业务应用的性能更强大，可以提高竞争力，并取得商业成功，因此，加强应用性能管理（APM）可以产生巨大商业利益。



### 二、开源APM比较

| 方案      | cat                                                       | zipkin                                           | pinpoint                        | skywalking                                            |
| --------- | --------------------------------------------------------- | ------------------------------------------------ | ------------------------------- | ----------------------------------------------------- |
| 依赖      | Java 6 7 8、Maven 3+ MySQL 5.6 5.7、Linux 2.6+ hadoop可选 | Java 6，7，8 Maven3.2+ rabbitMQ                  | Java 6，7，8 maven3+ Hbase0.94+ | Java 6，7，8 maven3.0+ nodejs zookeeper elasticsearch |
| 实现方式  | 代码埋点（拦截器，注解，过滤器等）                        | 拦截请求，发送（HTTP，mq）数据至zipkin服务       | java探针，字节码增强            | java探针，字节码增强                                  |
| 存储      | mysql , hdfs                                              | in-memory ， mysql ， Cassandra ， Elasticsearch | HBase                           | elasticsearch , H2                                    |
| jvm监控   | 不支持                                                    | 不支持                                           | 支持                            | 支持                                                  |
| trace查询 | 支持                                                      | 支持                                             | 需要二次开发                    | 支持                                                  |
| stars     | 12.8k                                                     | 12.5k                                            | 10k                             | 12.4k                                                 |
| 侵入      | 高，需要埋点                                              | 高，需要开发                                     | 低                              | 低                                                    |
| 部署成本  | 中                                                        | 中                                               | 较高                            | 低                                                    |

基于对应用尽可能的低侵入考虑，以上方案选型优先级pinpoint>skywalking>zipkin>cat。




百度百科APM

[https://baike.baidu.com/item/%E5%BA%94%E7%94%A8%E6%80%A7%E8%83%BD%E7%AE%A1%E7%90%86/292984?fromtitle=APM&fromid=2132727](https://baike.baidu.com/item/应用性能管理/292984?fromtitle=APM&fromid=2132727)



维基百科APM(英文版)

https://en.wikipedia.org/wiki/Application_performance_management



skywalking官网文档

https://skywalking.apache.org/zh/blog/2019-03-29-introduction-of-skywalking-and-simple-practice.html



这些应用都是参考google的Dapper方式

http://bigbully.github.io/Dapper-translation/





网易云的APM思考

https://sq.163yun.com/blog/article/168169689970475008

网易云参考资料

https://github.com/naver/pinpoint/blob/master/quickstart/
http://www.jianshu.com/p/37d9bb233936
http://bigbully.github.io/Dapper-translation
https://skyao.gitbooks.io/learning-pinpoint/content/installation/quickstart.html
[Pinpoint v1.5.0 APM 视频介绍](https://www.youtube.com/watch?v=U4EwnB34Dus&feature=youtu.be)






