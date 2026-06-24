# A公司煤炭数据治理项目 — 背景与场景

## 1. 项目背景

### 1.1 企业简介

A公司是一家大型煤炭能源集团，下辖5座矿井，年产原煤约3000万吨。集团总部设有安全生产、调度指挥、煤质管控、财务结算等多个业务中心，各中心依赖信息系统进行日常决策。

### 1.2 数据治理驱动力

| 驱动力 | 具体表现 |
|--------|----------|
| **安全生产合规** | 瓦斯、一氧化碳等监测数据需保存≥2年，异常告警须可追溯 |
| **经营分析需求** | 产销一体化分析需要打通ERP订单与PI生产实绩 |
| **数据孤岛严重** | SAP-ERP、PI-System、SCADA、LIMS、OA五个系统相互独立，无统一数据标准 |
| **质量问题频发** | 各系统数据质量问题频发（空值、重复、格式不一致），影响分析准确性 |
| **监管报送压力** | 煤质数据、产量数据需定期向能源局、应急管理部报送 |

---

## 名词术语说明

本项目涉及多个工业和信息化领域的专业系统，以下逐一说明：

### ERP（Enterprise Resource Planning，企业资源计划）

企业级管理软件，覆盖采购、生产、销售、库存、财务等核心业务流程。SAP-ERP 是 SAP 公司出品的 ERP 系统，在大型企业（尤其是制造业、能源业）中占有率高。本项目中使用 SAP-ERP 管理销售订单（VBAK/VBAP）、客户主数据（KNA1）、物料主数据（MARA）。

> **本项目中涉及的 SAP 表说明：**
> - `VBAK`：销售订单抬头表，每行一条订单（VBELN 为订单号）
> - `VBAP`：销售订单行项目表，一条订单有多行物料（MATNR 为物料编码）
> - `KNA1`：客户主数据表（KUNNR 为客户编码，STCD1 为社会信用代码）
> - `MARA`：物料主数据表（MATNR 为物料编码）
> - `LIKP/LIPS`：交货单抬头/行项目

### PI-System（ProcessBook / OSIsoft PI，实时数据 historian）

工业场景常用的时序数据 historian 系统，由 OSIsoft（现 AVEVA）开发。PI-System 以标签（Tag）为单位连续采集传感器数据（温度、压力、流量等），支持每秒百万级点位写入，数据保留策略通常为 3-5 年。与关系型数据库不同，PI-System 按时间顺序存储，适合做趋势分析、异常检测。本项目中使用 PI-System 采集各矿井的瓦斯（WAGAS）、温度（TEMP）、一氧化碳（CO）等实时参数。

> **PI 标签命名示例：**
> `M001_FACE_A_WAGAS` → 鄂尔多斯一号矿 A 面瓦斯传感器
> `M003_FACE_B_TEMP` → 榆林李家沟矿 B 面温度传感器

### SCADA（Supervisory Control and Data Acquisition，数据采集与监控系统）

工控系统核心，负责采集现场设备状态（开关机、故障、运行参数）并执行简单控制指令。SCADA 系统数据量大（高频采样）、实时性要求高（毫秒级），通常通过 OPC-UA 或 MQTT 协议向上游推送。本项目中 SCADA 负责皮带机、排水泵、提升机等关键设备的实时状态监控，数据经 Kafka 实时流进入数据湖。

> **SCADA 与 PI 的区别：** SCADA 偏向"控制"，PI 偏向" historian（历史存档和分析）"。很多企业两者并存，SCADA 实时控制，PI 长期存储。

### LIMS（Laboratory Information Management System，实验室信息管理系统）

实验室样品和检测数据管理平台。煤炭行业的 LIMS 主要管理煤质化验数据：采样批次（CHARG）、灰分（AD）、挥发分（VD）、发热量（QGR）、硫分（ST）等指标。LIMS 数据是产销定价和安全监管的核心依据，其检测批次号（CHARG）是连接 PI 生产数据和 SAP 销售订单的关键桥梁。

> **LIMS 数据特点：** 批次型（非连续型）、实验室出具、数据滞后于生产（采样→送检→化验→录入通常需要 1-7 天）。

### OA（Office Automation，办公自动化系统）

企业行政审批和流程管理平台，处理合同审批、付款申请、会议纪要等事务。本项目中的 OA 系统用于合同管理（CONTRACT 表）和文档流转（DOC_FLOW 表），其合同编号是追溯销售订单的重要依据。

> **OA 与 ERP 的典型断点：** OA 中的合同审批流程和 ERP 中的销售订单相互独立，合同号和订单号需要人工关联——这是数据孤岛的典型表现。

### ODS / DWD / DWM / DWA（数据仓库分层）

数据治理中的标准分层架构（四层模型）：

| 层级 | 全称 | 含义 |
|------|------|------|
| **ODS** | Operational Data Store，贴源层 | 原样存储从各系统采集的数据，保留原始结构和审计字段 |
| **DWD** | Data Warehouse Detail，主题层 | 按业务主题建模，统一编码体系，清洗脏数据，关联主数据 |
| **DWM** | Data Warehouse Middle，汇总层 | 按分析主题预聚合，生成通用指标 |
| **DWA** | Data Warehouse Application，应用层 | 面向具体业务场景的聚合数据，直接支撑报表和分析 |

> **为什么需要分层：** 避免"烟囱式"开发，每层职责清晰。下层出问题可以从上层重算，而不必重新从源系统抽取。

### 数据质量（Data Quality）

衡量数据可用性的多个维度，常见指标包括：

| 维度 | 说明 | 示例 |
|------|------|------|
| **完整性** | 是否有缺失值 | 客户名称字段为空的记录数 |
| **一致性** | 跨系统/跨表数据是否一致 | 同一客户在 ERP 和 LIMS 中的编码是否统一 |
| **准确性** | 数据是否真实反映业务 | 瓦斯浓度超过 10% 的异常读数 |
| **时效性** | 数据是否及时更新 | PI 数据延迟超过 5 分钟的告警 |
| **唯一性** | 是否有重复记录 | 同一 VBELN 出现多次的订单 |

### 数据血缘（Data Lineage）

记录数据从源端到目标端的完整流转路径，支持"追根溯源"。分为：

- **表级血缘**：A 表由 B 表和 C 表加工而来
- **列级血缘**：A 表的 A1 列由 B 表的 B1 列映射而来
- **横向血缘**：跨系统追溯，如"某销售订单的煤质数据来自哪个矿井哪一天的 PI 读数"

### CDC（Change Data Capture，变更数据捕获）

一种数据同步技术，通过监听数据库日志（WAL）捕获数据变更（INSERT/UPDATE/DELETE），将变更记录实时推送到下游。本项目使用 Debezium 实现 SAP-ERP 和 LIMS 的 CDC，将 Oracle/SQL Server 的变更事件写入 Kafka，再落入 Delta Lake ODS 层。

> **为什么用 CDC 而不是定时轮询：** CDC 只传输变更量，网络传输量小、延迟低，且能捕获 DELETE 操作（定时轮询无法感知删除）。

### ELT / ETL

见 [ELTvsETL.md](./ELTvsETL.md)。

### Delta Lake / Iceberg / Hudi（数据湖表格式）

三种主流的开源数据湖存储格式，也称为"表格式"（Table Format）。它们解决的问题是：把数据文件组织成"有结构的表"，支持 ACID 事务、Schema 验证、时间旅行等数据库特性，让数据湖可以像数仓一样被可靠地查询和更新。

