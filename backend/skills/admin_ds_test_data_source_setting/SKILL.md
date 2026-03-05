---
name: admin-ds-test-data-source-setting
description: Tests whether given connection parameters (platform, host, port, username, password, database) can connect. Usually used before creating a data source. Use when the user asks to test connection, validate connection params, or check if config works.
---

# 测试数据源连接配置参数

## 职责

- 使用用户提供的连接参数尝试连接**用户数据库**，验证配置是否正确。成功则返回成功信息，失败则返回详细错误原因（如认证失败、网络不通、数据库不存在等）。不访问系统库，仅连接用户指定的数据库。

## 使用场景

- 在创建数据源配置之前，先测试连接是否可用
- 验证用户提供的数据库连接信息是否正确
- 诊断数据库连接问题

## 参数说明

- **platform**：数据库平台类型，必须是以下之一：`mysql`, `postgresql`, `sqlserver`, `oracle`, `clickhouse`, `doris`, `sqlite`
- **host**：数据库服务器主机地址，如 localhost、192.168.1.100。**SQLite 可传空字符串**
- **port**：端口号。MySQL 常用 3306，PostgreSQL 5432，SQL Server 1433，Oracle 1521，ClickHouse 9000，Doris 9030。**SQLite 可传 0**
- **username**：连接用户名。**SQLite 可传空字符串**
- **password**：对应用户名的密码。**SQLite 可传空字符串**
- **database**：要连接的数据库名。**SQLite 时为本机文件路径**（相对 backend/local_sqlite 如 `chinook.sqlite`，或绝对路径）

## 返回结果

- 成功：返回「数据源连接测试成功：[详细信息]」
- 失败：返回「数据源连接测试失败：[错误原因]」；不支持的 platform 会提示支持的类型列表

## 执行方式

- 直接调用保留工具 **tool_test_data_source_setting**(platform, host, port, username, password, database)，将返回结果原样或整理后回复用户。不涉及系统库 SQL。

## 可用工具

- `tool_test_data_source_setting`：测试连接参数（保留工具，连接用户配置的数据库）
