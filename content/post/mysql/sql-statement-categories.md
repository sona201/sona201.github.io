---
title: "SQL 语句分类学习笔记"
date: "2024-04-24T14:16:49+08:00"
lastmod: "2024-04-24T14:16:49+08:00"
categories: ["mysql"]
slug: "sql-statement-categories"
draft: false
---

## sql

[sql分类](https://www.jb51.net/article/271374.htm)

SQSQL（Structured Query Language）是用于管理和操作关系型数据库的语言。根据功能和用途，SQL语法可以分为以下几个主要分类：

- 数据定义语言（DDL）：DDL用于定义和管理数据库对象，例如表、视图、索引等。常见的DDL语句包括CREATE（创建数据库对象）、ALTER（修改数据库对象）和DROP（删除数据库对象）等。
- 数据操作语言（DML）：DML用于对数据库中的数据进行操作，例如插入、更新和删除数据。常见的DML语句包括SELECT（查询数据）、INSERT（插入数据）、UPDATE（更新数据）和DELETE（删除数据）等。
- 数据查询语言（DQL）：DQL用于从数据库中查询数据。最常见的DQL语句是SELECT，它允许你指定要检索的数据、条件和排序等。
- 数据控制语言（DCL）：DCL用于控制数据库的访问权限和事务处理。常见的DCL语句包括GRANT（授权访问权限）、REVOKE（撤销访问权限）和COMMIT（提交事务）等。
- 事务控制语言（TCL）：TCL用于管理数据库中的事务。常见的TCL语句包括BEGIN（开始事务）、COMMIT（提交事务）和ROLLBACK（回滚事务）等。

这些分类涵盖了SQL语言的主要方面，每个分类都有特定的语法和用途。根据具体的需求，你可以选择适当的SQL语句来执行相应的操作。

### SQL四部分
(1)数据定义。(SQL DDL)用于定义SQL模式、基本表、视图和索引的创建和撤消操作。
(2)数据操纵。(SQL DML)数据操纵分成数据查询和数据更新两类。数据更新又分成插入、删除、和修改三种操作。
(3)数据控制。包括对基本表和视图的授权，完整性规则的描述，事务控制等内容。
(4)嵌入式SQL的使用规定。涉及到SQL语句嵌入在宿主语言程序中使用的规则。

1.DDL(Data Definition Language)数据库定义语言statements are used to define the database structure or schema.

DDL是SQL语言的四大功能之一。
用于定义数据库的三级结构，包括外模式、概念模式、内模式及其相互之间的映像，定义数据的完整性、安全控制等约束。
DDL不需要commit.
- CREATE
- ALTER
- DROP
- TRUNCATE
- COMMENT
- RENAME

2.DML(Data Manipulation Language)数据操纵语言statements are used for managing data within schema objects.

由DBMS提供，用于让用户或程序员使用，实现对数据库中数据的操作。
DML分成交互型DML和嵌入型DML两类。
依据语言的级别，DML又可分成过程性DML和非过程性DML两种。
需要commit.
- SELECT
- INSERT
- UPDATE
- DELETE
- MERGE
- CALL
- EXPLAIN PLAN
- LOCK TABLE

3.DCL(Data Control Language)数据库控制语言  授权，角色控制等
- GRANT 授权
- REVOKE 取消授权

4.TCL(Transaction Control Language)事务控制语言
- SAVEPOINT 设置保存点
- ROLLBACK  回滚
- SET TRANSACTION