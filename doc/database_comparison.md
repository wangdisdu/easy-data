# 不同数据库系统的命名空间与逻辑隔离对比

不同数据库系统在逻辑结构（如 database、schema、catalog 等）上的设计存在显著差异，这反映了它们各自的架构哲学和使用场景。以下是对
MySQL、PostgreSQL、SQL Server、Oracle、ClickHouse 和 Doris 在"命名空间"或"逻辑隔离"层面的详细对比分析：

## 1. MySQL

### 核心概念：

- **Database（数据库）**：等价于 schema。
- 没有独立的 schema 层级；`CREATE DATABASE` 和 `CREATE SCHEMA` 是同义语句。

### 命名空间结构：

```
Server → Database (Schema) → Table
```

### 特点：

- 用户权限可授予到 database 级别。
- 不支持跨 database 的外键（InnoDB 引擎限制）。
- 默认不区分大小写（取决于操作系统和配置）。

## 2. PostgreSQL

### 核心概念：

- **Database**：物理隔离，不同 database 之间不能直接查询（需通过 dblink 或 foreign data wrapper）。
- **Schema**：逻辑命名空间，存在于 database 内部，用于组织表、视图等对象。

### 命名空间结构：

```
Cluster → Database → Schema → Table
```

### 特点：

- 一个用户可以访问多个 database。
- 同一 database 中可通过 schema 实现多租户或模块化设计。
- 默认 schema 是 public，可通过 search_path 控制查找顺序。
- 支持跨 schema 查询（如 `schema1.table1 JOIN schema2.table2`）。

## 3. Microsoft SQL Server

### 核心概念：

- **Database**：逻辑容器，类似 PostgreSQL 的 database。
- **Schema**：数据库内部的对象命名空间，与用户解耦（自 SQL Server 2005 起）。

### 命名空间结构：

```
Instance → Database → Schema → Table
```

### 特点：

- 默认 schema 通常是 dbo（database owner）。
- 用户可拥有多个 schema，schema 可被多个用户共享。
- 支持跨 schema 查询，但不支持跨 database 外键（除非使用分布式事务或链接服务器）。
- 权限可精细控制到 schema 级别。

## 4. Oracle

### 核心概念：

- **Database**：整个实例通常对应一个 database（物理+逻辑整体）。
- **Schema**：与用户（User）一一对应。创建用户即创建同名 schema。

### 命名空间结构：

```
Database → User/Schema → Table
```

### 特点：

- 没有"database"作为用户可见的逻辑隔离单位（不像 MySQL/PG）。
- 所有对象属于某个用户（即 schema），如 `SCOTT.EMP`。
- 跨 schema 访问需授权（`GRANT SELECT ON schema.table TO user`）。
- 支持"可插拔数据库"（PDB）在 12c+ 中实现多租户，但传统上 schema 是主要隔离机制。
- 注：Oracle 的"database"概念更偏向物理实例，而 schema 是逻辑单位。

## 5. ClickHouse

### 核心概念：

- **Database**：逻辑容器，类似 MySQL。
- 无 Schema 概念（传统意义上的）：所有表直接属于 database。
- 表引擎（如 MergeTree）决定存储和查询行为。

### 命名空间结构：

```
Server → Database → Table
```

### 特点：

- 不支持跨 database 的 JOIN（除非使用 remote() 函数或字典）。
- 没有用户定义的 schema 层级，但可通过 database 模拟多租户。
- 更注重性能和列式存储，而非关系模型的完整性。

## 6. Apache Doris

### 核心概念：

- **Catalog（自 2.0 起引入）**：最高层级，用于集成外部数据源（如 Hive、Iceberg）。
- **Database**：传统逻辑库，类似 MySQL。
- 无 Schema 层级：表直接属于 database。

### 命名空间结构（Doris 2.0+）：

```
Catalog → Database → Table
```

### 特点：

- 默认 catalog 为 default_catalog，其下是本地 database。
- 早期版本（<2.0）只有 Database → Table 结构。
- 设计目标是 MPP 分析型数据库，强调简单易用，因此省略了 schema 层。