| 格式 | 主导方 | 特点 |
|------|--------|------|
| **Delta Lake** | Databricks（Spark 生态） | 与 Spark 深度集成，Python/SQL 支持好 |
| **Apache Iceberg** | Netflix/AWS/Apple | 跨引擎（Spark/Flink/Presto 均支持），云厂商原生适配 |
| **Apache Hudi** | Uber | 增量写入优化好，更适合 CDC 场景 |

> **类比**：如果把数据湖比作文件系统，这些格式就是"Excel 工作簿"——它们给原始文件加上了结构（列名、类型）、事务（保存后不丢数据）、历史（随时回退到旧版本）。

### 元数据（Metadata）

描述数据的数据。在数据治理中有三层含义：

1. **技术元数据**：表的字段名、类型、存储路径、负责人
2. **业务元数据**：字段的业务含义、数据Owner、质量评分
3. **操作元数据**：数据更新时间、ETL 作业记录、访问次数

元数据是构建数据资产目录的核心，也是血缘追踪的基础。

### 物化视图（Materialized View）

预先计算并存储结果的"特殊视图"。普通视图每次查询时实时计算，物化视图把结果写入磁盘，查询时直接读结果，速度快但存在数据延迟。

```sql
-- 普通视图：每次查都重新算
CREATE VIEW monthly_sales AS
SELECT MONTH(dt), SUM(amount) FROM sales GROUP BY MONTH(dt);

-- 物化视图：算一次存起来，定期刷新
CREATE MATERIALIZED VIEW mv_monthly_sales AS
SELECT MONTH(dt), SUM(amount) FROM sales GROUP BY MONTH(dt);
REFRESH MATERIALIZED VIEW mv_monthly_sales;
```

> **本项目用途**：在 Doris OLAP 层创建月度汇总物化视图，用户查询"各矿井月产量"时无需实时聚合亿级明细，直接读预计算结果。

### 星型模型（Star Schema）

OLAP 领域最常用的多维数据模型，由一张**事实表**和多张**维度表**组成，因结构像星星而得名。

```
        dim_mine（维度表：矿井）
              │
              │  mine_code
    ┌─────────▼─────────┐
    │  fact_sales       │  事实表：产销记录
    │  (日产量/订单额)  │  包含外键引用维度表
    └─────────┬─────────┘
              │
    dim_customer（维度表：客户）
```

- **事实表**：记录业务事件（销售、发货、检测），数据量大，不断增长
- **维度表**：记录事物的描述信息（客户是谁、矿井在哪），数据量小、变化慢

> **对比雪花模型**：雪花模型在维度表上再挂子维度表（更规范但查询更复杂），星型模型是维度表直接挂到事实表（查询快，本项目采用）。

### ACID 事务

数据库事务的四个特性：

- **A（Atomicity，原子性）**：一组操作要么全成功，要么全失败回滚
- **C（Consistency，一致性）**：事务前后数据库状态都是合法的
- **I（Isolation，隔离性）**：并发事务之间互不干扰
- **D（Durability，持久性）**：事务提交后数据永久保存

数据湖支持 ACID 事务的意义在于：多个人同时读写同一张表时，不会出现"读到一半未提交的数据"或"覆盖别人刚写的数据"的问题。

### 时间旅行（Time Travel）

数据湖的"后悔药"功能——可以查询任意历史时刻的数据版本。

```sql
-- Delta Lake：查询 3 天前的版本
SELECT * FROM sales VERSION AS OF 3

-- 查询 2024-01-01 的快照
SELECT * FROM sales TIMESTAMP AS OF '2024-01-01'
```

> **本项目用途**：当清洗规则调整时，可以回溯历史 ODS 数据，用新规则重算 DWD 层，无需重新从源系统抽取。

### Schema 演进（Schema Evolution）

表结构可以动态添加列、修改列类型，同时保留历史数据的特性。例如：销售订单表原本没有"煤种"字段，业务需要后可直接添加，历史记录中该字段为 NULL，不影响现有数据。

### dbt（data build tool）

SQL 优先的数据转换工具，核心思想是"用 SQL 文件管理数据模型"。dbt 读取 SQL 定义的转换规则，自动解析依赖关系、按序执行、生成文档和血缘图谱。

```
models/
  ├── staging/
  │   └── stg_sap_vbak.sql      # 清洗 SAP 订单数据
  ├── dwd/
  │   ├── dwd_production_daily.sql
  │   └── dwd_sales_order.sql   # 引用 stg_sap_vbak
  └── dwm/
      └── dwm_monthly_sales.sql  # 引用 dwd_sales_order
```

dbt Cloud 支持调度和告警，dbt Core 可本地使用。

### DataHub

LinkedIn 开源的元数据管理平台，提供数据资产目录、血缘图谱、搜索发现等功能。相比 Apache Atlas，DataHub 部署更简单（Docker compose）、前端体验更好、API 更完善（GraphQL）。

> **类比**：如果把数据湖比作图书馆，DataHub 就是图书馆的"索引系统"——告诉你每本书（数据集）在哪个书架（存储路径）、作者是谁（Owner）、和其他书有什么关系（血缘）。

### Kafka Connect / Debezium

- **Kafka Connect**：Kafka 的扩展框架，负责把外部数据源（数据库、文件系统）批量接入 Kafka，或从 Kafka 写出到目标存储。内置大量 Connector（JDBC、S3、HDFS 等）
- **Debezium**：基于 Kafka Connect 的 CDC 工具，监听数据库日志（WAL）捕获变更事件（INSERT/UPDATE/DELETE），将每条变更作为一条消息发送到 Kafka

> **本项目用途**：Debezium 监听 SAP-ERP（Oracle）和 LIMS（SQL Server）的 WAL，将每笔订单变更实时写入 Kafka Topic，`kafka-connect` 再将消息写入 Delta Lake ODS 层。

### SMT（Single Message Transform）

Kafka Connect 在消息写入前执行的轻量级转换逻辑，例如：
- 字段重命名：`before_id` → `id`
- 过滤已删除记录：`__deleted = 'true'` 的消息直接丢弃
- 字段脱敏：`STCD1` 字段打星号

在 CDC 入湖流程中，SMT 完成"数据进入湖之前的最后一道清洗"。

### Great Expectations

Python 编写的开源数据质量检测库，通过声明式定义数据"期望"（Expectations），自动验证数据是否符合预期。

```python
import great_expectations as ge

df = ge.from_pandas(df)

# 定义期望
df.expect_column_values_to_not_be_null("VBELN")       # VBELN 不能为空
df.expect_column_values_to_be_between("WAGAS", 0, 10) # 瓦斯浓度 0-10%
df.expect_column_distinct_values_to_be_in_set("AUART", # 订单类型必须是这些
    ["OR", "ZOR", "RET"])

# 运行验证并生成报告
results = df.validate()
print(results.success)  # True / False
```

> **本项目用途**：每批次数据入湖后，运行 Great Expectations 进行质量验证，生成 HTML 报告并触发告警。

### SCD Type 2（缓慢变化维 Type 2）

维度表中记录历史变化的方式之一——每当维度属性变化时，插入新行并标注起止时间，旧行标注失效日期。

```sql
-- 客户地址变化：保留历史记录
KUNNR  | NAME1          | addr     | valid_from | valid_to
C001   | 内蒙古能源公司   | 呼和浩特A  | 2022-01-01 | 2023-06-30
C001   | 内蒙古能源公司   | 鄂尔多斯B  | 2023-07-01 | 9999-12-31
```

| SCD 类型 | 变化处理方式 | 适用场景 |
|---------|------------|---------|
| Type 1 | 直接覆盖旧值 | 不需要历史值 |
| Type 2 | 保留历史行（加时间戳） | 需要追踪历史变化 |
| Type 3 | 保留当前和上一个值 | 仅需最近一次历史 |

