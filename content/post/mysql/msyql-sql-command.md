---
title: "MySQL SQL 常用命令"
description: "从个人笔记仓库整理迁移"
date: "2026-10-03T22:00:00+08:00"
lastmod: "2026-10-03T22:00:00+08:00"
categories: ["mysql"]
tags: ["mysql", "sql", "command"]
draft: false
---

#sql #mysql #command

命令和输出已脱敏，名称与地址为示例。库表名统一使用 `example_db`、`example_table`，业务账号使用 `app_user`；`192.0.2.x` 是示例地址。`<new-password>` 只表示需要自行替换的密码占位，不是实际密码。

## 1 库表结构操作

### 1.1 建库

#### 1.1.1 DDL 创建数据库并设置字符集

```sql
CREATE DATABASE `example_db` CHARACTER SET utf8mb4;
CREATE DATABASE IF NOT EXISTS `example_db`;
```

| 字符集 | 说明 |
| --- | --- |
| gbk | 中文字符集 |
| utf8（utf8mb3） | 最多使用 3 个字节，不能表示全部 Unicode 字符 |
| latin1 | 单字节字符集 |
| utf8mb4 | 最多使用 4 个字节，可以表示完整 Unicode 字符范围 |

#### 1.1.2 DDL 删库

```sql
DROP DATABASE `example_db`;
```

#### 查询当前用户权限

```sql
SHOW GRANTS;
```

#### 删除权限

```sql
REVOKE SELECT, INSERT, UPDATE, DELETE
ON `example_db`.`example_table` FROM 'app_user'@'192.0.2.20';
```

### MySQL 8.0 创建用户

```sql
CREATE USER 'app_user'@'192.0.2.20' IDENTIFIED BY '<new-password>';
```

### 给用户赋权

```sql
-- 数据库粒度
GRANT SELECT, INSERT, UPDATE, DELETE
ON `example_db`.* TO 'app_user'@'192.0.2.20';

-- 表粒度；为不同的表分别执行授权语句
GRANT SELECT ON `example_db`.`example_table` TO 'app_user'@'192.0.2.20';
GRANT SELECT ON `example_db`.`example_archive` TO 'app_user'@'192.0.2.20';
```

#### 查询用户与权限

```sql
SELECT User, Host FROM mysql.user;
SHOW GRANTS FOR 'app_user'@'192.0.2.20';
SELECT USER();
```

#### 刷新权限

```sql
FLUSH PRIVILEGES;
```

#### 删除用户

```sql
DROP USER 'app_user'@'192.0.2.20';
```

#### 修改用户密码（登录状态）

```sql
ALTER USER 'app_user'@'192.0.2.20' IDENTIFIED BY '<new-password>';
```

### 1.2 数据库表的增删改查

#### 1.2.1 DDL 新增表

```sql
CREATE TABLE `example_db`.`example_table` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL DEFAULT '' COMMENT '示例名称',
  `status` int NOT NULL DEFAULT 0 COMMENT '示例状态',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.2.2 DDL 删除表

```sql
-- 直接删除表
DROP TABLE `example_db`.`example_table`;

-- 先检查是否存在
DROP TABLE IF EXISTS `example_db`.`example_table`;
```

#### 1.2.3 DDL 新增字段并指定位置

```sql
ALTER TABLE `example_db`.`example_table`
ADD `description` varchar(255) NOT NULL DEFAULT '' COMMENT '示例说明'
AFTER `name`;
```

#### 1.2.4 DDL 修改字段

```sql
-- 修改字段名称和定义
ALTER TABLE `example_db`.`example_table`
CHANGE `description` `example_text` varchar(500) NOT NULL DEFAULT '';

