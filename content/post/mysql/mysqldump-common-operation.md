---
title: "mysqldump 常用操作"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["mysql"]
tags: ["mysql", "mysqldump", "backup"]
draft: false
---

#mysql #sql #mysqldump

命令和输出已脱敏，名称与地址为示例。示例使用 `example_db`、`example_table`、`app_user` 和 `192.0.2.10`；`-p` 后不附密码，执行时按提示输入。

## mysqldump

### mysqldump 5.7

#### 1. 导出表结构和表数据

```sh
mysqldump -h 192.0.2.10 -u app_user -p example_db example_table > example_table.sql
```

#### 2. 导出整个数据库结构和数据

```sh
mysqldump -h 192.0.2.10 -u app_user -p example_db > example_db.sql
```

#### 3. 导出单个数据表结构和数据

```sh
mysqldump -h 192.0.2.10 -u app_user -p example_db example_table > example_table.sql
```

#### 4. 导出整个数据库结构（不包含数据）

```sh
mysqldump -h 192.0.2.10 -u app_user -p --no-data example_db > example_schema.sql
```

#### 5. 导出单个数据表结构（不包含数据）

```sh
mysqldump -h 192.0.2.10 -u app_user -p --no-data example_db example_table > example_table_schema.sql
```

#### 6. 备份导出数据时排除某张表

使用 `--ignore-table=数据库名.表名`；每张需要排除的表各写一个参数。

```sh
mysqldump -h 192.0.2.10 -u app_user -p example_db \
  --ignore-table=example_db.example_log > example_db.sql
```

### mysqldump 8.0

使用 8.0 客户端导出不支持列统计查询的旧版本服务端时，可以指定 `--column-statistics=0`。

```sh
mysqldump --column-statistics=0 -h 192.0.2.10 -u app_user -p example_db \
  --ignore-table=example_db.example_log \
  --ignore-table=example_db.example_cache > example_db.sql
```

下面保留一个参数组合示例；实际使用时根据表引擎和恢复要求选择参数。

```sh
mysqldump -h 192.0.2.10 -u app_user -p \
  --single-transaction --set-gtid-purged=OFF --add-drop-table \
  --databases example_db > example_db.sql
```

`--databases` 会在导出文件中包含创建和选择数据库的语句。下面是经过缩减的示例片段，不是完整备份文件：

```sql
-- Host: 192.0.2.10    Database: example_db
-- Current Database: `example_db`
CREATE DATABASE /*!32312 IF NOT EXISTS*/ `example_db` /*!40100 DEFAULT CHARACTER SET latin1 */;
USE `example_db`;

-- Table structure for table `example_table`
DROP TABLE IF EXISTS `example_table`;
CREATE TABLE `example_table` (
  `id` int NOT NULL,
  PRIMARY KEY (`id`)
);
```

这条 `CREATE DATABASE` 语句中：

- `example_db` 是示例数据库名。
- `/*!32312 IF NOT EXISTS*/` 是 MySQL 条件注释；MySQL 3.23.12 及以上版本会执行其中的 `IF NOT EXISTS`。
- `/*!40100 DEFAULT CHARACTER SET latin1 */` 在 MySQL 4.1.0 及以上版本指定默认字符集。这里保留 `latin1` 仅用于解释原命令结构，实际字符集应与需要恢复的数据库一致。

如果数据库已经存在，`IF NOT EXISTS` 会避免再次创建；它不会把已有库的字符集改成示例值。