### 向量化执行（Vectorized Execution）

一次处理一批数据（而非一行一行）的高效计算模式。列式存储天然支持向量化，CPU SIMD 指令一次可以对 128/256 位数据做并行计算。

> **与普通执行的对比**：普通执行是"一行一行的算"，向量化执行是"一列一列的算"。在大数据量下，向量化执行可提升 10-100 倍性能。ClickHouse 和 Doris 都以向量化执行引擎著称。

### RBAC + ABAC（访问控制）

两种访问控制模型的组合：

- **RBAC（Role-Based Access Control，基于角色的访问控制）**：按角色授权，"数据分析师可以读所有 ODS 表"——简单高效，但无法精细到具体数据范围
- **ABAC（Attribute-Based Access Control，基于属性的访问控制）**：按数据属性授权，"安全部的人只能看 M001-M003 矿井的 PI 数据"——更精细

```python
# RBAC：角色 → 权限
"安全管理员"   → ["PI告警数据:读写", "质量数据:读写"]
"业务分析师"   → ["DWA层数据:只读", "元数据:只读"]

# ABAC：用户属性 + 数据属性 → 动态判断
user.mine_scope = ["M001", "M002"]   # 可访问矿井范围
data.mine_code  = "M003"              # 数据属于哪个矿井
# 判定：user.mine_scope 包含 data.mine_code？ → 拒绝
```

### 快照（Snapshot）

数据湖在每次写入后生成的完整数据状态记录。Delta Lake / Iceberg 的快照通过文件清单（manifest）实现，写入新数据不覆盖旧数据，支持回退到任意历史版本。

### Docker Compose

定义和运行多容器 Docker 应用的工具。通过 YAML 文件声明多个服务（容器）的配置（镜像、端口、环境变量、依赖关系），一条命令 `docker-compose up -d` 即可启动完整环境。

```yaml
services:
  kafka:
    image: confluentinc/cp-kafka:7.4
    ports:
      - "9092:9092"
  mysql:
    image: mysql:8.0
    ports:
      - "3306:3306"
```

> **类比**：Docker Compose 就像"装修图纸"，Docker 容器是"预制件"，图纸告诉预制件怎么组合成一套房子。

### Apache Flink

分布式流处理引擎，支持有状态计算、事件时间处理、精确一次（Exactly-Once）语义。与批处理不同，Flink 处理的是"无尽的数据流"，适合 SCADA 实时告警、实时质量检测等场景。

> **Spark vs Flink**：Spark 先有批处理，后来加了流（Flink 先有流，后来加了批）。对延迟要求极高（毫秒级）的场景选 Flink，对吞吐量要求高但延迟要求一般的场景选 Spark Structured Streaming。

### 批处理（Batch Processing）与流处理（Stream Processing）

| | 批处理 | 流处理 |
|---|---|---|
| 数据形态 | 有界数据集（一次性处理） | 无界数据流（持续处理） |
| 延迟 | 分钟~小时级 | 毫秒~秒级 |
| 工具 | Spark、Hive | Flink、Kafka Streams |
| 适用场景 | 日终报表、ETL 作业 | 实时监控、即时告警 |

"批流一体"指用同一套引擎或同一套 API 同时处理批和流两种数据，降低开发和运维成本。

### 湖仓一体（Lakehouse）

一种融合数据湖和数据仓库优点的架构：既有数据湖的开放文件格式（Parquet/ORC）和低成本存储，又有数仓的数据管理和性能优化能力（ACID 事务、物化视图、索引）。Delta Lake/Iceberg/Hudi 就是实现湖仓一体的关键技术。

---

## 2. 数据现状与问题分析

### 2.1 系统矩阵

A公司核心业务系统如下：

| 系统 | 厂商/技术栈 | 用途 | 数据特征 |
|------|-----------|------|----------|
| **SAP-ERP** | Oracle关系型 | 销售订单、采购、财务 | 事务型、结构化、主数据+交易数据 |
| **PI-System** | TimescaleDB时序 | 实时工况参数采集 | 时序型、连续采样（1min间隔） |
| **SCADA** | 工控系统/Kafka | 设备状态、告警事件 | 高频流式、点位型 |
| **LIMS** | 实验室信息管理 | 煤质化验数据 | 检测报告型、批次属性 |
| **OA** | 流程引擎 | 行政审批、合同管理 | 事务型、状态流转 |

### 2.2 数据孤岛现状

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  SAP-ERP    │    │  PI-System  │    │    LIMS     │
│  Oracle     │    │ TimescaleDB │    │  SQL Server │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │ 客户编码 KUNNR   │ 矿井编码 M001    │ 矿井编码 M001
       │ 信用等级字段    │ 瓦斯浓度标签     │ 采样编号格式不一
       │ STCD1 统一    │ WAGAS_A1_001    │ 化验日期格式歧义
       │ 社会信用代码  │                 │
       └──────────────────────────┐         │
                                  │         │
                          【数据湖/数仓】
                                  │         │
                    ┌─────────────┴─────────┘
                    │  缺乏统一主数据管理
                    │  跨系统关联依赖人工核对
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    OA系统   │
                    │ 流程与主数据│
                    │ 完全割裂    │
                    └─────────────┘
```

### 2.3 核心数据问题

#### 问题一：主数据不一致（Data Profiling结论）

| 维度 | SAP-ERP (KNA1) | PI-System | LIMS |
|------|---------------|-----------|------|
| 矿井编码 | M001-M005 | M001-M005 | M001-M005 |
| 矿井名称 | "鄂尔多斯一号煤矿" | 标签无名称属性 | "鄂尔多斯1号" |
| 编码位数 | 4位（M001） | 无统一编码 | 3位（M01） |
| 信用代码格式 | STCD1: 9+6+4+3 | — | 无此字段 |

**影响**：产销分析、矿端成本核算无法自动关联，需人工映射表。

#### 问题二：时序数据质量问题

- **设备掉线**：PI系统每日约0.5%的点位数据缺失，表现为连续时间戳中断
- **异常突升**：传感器数据存在约1%的异常波动（WAGAS读数突增3倍以上），需判断是设备故障还是真实异常
- **数据压缩**：PI系统使用swingdoor压缩算法，偏差0.01，仅保留拐点值，导致与SCADA实时流数值存在精度差异

#### 问题三：订单-发货数据不一致

- VBAP行项目中有约1%关联到无效VBELN（0000000000），导致交货单拆分无法自动化
- LIKP交货单与VBAP行项目存在数量差（允许公差±5%），但系统无差异告警
- 部分订单在ERP中已"已完成"，但PI系统中对应矿点仍在生产（数据延迟造成）

#### 问题四：煤质数据与销售订单脱节

- LIMS检测结果以批次为单位，与SAP中"批次（CHARG）"无直接关联
- 化验报告发出后，销售部门无法自动获取，导致部分订单按"预估煤质"定价，后续结算存在差价争议
- 检测样品约2%存在数据质量问题（空值、重复录入），需人工核验

#### 问题五：OA流程数据资产化不足

- 合同DOC_NO编码规则不统一（历史数据为`DOC2022XXXXX`，新数据为`HT2024XXXXXX`），无法按时间序列分析
- 流程状态与ERP订单状态无联动，如"审批中"的付款申请无法自动阻止财务过账
- 300万条历史流程数据无全文索引，审计追溯依赖人工翻查

---

## 3. 数据治理解决方案

### 3.1 总体架构

```
                    ┌─────────────────────────────────────┐
                    │         数据治理平台（DataOps）       │
                    │  Apache Atlas / DataHub / 自研目录    │
                    └──────────────┬──────────────────────┘
                                   │ 元数据采集 / 血缘标注
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
  ┌──────▼──────┐         ┌───────▼───────┐        ┌──────▼──────┐
  │  数据采集层  │         │   数据存储层   │        │  数据质量层  │
  │ Flume/Kafka │         │ MinIO / HDFS  │        │ Great_expectations │
  │  CDC / API  │         │ Delta Lake    │        │ 自研规则引擎 │
  └──────┬──────┘         └───────┬───────┘        └──────┬──────┘
         │                         │                         │
  ┌──────▼──────┐         ┌───────▼───────┐        ┌──────▼──────┐
  │ SAP-ERP     │         │   贴源层 ODS   │        │  数据质量报告│
  │ PI-System   │   ──▶   │   主题层 DWD   │   ──▶  │  问题工单   │
  │ SCADA       │         │   汇总层 DWM   │        │  告警推送   │
  │ LIMS        │         │   应用层 DWA   │        │  质量评分卡 │
  │ OA          │         └───────────────┘        └─────────────┘
  └─────────────┘