-- 修改字段类型或长度
ALTER TABLE `example_db`.`example_table`
MODIFY `example_text` varchar(1000) NOT NULL DEFAULT '';
```

#### 修改字段顺序

```sql
ALTER TABLE `example_db`.`example_table`
MODIFY `status` int NOT NULL DEFAULT 0 AFTER `name`;
```

#### 修改自增 ID 起始值

```sql
ALTER TABLE `example_db`.`example_table` AUTO_INCREMENT=100;
```

也可以在建表时指定：

```sql
CREATE TABLE `example_db`.`example_archive` (
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=100 DEFAULT CHARSET=utf8mb4;
```

#### 查看建表语句

```sql
SHOW CREATE TABLE `example_db`.`example_table`;
```

#### 1.2.5 DDL 删除字段

```sql
ALTER TABLE `example_db`.`example_table` DROP `example_text`;
```

#### 1.2.6 DDL 新增索引

```sql
ALTER TABLE `example_db`.`example_table`
ADD UNIQUE INDEX `example_name_status_idx` (`name`, `status`);

ALTER TABLE `example_db`.`example_table`
ADD INDEX `example_created_idx` (`created_at`) USING BTREE;
```

#### 1.2.7 DDL 删除索引

```sql
ALTER TABLE `example_db`.`example_table`
DROP INDEX `example_name_status_idx`;
```

#### 设置自动提交

```sql
SET autocommit=0;
```

### 表数据的增删改查

以下语句分别展示操作形式，不是需要从上到下连续执行的脚本。

#### DML 插入数据

```sql
INSERT INTO `example_db`.`example_table` (`name`, `status`)
VALUES ('example_a', 0), ('example_b', 1);
```

#### DML 删除数据

```sql
DELETE FROM `example_db`.`example_table` WHERE `id`=1;
```

#### DML 清空表数据

```sql
TRUNCATE TABLE `example_db`.`example_table`;
```

#### DML 更新数据

```sql
UPDATE `example_db`.`example_table`
SET `status`=1, `name`='example_c' WHERE `id`=2;
```

#### DML 查询数据

```sql
SELECT * FROM `example_db`.`example_table` WHERE `status`=1;
```

#### DML 跳过前 10 行后查询 5 行

```sql
SELECT * FROM `example_db`.`example_table` ORDER BY `id` LIMIT 10, 5;
```

### SQL 其他操作

#### 手动导入 SQL

```sh
mysql -h 192.0.2.10 -P 3306 -u app_user -p example_db < example_db.sql
```

`-p` 后不附密码，按提示输入。也可以进入 MySQL 客户端后执行：

```sql
SOURCE /path/to/example_db.sql;
```

#### 查看慢查询时间设置，单位为秒

```sql
SHOW VARIABLES LIKE 'long_query_time';
```

#### 查询存储过程创建语句

```sql
SHOW CREATE PROCEDURE `example_db`.`example_procedure`;
```

#### 查看主从复制信息

查看主库状态：

```sql
SHOW MASTER STATUS;
```

缩减后的示例输出：

```text
File: mysql-bin.000001
Position: 154
Binlog_Do_DB: example_db
Binlog_Ignore_DB:
```

查看从库状态：

```sql
SHOW SLAVE STATUS\G
```

只保留便于辨认字段的示例，实际输出还包含其他字段：

```text
Master_Host: 192.0.2.10
Master_User: app_user
Master_Port: 3306
Master_Log_File: mysql-bin.000001
Read_Master_Log_Pos: 154
Slave_IO_Running: Yes
Slave_SQL_Running: Yes
Last_IO_Error:
Last_SQL_Error:
```

查看当前连接：

```sql
SHOW PROCESSLIST;
```

下面是合成的最小示例，不是实际连接清单：

```text
Id | User     | Host             | db         | Command | Time | State | Info
1  | app_user | 192.0.2.20:50000 | example_db | Sleep   | 0    |       | NULL
```

#### 使用子查询排除结果

以 `example_table` 中的 `id` 与 `status` 字段为例，保留状态为 1 的记录，并排除归档表中已有的 ID：

```sql
SELECT `id`
FROM `example_db`.`example_table`
WHERE `status`=1
  AND `id` NOT IN (
    SELECT `id` FROM `example_db`.`example_archive`
  );
```