```

### 3.2 数据标准体系

#### 3.2.1 核心主数据标准

| 数据域 | 标准编码规则 | 标准名称 | 负责部门 |
|--------|-------------|----------|----------|
| 矿井 | M001-M005（4位数字） | 集团统一矿井目录 | 安全部 |
| 煤种 | C01=原煤/C02=精煤/C03=中煤/C04=矸石/C05=洗煤 | 煤种分类标准 | 煤质中心 |
| 客户 | KUNNR 6位数字 | 客户主数据标准 | 销售部 |
| 物料 | MATNR 9位数字（501XXXXXX） | 物料编码规则 | 采购部 |
| 合同 | HT+YYYY+6位序号 | 合同编号规则 | 法务部 |

#### 3.2.2 时序数据标签标准

格式：`{矿井}_{工作面}_{传感器类型}`

示例：
```
M001_FACE_A_WAGAS   — 鄂尔多斯一号矿A工作面瓦斯浓度
M001_FACE_A_TEMP    — 鄂尔多斯一号矿A工作面温度
M002_FACE_B_CO      — 榆林李家沟矿B工作面一氧化碳
```

阈值规则（元数据属性）：
| 传感器 | 正常范围 | 报警阈值 | 危险阈值 |
|--------|---------|---------|---------|
| WAGAS | 0-0.5% | 0.8% | 1.0% |
| CO | 0-24ppm | 24ppm | 50ppm |
| TEMP | 15-35℃ | 38℃ | 45℃ |

### 3.3 数据质量管理

#### 3.3.1 质量规则设计

**规则一：主数据唯一性**

```sql
-- KNA1客户主数据：STCD1（社会信用代码）必须唯一
SELECT KUNNR, COUNT(DISTINCT STCD1) as cnt
FROM ods_sap_kna1
GROUP BY STCD1
HAVING COUNT(DISTINCT KUNNR) > 1;
```

**规则二：订单行项目完整性**

```sql
-- VBAP行项目：VBELN必须关联有效的销售订单
SELECT COUNT(*) FROM ods_sap_vbap
WHERE SUBSTR(VBELN, 1, 10) = '0000000000';  -- 应为0
```

**规则三：时序数据连续性（PI-System）**

```python
# 检验逻辑：检查每个标签的时间戳序列是否有断点
def check_pi_continuity(df, tag, interval_min=1):
    df_tag = df[df['tag'] == tag].sort_values('timestamp')
    expected = pd.date_range(
        start=df_tag['timestamp'].min(),
        end=df_tag['timestamp'].max(),
        freq=f'{interval_min}min'
    )
    actual = df_tag['timestamp'].values
    gap_count = len(expected) - len(actual)
    return gap_count  # >0 则存在缺失
```

**规则四：煤质数据有效性**

```python
# 灰分（AD）必须在合理区间内
AD_RANGES = {
    '原煤': (10, 50),
    '精煤': (5, 15),
    '中煤': (15, 45),
    '矸石': (45, 90),
    '洗煤': (5, 20),
}
def validate_lims_ad(sample_type, ad_value):
    lo, hi = AD_RANGES.get(sample_type, (0, 100))
    return lo <= ad_value <= hi
```

#### 3.3.2 质量评分卡

按数据域月度评分：

| 数据域 | 完整性(30%) | 一致性(30%) | 时效性(20%) | 准确性(20%) | 综合得分 |
|--------|------------|------------|------------|------------|---------|
| SAP-ERP | 97.2 | 91.5 | 99.8 | 95.1 | 95.7 |
| PI-System | 98.1 | 93.8 | 99.5 | 89.2 | 95.0 |
| LIMS | 94.6 | 88.3 | 96.4 | 91.7 | 92.5 |
| OA | 92.1 | 85.0 | 94.8 | 90.5 | 90.3 |

### 3.4 数据安全分级

| 级别 | 定义 | 数据范围 | 保护要求 |
|------|------|---------|---------|
| **核心资产** | 一旦泄露影响安全生产 | PI实时告警阈值、SCADA控制指令 | 加密存储、访问审批、审计日志 |
| **重要资产** | 影响经营分析准确性 | SAP销售订单、LIMS煤质数据 | 访问控制、操作审计、防批量导出 |
| **一般资产** | 内部流程数据 | OA流程数据、历史归档 | 基础访问控制 |

### 3.5 数据资产目录

元数据清单（示例）：

```json
{
  "sys_name": "SAP-ERP",
  "table_name": "VBAK",
  "table_cn": "销售订单抬头",
  "owner": "销售部",
  "row_count": 6030000,
  "storage_size_mb": 97,
  "partition_field": "ERDAT",
  "columns": [
    {"name": "VBELN", "cn": "销售凭证号", "type": "VARCHAR(10)", "pk": true},
    {"name": "ERDAT", "cn": "凭证日期", "type": "DATE"},
    {"name": "KUNNR", "cn": "客户编号", "type": "VARCHAR(6)", "fk": "KNA1.KUNNR"}
  ],
  "quality_rules": ["完整性-订单号非空", "一致性-客户编号关联KNA1"],
  "sla": "T+1全量"
}
```

### 3.6 数据血缘追踪

```
PI-System.tags (WAGAS_M001_FACE_A)
        │ 关联
        ▼
  LIMS.samples (M001 采样批次)
        │ 关联（批次号 CHARG）
        ▼
  SAP-ERP.VBAP (物料明细)
        │ 关联（销售订单 VBELN）
        ▼
  SAP-ERP.VBAK (订单抬头)
        │ 关联（客户 KUNNR）
        ▼
  SAP-ERP.KNA1 (客户主数据)
        │
        │ 触发
        ▼
  OA.DOC_FLOW (合同审批流程)
```

---

## 4. 模拟数据说明

### 4.1 模拟范围

本项目生成了A公司5个异构系统的模拟数据，用于数据治理功能演示和算法验证。

| 系统 | 记录数 | 存储大小 | 说明 |
|------|--------|---------|------|
| SAP-ERP | 1809万 | 456.5 MB | 含KNA1/VBAK/VBAP主从数据 |
| PI-System | 7862万 | 364.6 MB | 100标签×1分钟间隔×2年 |
| LIMS | 201万 | 56.5 MB | 煤质检测记录 |
| OA | 502.5万 | 118.4 MB | 审批流程记录 |
| **合计** | **~1亿** | **995.6 MB** | — |

### 4.2 质量问题注入

各数据集均注入了模拟的数据质量问题：

- **SAP-ERP**：0.5%空值、0.5%异常值、0.5%重复行；VBAP约1%关联到无效订单号
- **PI-System**：0.5%点位缺失（模拟设备掉线）、1%异常突升（模拟传感器故障）
- **LIMS**：与其他系统一致的质量问题比例
- **OA**：2%数据质量问题

### 4.3 数据孤岛模拟

- 各系统使用独立的矿井/客户编码体系（长度不一致、前缀不一致）
- 无外键关联，跨系统分析需要通过主数据映射表实现
- 同一矿井在不同系统中的名称存在细微差异

---

## 5. 后续治理路径

本节定义从 Demo 环境到生产部署的 5 个 Phase。**Phase 编号仅在本节统一；其他文档不再重复定义 Phase**。每个 Phase 给出：核心工作项 / 交付物 / 估时（参考 `docs/Design.md` 选型）。

> 设计选型（ClickHouse vs Doris、Superset vs Metabase 等）见 `docs/Design.md` 相应章节；本节不重复。

### Phase 1【数据接入】 ── ODS 贴源层建设（3 个月）

| 工作项 | 交付物 |
|--------|--------|
| 基础设施落地 | Delta Lake + Spark + Kafka 集群 |
| 历史数据入湖 | ODS 贴源层 5 系统（sap_erp/pi_system/lims/oa/scada）全量 Parquet → Delta |
| 增量同步 | Kafka Connect / Debezium 监听源库 CDC，写入 ODS Delta 表 |

### Phase 2【治理落地 + 应用赋能】 ── 元数据 + 质量 + DWD + OLAP（4.5 个月）

> **本节是合并定义**：原 `Background.md` 第 5 节的「标准建设」与 `Design.md` 第 10 节的「Phase 2 + 长期 OLAP」按工作依赖合并到此处。
> **预估时间**比 Design.md 原 3 个月多 50%，因为吃进了原 Phase 5（OLAP / 跨系统宽表）的部分工作。

| 工作项 | 交付物 | 估时 |
|--------|--------|------|
| DataHub 标准化接入 | GMS REST + Kafka 事件流（替代当前 `direct_es_bulk.py`） | 2 周 |
| 自动血缘采集 | Spark / Flink 任务自动产出 lineage aspect（替代手工 `lineage_recipe.yaml`） | 3 周 |
| GE Checkpoint 化 | 规则引擎持久化报告 + 定时调度（替代当前 `run_great_expectations.py` 一次性 CLI） | 2 周 |
| DWD 主题层首批 | 销售 / 生产 2 个主题域 DWD 表（按主题重组，非当前按系统分） | 3 周 |
| 主数据编码标准化 | 矿井 / 客户 / 物料编码映射表（MDM 轻量化，不建独立 MDM 系统；如源系统已统一则跳过） | 2 周（并行） |
| 跨系统产销宽表 | `dwa_sales_production`（4 表 JOIN：PI生产 + LIMS煤质 + SAP订单 + KNA1客户） | 2 周 |
| OLAP 引擎 | ClickHouse 或 Doris（参见 `docs/Design.md` 选型）+ Materialized View | 3 周 |
| 可视化看板 | Apache Superset 或 DataHub Dashboard | 2 周 |
| 4 个分析场景 SQL 模板 | 产销对比 / 煤质定价 / 安全趋势 / 订单履约 | 1 周 |

**Phase 2 入口条件**：Phase 1 ODS 稳定运行 ≥ 1 个月；**Phase 2 出口条件**：4 个分析场景可在 OLAP 看板中切换维度实时出数。

### Phase 3【质量与安全运营】 ── 监控 + 工单 + 安全（6 个月）

| 工作项 | 交付物 |
|--------|--------|
| 实时质量监控 | Flink 流式规则引擎（替代当前 GE 批处理） |
| 告警工单系统 | 与 OA / 钉钉 / 飞书集成，自动派单到 Owner |
| DWM 汇总层 | 跨域汇总（销售+生产+煤质+安全） |
| 安全分级与脱敏 | RBAC + ABAC + 字段级脱敏（按 6.6 章节定义的「核心/重要/一般」三级） |

### Phase 4【资产运营】 ── 数据资产目录 + 开放 API（持续）

| 工作项 | 交付物 |
|--------|--------|
| 元数据采集自动化 | 从 Phase 2 的 DataHub 接入延伸至全公司系统 |
| 资产地图 | 5 系统 × N 主题 × N 字段的可视化探索 |
| 数据资产开放 API | REST / GraphQL，按 Owner 审批后开放 |

### Phase 5【分析与决策赋能】 ── 自助分析 + AI 增强（持续）

| 工作项 | 交付物 |
|--------|--------|
| 自助分析 | Superset / Metabase 全员开放 |
| AI 增强 | 异常检测、根因定位、智能修复建议（基于 LLM） |
| 实时决策 | 流批一体 OLAP + 业务规则引擎 |

---

## 6. 演示目标

本 Demo 通过 A 公司5个异构系统的模拟数据，全流程展示数据治理的核心能力。演示分为多个模块，依次递进：

---

### 6.0 演示流程总览

**模块与 Phase 的归属关系**：

| 模块 | 演示时长 | 归属 Phase |
|------|---------|-----------|
| 6.1 数据资产可视化 | 5 分钟 | **Phase 1** |
| 6.2 质量检测与根因定位 | 10 分钟 | **Phase 1** |
| 6.3 血缘全链路追溯 | 10 分钟 | **Phase 1** |
| 6.4 清洗与质量提升 | 10 分钟 | **Phase 1** |
| 6.5 ELT + DWA 主题宽表 | 10 分钟 | **Phase 1** |
| 6.6 DWA 宽表分析 + DuckDB 即席查询 | 10 分钟 | **Phase 1** |
| 6.7 主数据编码标准化 | 10 分钟 | **Phase 2**（跨系统分析前置依赖） |
| 6.8 DataHub 生产接入 | 10 分钟 | **Phase 2** |
| 6.9 自动血缘采集 | 10 分钟 | **Phase 2** |
| 6.10 定时质量监控 | 10 分钟 | **Phase 2** |
| 6.11 主题域 DWD | 10 分钟 | **Phase 2** |
| 6.12 跨系统 DWA + OLAP | 10 分钟 | **Phase 2** |
| 6.13~6.16 | 待设计 | **Phase 3** |

> **模块与 Phase 的关系**：6.2~6.7 属于 Phase 1；6.8~6.13 属于 Phase 2（见下方）；6.14~6.16 属于 Phase 3（占位，未设计）。


### 6.1 模块一：数据资产可视化（演示 5 分钟，归属 Phase 1）

**目标**：展示数据接入后的全局可见性——有哪些数据、分布在哪里、质量如何。

| 演示点 | 预期效果 |
|--------|---------|
| 数据源接入 | 5个系统的连接状态一目了然 |
| 资产目录 | 每张表有中文注释、Owner、存储大小、记录数 |
| 质量概览 | 各系统质量评分卡（饼图/柱状图） |
| 安全分级 | 核心/重要/一般资产分类展示 |

**验证方式**：打开数据治理平台首页，即可看到5个系统的资产地图和质量评分。

---

### 6.2 模块二：数据质量检测与根因定位（演示 10 分钟，归属 Phase 1）

**目标**：展示质量问题的自动化发现、告警和根因分析能力。

| 演示场景 | 发现的问题 | 验证效果 |
|---------|-----------|---------|
| SAP VBAK 空值检测 | NETWR、ERZET 约0.5%空值 | 系统自动告警，定位到列 |
| SAP VBAP 关联失效 | 1%行项目关联到无效订单号 | 血缘断裂告警，定位影响单据 |
| PI 时序断点检测 | 0.5%点位缺失（WAGAS标签） | 连续性规则命中，定位到标签和时间段 |
| PI 异常突升检测 | 1%数值突升3倍以上 | 异常波动规则命中，列出异常时间点 |
| LIMS 煤质有效性 | AD灰分超出煤种合理范围 | 业务规则命中，列出异常样品ID |

**验证方式**：触发质量检测任务，在问题工单列表中看到所有告警记录，包含问题描述、影响行数、责任部门。

---

### 6.3 模块三：数据血缘全链路追溯（演示 10 分钟，归属 Phase 1 手工 / Phase 2 自动）

**目标**：展示跨系统数据从哪儿来、到哪儿去，能定位源头也能评估影响范围。

#### 🎯 业务视角

**能告诉老板什么？**
- 「这个订单的煤质数据从哪批样品来的」——点 SAP `vbak` 就能看到 `lims.samples`
- 「这个样品有没有对应到销售」——点 LIMS 样品能看到哪些订单在用
- 「LIMS 煤质异常会影响哪些订单」——血缘图上找下游，5 分钟出影响面清单

**实际已建的血缘关系（4 条边）：**

| 上游（源） | 下游（去向） | 业务含义 |
|-----------|-------------|---------|
| `sap_erp.vbak` | `lims.samples` | 销售订单对应到 LIMS 采样批次（按 KUNNR 关联） |
| `sap_erp.vbap` | `lims.samples` | 销售行项目对应到 LIMS 采样批次 |
| `sap_erp.vbak` | `dwd.vbak` | ODS 销售订单 → DWD 清洗后销售订单 |
| `pi_system.tags` | `dwd.tags` | ODS PI 时序 → DWD 清洗后时序 |
| `lims.samples` | `dwd.samples` | ODS LIMS 样品 → DWD 清洗后样品 |

**演示剧本**（5 分钟）：
1. 打开 DataHub UI → 搜索 `lims` → 进入 `lims.samples` dataset
2. 切到 **Lineage** 标签页 → 展示 2 条上游（VBAK / VBAP）
3. 切到下游 → 展示 1 条（DWD 清洗表）
4. 类比点 `pi_system.tags` → 上游为空（源表）、下游指向 DWD
5. 收尾：告诉老板「生产事故→煤质异常→订单延迟」这条 3 跳链路，用血缘图 + 影响列表两件套给业务方看

**暂时做不到的（待办）：**
- PI → LIMS 采样批次 的 5 跳完整链路（当前 recipe 没建边，UI 上看到的是断点）
- LIMS → SAP CHARG → VBAP → VBAK → KNA1 → OA 的产销全链
- 业务人员读血缘图谱：当前 DataHub v1.6 UI 是英文 + 工程师视角，需用 `scripts/check_browse.py` 或截图辅助讲

#### 🛠️ 技术视角

**血缘配置**：`lineage_recipe.yaml`（YAML 描述 source/target/join key）。

**写入路径**：通过 DataHub GMS REST `/aspects` 写入 `upstreamLineage` aspect。
```bash
uv run python scripts/emit_lineage.py
```

**Schema**：
```yaml
- source: sap_erp.vbak
  target: lims.samples
  join_key: KUNNR
  type: business_lineage  # 跨系统 JOIN
- source: sap_erp.vbak
  target: dwd.vbak
  type: processing_lineage  # 加工血缘（ODS→DWD）
```

**数据落点**：
- GMS MySQL 库：`metadata_aspect` 表的 `upstreamLineage` aspect
- DataHub UI Lineage 视图：从 OpenSearch 索引 `datasetindex_v2` 读出来渲染

---

### 6.4 模块四：数据清洗与质量提升（演示 10 分钟，归属 Phase 1）

**目标**：展示从 ODS 原始层到 DWD 清洗层，脏数据怎么变干净。

#### 🎯 业务视角

**能告诉老板什么？**
- 同一份数据清洗前质量分 C/D，清洗后能上 B/A
- 清洗后下游报表不再需要逐条挑异常
- 清洗规则可复用，新进数据按规则自动跑

**实际已做的清洗（3 类）：**

| 清洗类型 | 业务含义 | 实际规则 |
|---------|---------|---------|
| 去空 | 关键字段不能为空 | 业务主键、销售金额、时间戳 |
| 去重 | 同一笔不能录两次 | 主键去重 |
| 规范化 | 字段格式统一 | 矿井编码大写、客户号去前导零、日期统一 ISO |

**演示剧本**（5 分钟）：
1. 打开 module1.ipynb → 「步骤 1：资产目录与存储分布」
2. 对比 ODS 层（`data/historical/sap_erp/vbak_year=2022.parquet`）和 DWD 层（`data/lakehouse/dwd/sap_erp/dwd_vbak/`）的行数
3. 跑 `ingest_to_deltalake.py --layer dwd` → 给出「清洗前 3,014,284 行 → 清洗后 2,999,312 行（剔除 14,972 行，0.5%）」的数字
4. 收尾：跑一次质量检测，对比评分卡分变化

**暂时做不到的（演示版简化）**：
- 智能清洗：VBAP 关联失效行标记（IS_VALID_LINK 列）— 计划里有，实际没实现
- PI 异常值线性插值：未实现，仅在质量检测里识别为异常
- LIMS 灰分有效性校验并自动修正：未实现，仅在 GE 规则里识别为异常

**这些「待办」对业务意味着**：当前 DWD 层是「干净但不修复」，质量问题需要源头系统改单；DWD 只保证「格式统一、可下游消费」。

#### 🛠️ 技术视角

**执行命令**：
```bash
uv run python scripts/ingest_to_deltalake.py --layer ods   # ODS 入湖
uv run python scripts/ingest_to_deltalake.py --layer dwd   # DWD 清洗
```

**存储路径**：
- ODS：`data/lakehouse/ods/{system}/{table}/`（Delta Lake 格式，Parquet + _delta_log）
- DWD：`data/lakehouse/dwd/{system}/{table}/`

**清洗规则实现**：见 `scripts/ingest_to_deltalake.py` 的 `--layer dwd` 分支（pandas 实现，无 GE 引擎参与清洗阶段；GE 只在质量检测阶段用）。

**Delta Lake 优势（讲解点）**：
- ACID 事务：清洗过程中断不会留下半截
- Schema 演进：上游加列不会被拒绝
- Time Travel：`DeltaTable(...).history()` 可回溯到任意版本

**与 GE 质量检测的关系**：
- 清洗 = 已知脏数据按规则改
- 质量检测 = 跑规则看分数，**不自动改数据**
- 两者解耦：质量检测可重复跑出评分卡；清洗是一次性 ETL 动作

---

### 6.5 模块五：ELT 数据加工与 DWA 主题宽表（演示 10 分钟，归属 Phase 1）

**目标**：从 DWD 清洗层构建 DWA 汇总宽表，支撑业务报表和即席查询。

#### 🎯 业务视角

**能告诉老板什么？**
- 销售部想看「日销售汇总」：直接查 DWA 表，不用再跑 5 个 SQL JOIN
- 安全部想看「传感器告警排名」：直接查 `dwa_tag_alarm` Top 20
- 煤质中心想看「月度煤质报告」：直接查 `dwa_coal_quality`

**实际已构建的 3 张 DWA 宽表：**

| DWA 表名 | 业务场景 | 主要字段 | 数据源 |
|---------|---------|---------|--------|
| `dwa_sales_daily` | 日销售汇总 | sale_date, order_count, customer_count, total_amount | sap_erp.vbak |
| `dwa_tag_alarm` | 传感器告警 Top | tag_name, alarm_count, alarm_pct | pi_system.tags |
| `dwa_coal_quality` | 月度煤质 | mine_code, year_month, coal_type, avg_ash, avg_qgr | lims.samples |

**演示剧本**（5 分钟）：
1. 跑 `build_dwa_models.py --layer dwa` → 输出 3 张宽表的行数、存储大小
2. 用 DuckDB 查 `dwa_sales_daily` → 出最近 30 天销售趋势
3. 查 `dwa_coal_quality` → 出煤种价格分布（结合 step1 业务影响翻译讲）

**暂时做不到的（演示版简化）**：
- 跨系统产销一体化宽表 `dwd_sales_production`（PI生产 + LIMS煤质 + SAP订单 + KNA1客户）—— 计划承诺过，实际没建
- 矿井编码标准化映射表：实际靠源系统字段值已经一致（如都叫 `M001`），没单独建维表
- 客户主数据整合（VBAK + KNA1 补全客户标准名称）：未实现
- 历史数据回溯重处理：未实现，DWA 只跑最新一次 ETL

**对业务的影响**：当前 3 张 DWA 宽表是**单系统**的，跨系统分析需要业务人员自己写 SQL JOIN。后续 Phase 2 才会补跨系统宽表。

#### 🛠️ 技术视角

**执行命令**：
```bash
uv run python scripts/build_dwa_models.py --layer dwa
```

**引擎**：DuckDB（in-memory OLAP，连 Parquet/Delta Lake 文件直接算）
> 注：pyproject.toml 暂未显式声明 `duckdb` 依赖（仅 `build_dwa_models.py` 直接 import）；如需重跑需 `uv pip install duckdb`。

**DWA 宽表示例 SQL（实际 build_dwa_models.py 中的片段）**：

```sql
-- dwa_sales_daily 聚合
SELECT
    order_date                          AS sale_date,
    COUNT(DISTINCT vbeln)               AS order_count,
    COUNT(DISTINCT kunnr)               AS customer_count,
    SUM(netwr)                          AS total_amount
FROM dwd_vbak
WHERE order_date BETWEEN '2022-01-01' AND '2023-06-30'
GROUP BY order_date
ORDER BY order_date;
```

**存储路径**：`data/lakehouse/dwa/{system}/{dwa_table}/`

---

### 6.6 模块六：DWA 宽表分析 + DuckDB 即席查询（演示 10 分钟，归属 Phase 1 DuckDB 演示版 / Phase 2 ClickHouse + Superset）

**目标**：用 DWA 宽表 + DuckDB 即席查询做业务分析，验证治理后数据的可用性。

#### 🎯 业务视角

**能告诉老板什么？**
- 业务人员不需要写复杂 SQL：宽表已经聚合好，直接看数
- 临时分析需求：从「提需求→排期→出报表」的 3~5 天，降到「业务自己查 DWA 表」的 10 分钟
- 4 个高频分析场景（按当前实现可达范围）：

| 分析场景 | 数据源 | 业务结论 | 当前可达 |
|---------|--------|---------|---------|
| 销售趋势 | `dwa_sales_daily` | 最近 30 天订单数 / 销售额 / 客户数 | ✅ 可查 |
| 告警传感器排名 | `dwa_tag_alarm` | Top 20 高频告警传感器，定位维护重点 | ✅ 可查 |
| 月度煤质 | `dwa_coal_quality` | 各矿井各煤种灰分 / 热值月度均值 | ✅ 可查 |
| 跨系统产销对比 | dwa + dwd JOIN | 矿井日产量 vs 日发货量 | ⚠️ 可查但需自己写 JOIN |

**演示剧本**（5 分钟）：
1. `build_dwa_models.py` 跑出 3 张 DWA 表
2. 用 `duckdb` CLI 或 Python 临时 SQL 查 Top 10 告警传感器 → 给出「这 10 个点位占 80% 告警量」结论
3. 查煤质月度走势 → 给出「3 月精煤灰分普遍偏高」结论
4. 收尾：演示「临时问个数字不用等 IT」

**暂时做不到的**：
- 产销对比分析中「产量>>发货量 = 库存异常」需要 PI 与 SAP 跨系统 JOIN，当前 DWA 没建跨系统表
- 煤质定价分析「灰分升 1% 价差 15 元/吨」是**业务经验**，DWA 表里有灰分和销售额但没自动算相关系数
- 订单履约率（承诺 vs 实际）：LIKP/LIPS 表里有数据但没专门建 DWA 宽表
- 钻取（年→月→日→单笔）/ 切片（单矿井）：需要 OLAP 看板，当前用 DuckDB CLI 替代

#### 🛠️ 技术视角

**执行方式**：
```bash
# 命令行即席查询
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily' LIMIT 10;"

# Python 内嵌查询
import duckdb
duckdb.connect().execute("""
    SELECT mine_code, year_month, avg_ash
    FROM 'data/lakehouse/dwa/lims/dwa_coal_quality'
    ORDER BY avg_ash DESC LIMIT 5;
""").fetchall()
```

**后续 Phase 2 路线**（完整定义见第 5 节）：
- 部署 ClickHouse / Doris 做 OLAP 引擎
- 用 Apache Superset / DataHub Dashboard 做可视化看板
- 补建跨系统产销宽表 `dwa_sales_production`
- 补建 4 个分析场景的 SQL 模板

**当前 Demo 边界**（演示时**必须**明确说）：
- 这是**数据可用性验证**，不是生产级 OLAP
- 4 个分析场景里 1、2、3 能现场出数，4（产销对比）需要业务自己写 JOIN
- 临时查询 5 分钟能出，生产报表需等 Phase 2

**教学 notebook**：[`notebook/module6.ipynb`](notebook/module6.ipynb)

---

### 6.7 模块七：主数据编码标准化（演示 10 分钟，归属 Phase 2）

**目标**：统一矿井 / 客户 / 物料编码，为跨系统分析（主题域 DWD、产销宽表）扫除 JOIN 障碍。

> **承上启下**：Phase 1 各系统数据独立可用（6.2~6.7）；Phase 2 跨系统分析（6.11 主题域 DWD → 6.12 跨系统产销宽表）依赖统一的编码体系。本模块是这两者的桥梁。

| 演示点 | Phase 1（当前） | Phase 2（升级后） |
|--------|---------------|-----------------|
| 矿井编码 | PI/LIMS/SAP 三系统各用自己的命名（如 PI 称 `M001`，SAP 称 `M001`，字面一致但字段名不同） | 统一矿井维表（`mine_code → mine_name → mine_type`），源系统字段映射到标准编码 |
| 客户编码 | VBAK 的 KUNNR 和 KNA1 的 KUNNR 各自独立，无校验 | 客户维表（`kunnr → customer_name → region → credit_level`），KUNNR 唯一性校验 |
| 物料编码 | MARA 物料编码未在 LIMS/OA 中关联 | 物料维表（`matnr → mat_desc → mat_type`），跨系统关联 |
| 标准化方式 | 源系统已统一，无需映射（如矿井编码字面已一致） | 建轻量维表（不建独立 MDM 系统），在 DWD 层 JOIN 时应用映射 |
| 与 DWA 的关系 | `dwa_sales_daily` 等单系统宽表不受影响 | `dwa_sales_production` 跨 4 表 JOIN 依赖矿井/客户编码统一 |

**Phase 1 教学**：`notebook/module1.ipynb` 第 3 节（`dwd_vbak` 清洗脚本，矿井编码已是字面统一，无需显式映射）

**Phase 2 教学**：展示矿井维表 + 客户维表 schema + DWD 层 JOIN 映射 SQL

**验证方式**：DWD 层查询中，PI矿井编码 = SAP矿井编码 = LIMS矿井编码，三表 JOIN 无需 `WHERE a.mine = b.mine AND b.mine = c.mine` 的多表映射子查询。

---

### 6.8 模块八：DataHub 生产接入（演示 10 分钟，归属 Phase 2）

**目标**：从「手工直写 OpenSearch」升级为「Kafka 事件流 → GMS → OpenSearch 自动同步」。

| 演示点 | Phase 1（当前） | Phase 2（升级后） |
|--------|---------------|-----------------|
| 接入方式 | `scripts/direct_es_bulk.py` 直接 bulk 写入 OpenSearch | GMS REST API + Kafka 事件流（DataHub actions 服务消费） |
| 新表注册 | 手动跑 `emit_browsepaths.py` | 新 Parquet 文件落地 → Kafka 事件 → DataHub 自动发现 |
| 元数据更新 | 手动跑 `emit_browsepaths.py` | Kafka CDC 事件驱动，无需人工干预 |
| 资产一致性 | ES 和 MySQL 可能短暂不一致 | 最终一致（GMS 为唯一写入路径） |

**Phase 1 教学**：`notebook/datahub_setup.ipynb` 第 3 节（手动 bulk 写入 + 验证 ES count）

**Phase 2 教学**：`datahub-quickstart.yml` 中的 `datahub-actions` 服务配置 + Kafka topic 消费逻辑

**验证方式**：新 Parquet 文件入湖后，30 秒内 DataHub UI 出现对应 dataset；对比 Phase 1 需手动跑脚本。

---

### 6.9 模块九：自动血缘采集（演示 10 分钟，归属 Phase 2）

**目标**：从「手工 `lineage_recipe.yaml`」升级为「Spark/Flink 任务自动解析 SQL 产出 lineage aspect」。

| 演示点 | Phase 1（当前） | Phase 2（升级后） |
|--------|---------------|-----------------|
| 血缘定义 | 手工 YAML（`lineage_recipe.yaml`），5 条边 | Spark/Flink 任务从 SQL 解析 FROM/JOIN 自动产出，理论上覆盖所有 DWD/DWA 表 |
| 血缘格式 | 手工写入 GMS upstreamLineage aspect | OpenLineage 标准，DataHub actions 服务消费 |
| 血缘更新 | 每次改 recipe 手动跑 `emit_lineage.py` | DWD/DWA ETL 任务完成后自动追加，无需人工 |
| 血缘覆盖 | 5 条（手工维护） | 理论上 N×M 条（ETL 任务自动发现） |

**Phase 1 教学**：`notebook/module1.ipynb` 第 4 节（血缘图 + 5 条边的手工录入）

**Phase 2 教学**：展示 OpenLineage 配置 + Spark 任务血缘截图（DataHub UI 自动刷新）

**验证方式**：新建 1 张 DWD 表后，无需手动跑脚本，DataHub UI Lineage 标签页在 ETL 任务完成后自动出现上游/下游。

**待验证风险**：DataHub v1.6 的 upstreamLineage aspect 是否支持 OpenLineage 格式；如不支持需自定义 emitter。

---

### 6.10 模块十：定时质量监控（演示 10 分钟，归属 Phase 2）

**目标**：从「一次性 GE CLI」升级为「定时任务 + 持久化报告 + Owner 通知」。

| 演示点 | Phase 1（当前） | Phase 2（升级后） |
|--------|---------------|-----------------|
| 执行方式 | 手动跑 `scripts/run_great_expectations.py` | Airflow / Cron 每日凌晨自动跑 |
| 报告存储 | CLI 输出在终端，丢了就没 | 持久化 JSON/HTML 报告（MinIO 或 NFS） |
| 告警触发 | 看到分数低，自己判断 | 分数低于阈值（< 70）自动发邮件给 Owner |
| 趋势历史 | 只有单次跑分 | 每次跑分写入时序库（ClickHouse），支持分数趋势图 |

**Phase 1 教学**：`notebook/module1.ipynb` 第 2 节（跑 GE → 看评分卡）

**Phase 2 教学**：Airflow DAG 截图 + 邮件告警示例 + ClickHouse 分数趋势折线图

**验证方式**：执行 DAG 后，邮件收到告警（若分数 < 70）；ClickHouse 中查询历史分数趋势。

---

### 6.11 模块十一：主题域 DWD（演示 10 分钟，归属 Phase 2）

**目标**：从「按系统分 DWD 表」升级为「按业务主题重组 DWD 表」。

| 演示点 | Phase 1（当前） | Phase 2（升级后） |
|--------|---------------|-----------------|
| 表组织方式 | `dwd/sap_erp/dwd_vbak`（按系统分） | `dwd/sales/vbak` / `dwd/production/tags`（按主题分） |
| 主题域维表 | 无 | 矿井维表、客户维表（来自 6.1 主数据标准化） |
| 主题域数量 | 1（不分主题） | 首批：销售主题（vbak/vbap/kna1）+ 生产主题（tags/samples） |
| 跨主题关联 | 需要跨目录 JOIN | 同一主题目录下 JOIN；跨主题通过维表关联（来自 6.1） |

**Phase 1 教学**：`notebook/module1.ipynb` 第 3 节（ODS → DWD 入湖脚本，按系统分目录）

**Phase 2 教学**：展示新目录结构 + 主题域维表（来自 6.1）+ 清洗规则按主题定义

**验证方式**：`data/lakehouse/dwd/` 下存在 `sales/` 和 `production/` 两个子目录；维表在 `dwd/_dimensions/` 目录。

---

### 6.12 模块十二：跨系统 DWA + OLAP 即席查询（演示 10 分钟，归属 Phase 2）

**目标**：从「单系统 DWA 宽表 + DuckDB」升级为「4 表 JOIN 跨系统产销宽表 + ClickHouse Materialized View + Superset 看板」。

| 演示点 | Phase 1（当前） | Phase 2（升级后） |
|--------|---------------|-----------------|
| DWA 宽表 | 3 张单系统宽表（`dwa_sales_daily` / `dwa_tag_alarm` / `dwa_coal_quality`） | 1 张跨系统产销宽表 `dwa_sales_production`（PI生产 + LIMS煤质 + SAP订单 + KNA1客户，依赖 6.1 矿井/客户维表） |
| 查询引擎 | DuckDB（内存 CLI） | ClickHouse / Doris（物化视图自动刷新） |
| 可视化 | DuckDB → CSV → Excel 透视 | Superset 看板切换维度实时出图 |
| 分析场景 | 产销对比需自己写 JOIN | 看板内置 4 个场景（产销对比 / 煤质定价 / 安全趋势 / 订单履约） |

**Phase 1 教学**：`notebook/module1.ipynb` 第 5 节（DuckDB 查 DWA + 4 个分析场景示例）

**Phase 2 教学**：Superset 看板截图（4 个场景）+ ClickHouse Materialized View 定义

**验证方式**：在 Superset 看板中切换矿井/煤种/时间维度，实时看到指标变化；跨矿井产销对比图一键出数。

---

### 6.13 模块十三（占位，归属 Phase 3）

> Phase 3 尚未设计。预期主题：Flink 实时质量监控 + 告警工单集成。

---

### 6.14 模块十四（占位，归属 Phase 3）

> Phase 3 尚未设计。预期主题：RBAC + ABAC 安全分级与字段级脱敏。

---

### 6.15 模块十五（占位，归属 Phase 3）

> Phase 3 尚未设计。预期主题：自助分析与 AI 增强（LLM 根因定位）。

