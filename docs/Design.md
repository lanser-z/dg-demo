# A公司煤炭数据治理平台 — 技术架构设计

## 1. 架构设计原则

| 原则 | 说明 |
|------|------|
| **分层解耦** | 采集层、存储层、治理层、应用层各自独立，层间通过标准化接口通信 |
| **湖仓一体** | 原始数据入湖，加工数据按需入仓，避免数据冗余的同时保留灵活性 |
| **批流协同** | 历史批量分析和实时监控共用同一套存储引擎 |
| **开源优先** | 优先选用成熟开源组件，降低License成本，保留自主可控能力 |
| **渐进演进** | 架构支持从单模块逐步扩展为完整平台，不强求一步到位 |

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        接入层（API Gateway / Web UI）            │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌──────▼──────┐     ┌───────▼──────┐     ┌──────▼──────────┐
│  资产目录模块  │     │  质量监控模块  │     │   血缘追踪模块   │
│  DataHub     │     │ Great Expectations│   │  Apache Atlas  │
│  + 自研前端   │     │  + 自研告警引擎 │     │  + 自研可视化  │
└──────┬──────┘     └───────┬──────┘     └──────┬──────────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                      治理服务层（Governance Services）           │
│  元数据服务 / 质量引擎 / 血缘引擎 / 告警服务 / 权限服务          │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                      存储层（Storage Layer）                    │
│                                                                  │
│  ┌─────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  ODS    │  │    DWD     │  │    DWM     │  │    DWA    │  │
│  │  贴源层  │  │   主题层    │  │   汇总层    │  │   应用层    │  │
│  │ Delta   │  │  Delta     │  │  Delta     │  │  MySQL/   │  │
│  │ Lake    │  │  Lake      │  │  Lake      │  │  ClickHouse│ │
│  └────┬────┘  └──────┬─────┘  └──────┬─────┘  └─────┬──────┘  │
│       │                │                 │               │         │
│       └────────────────┴────────┬────────┴───────────────┘         │
│                                 │                                  │
└─────────────────────────────────┼──────────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────┐
│                      数据采集层（Ingestion Layer）                   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  SAP-ERP │  │ PI-System│  │   LIMS   │  │    OA    │        │
│  │  CDC采集  │  │  Kafka   │  │  API轮询  │  │  数据库   │        │
│  │ debezium │  │  Connect │  │          │  │  CDC     │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. 技术选型

### 3.1 数据存储：Delta Lake vs Apache Iceberg vs Hudi

| 维度 | Delta Lake | Apache Iceberg | Apache Hudi |
|------|-----------|---------------|-------------|
| **社区活跃度** | 高（Databricks主导） | 高（Netflix/AWS/Apple等） | 中（Uber主导） |
| **SQL支持** | 优秀（Spark SQL原生） | 较好（Spark/Presto/Trino） | 较好 |
| **事务支持** | ACID事务 | ACID事务 | ACID事务 |
| **时间旅行** | 支持 | 支持（快照隔离更完善） | 支持 |
| **Schema演进** | 支持 | 支持（更规范） | 支持 |
| **Cloud兼容性** | Databricks全家桶最优 | AWS/GCP/Azure均优 | AWS最优 |
| **本案适用性** | ★★★★★ | ★★★★ | ★★★ |

**选型结论：Delta Lake**

理由：
- Spark 是当前最成熟的批处理引擎，Delta Lake 与 Spark 集成度最高，配置最简
- OpenMC 社区在国内企业落地案例丰富，遇到问题容易找到参考
- 支持 Merge/Update/Delete，适合 PI 时序数据的增量写入和历史数据修正
- 与 MinIO（兼容S3协议）搭配，可构建私有化全开源数据湖

**备选方案**：若未来迁移至云厂商（AWS Glue / 阿里云MaxCompute），可无缝切换至 Iceberg（云厂商原生支持更好）。

---

### 3.2 元数据管理：Apache Atlas vs DataHub vs Collibra

| 维度 | Apache Atlas | DataHub | Collibra |
|------|-------------|---------|----------|
| **开源/商业** | 开源（Apache） | 开源（LinkedIn） | 商业 |
| **部署复杂度** | 高（依赖Hadoop生态） | 低（Docker compose） | SaaS/私有化 |
| **实时元数据** | 支持（Kafka总线） | 支持（Kafka/MCP） | 支持 |
| **血缘捕获** | 自动（Hook机制） | 自动（DataHub Lineage API） | 手动为主 |
| **API完善度** | REST API较完整 | GraphQL + REST | REST |
| **前端体验** | 一般（老旧） | 较好（React） | 优秀 |
| **国内落地** | 较多（Hadoop企业） | 快速增长 | 较少（价格因素） |
| **本案适用性** | ★★★★ | ★★★★★ | ★★★ |

**选型结论：DataHub**

理由：
- Docker Compose 一键部署，运维成本极低
- GraphQL API 设计现代，自研前端接入成本低
- LinkedIn 背书，社区活跃度高，版本迭代快
- 支持 Kafka 实时元数据推送，可接入 PI/SCADA 流数据
- 血缘模型基于节点-边（Node-Edge）设计，适合多系统复杂血缘建模

**注意**：Apache Atlas 的 Hook 机制在接入已有 Hadoop 生态的企业时有优势，若 A 公司未来引入 CDH/HDP 集群，可并行引入 Atlas 增强血缘采集。

---

### 3.3 数据质量：Great Expectations vs 自研规则引擎 vs DQ Hub

| 维度 | Great Expectations | 自研规则引擎 | DQ Hub（阿里） |
|------|------------------|-------------|---------------|
| **部署形式** | Python库 / Spark集成 | 服务部署 | 商业产品 |
| **规则写法** | Python DSL / JSON | 自定义DSL | 可视化配置 |
| **批测支持** | 优秀 | 依赖实现 | 优秀 |
| **实时检测** | 一般（需流组件） | 可按需开发 | 优秀 |
| **告警集成** | Slack/微信/邮件 | 自定义 | 内置 |
| **质量评分** | 支持（自定义指标） | 需自行实现 | 内置 |
| **学习曲线** | 中等（Python） | 高（需自研） | 低 |
| **本案适用性** | ★★★★ | ★★★ | ★★★ |

**选型结论：Great Expectations + 自研告警层**

理由：
- Great Expectations 是 Python 原生质量检测库，与 PySpark 集成良好，可无缝接入 Delta Lake 数据验证
- 规则以代码形式管理（而非黑盒配置），版本化管理方便追溯
- 支持与 PI 时序数据质量检测结合（`expect_column_values_to_be_between` 等）
- 告警和评分卡逻辑自行开发，保持灵活性

**架构集成方式**：

```python
# Great Expectations 与 Spark 批测集成示例
import great_expectations as ge

df = ge.dataset.SparkDFDataset(spark_df)

# 定义期望
df.expect_column_values_to_be_between(
    column="AD",
    min_value=5,
    max_value=50
)

df.expect_column_values_to_not_be_null(column="SAMPLE_ID")

# 执行验证并生成报告
results = df.validate()
```

---

### 3.4 消息队列：Kafka vs RabbitMQ

| 维度 | Apache Kafka | RabbitMQ |
|------|-------------|----------|
| **设计定位** | 分布式流平台 | 企业级消息代理 |
| **吞吐量** | 百万级/秒 | 万级/秒 |
| **消息持久化** | 天然持久化，偏移量管理 | 支持持久化 |
| **消费模式** | 发布-订阅（Consumer Group） | 队列 + 交换器 |
| **消息回溯** | 支持（从偏移量重读） | 不支持（仅重队） |
| **生态扩展** | Kafka Connect / Schema Registry | 插件机制 |
| **SCADA集成** | ★★★★★（工业协议适配） | ★★ |
| **本案适用性** | ★★★★★ | ★★ |

**选型结论：Apache Kafka**

理由：
- SCADA 系统普遍支持 Kafka 协议（工业互联网标准），零改造接入
- 高吞吐满足 PI 时序数据 1分钟/条的持续写入
- 消息回溯能力支持质量检测失败后的数据重放
- Kafka Connect 生态成熟，有现成的 Debezium CDC 连接器对接 SAP/Oracle

**备选**：若 SCADA 系统仅支持 MQTT，可在前端增加 MQTT Broker（Mosquitto），再桥接至 Kafka。

---

### 3.5 时序存储：TimescaleDB vs InfluxDB vs QuestDB

| 维度 | TimescaleDB | InfluxDB | QuestDB |
|------|-------------|----------|---------|
| **存储引擎** | PostgreSQL超表 | TSM引擎 | JDK列式 |
| **SQL支持** | 完整SQL（PostgreSQL兼容） | InfluxQL + SQL | 完整SQL |
| **压缩率** | 高 | 高 | 极高 |
| **写入性能** | 高（自动分块） | 高 | 极高（SIMD优化） |
| **连续查询** | 连续聚合自动化 | 原生CQ | SQL任务调度 |
| **生态集成** | Grafana / Superset | Grafana原生 | Grafana / Python |
| **本案适用性** | ★★★★★（已在PI中使用） | ★★★★ | ★★★ |

**选型结论：TimescaleDB**

理由：
- A 公司 PI-System 已使用 TimescaleDB，选型一致降低运维复杂度
- 完整的 PostgreSQL 生态，支持跨表 JOIN（可与 LIMS/OA 数据直接关联查询）
- 自动按时间分块（Chunk），按时间范围查询性能优秀
- 连续聚合（Continuous Aggregates）自动计算时序指标（如每班次/每日均值、峰值）
- 压缩比高（实测约 10:1），存储成本可控

---

### 3.6 批处理引擎：Apache Spark vs Flink

| 维度 | Apache Spark | Apache Flink |
|------|-------------|-------------|
| **编程模型** | RDD/Dataset API | DataStream API |
| **批流统一** | Spark Structured Streaming | 原生流批一体 |
| **延迟** | 准实时（~100ms） | 真正实时（<10ms） |
| **Exactly-once** | 支持 | 支持 |
| **状态管理** | Checkpoint | Checkpoint + 状态后端 |
| **SQL支持** | Spark SQL（成熟） | Flink SQL（发展中） |
| **成熟度** | 极高（10年+） | 高（5年+） |
| **学习成本** | 中 | 中高 |
| **Delta Lake集成** | 原生 | 需第三方连接器 |
| **本案适用性** | ★★★★★ | ★★★★ |

**选型结论：Apache Spark（历史批次） + Flink（实时流预处理）**

理由：
- Delta Lake 官方原生支持 Spark，无需额外适配
- SAP/PI 历史数据的清洗、转换以批处理为主，Spark 更成熟稳定
- Flink 负责 SCADA 实时流的预处理（如滑动窗口聚合、异常检测）
- 两者可共用 Kafka 作为数据总线，架构清晰

---

### 3.7 技术选型汇总

| 模块 | 推荐方案 | 备选方案 |
|------|---------|---------|
| 数据湖格式 | Delta Lake | Apache Iceberg |
| 元数据管理 | DataHub | Apache Atlas |
| 数据质量 | Great Expectations + 自研告警 | — |
| 消息队列 | Apache Kafka | — |
| 时序存储 | TimescaleDB | InfluxDB |
| 批处理 | Apache Spark | — |
| 流处理 | Apache Flink | Spark Structured Streaming |
| 对象存储 | MinIO（兼容S3） | HDFS |
| 调度 | Apache DolphinScheduler | Airflow |
| 可视化 | Grafana + Superset | Metabase |
| 配置管理 | Apollo / Nacos | — |

---

## 4. 分层架构设计

### 4.1 数据采集层

```
数据源 ──── CDC/流 ────> Kafka ────> Flink预处理 ────> Delta Lake (ODS)
                  │
                  └────> Debezium ──> Kafka Connect ──> Delta Lake (ODS)
```

**CDC方案（SAP-ERP / Oracle）**：

| 源端 | CDC工具 | 说明 |
|------|--------|------|
| Oracle | Debezium + Oracle CDC | 解析Redo Log，实时捕获变更 |
| SQL Server | Debezium SQL Server | 捕获INSERT/UPDATE/DELETE |
| MySQL | Debezium MySQL | 解析Binlog |
| PostgreSQL | Debezium PostgreSQL | 逻辑复制（10+支持） |
| PI-System | Kafka Connect PI System | OSIsoft官方连接器 |
| LIMS | API轮询 + 时间戳比对 | 无CDC接口，定期拉取 |
| OA | Debezium（MySQL） | 法务系统多为MySQL |

**增量识别策略**：
- 具备时间戳字段的表：`WHERE updatetime > last_sync_time`
- 无时间戳但有主键：`CDC (Debezium)` 自动捕获
- PI时序数据：`WHERE timestamp > last_sync_timestamp`

### 4.2 贴源层（ODS）

设计原则：与源系统表结构保持一致，仅做类型统一和CDC审计字段追加。

```python
# ODS表命名规范
ods_{sys_code}_{table_name}

# ODS公共审计字段
class ODSMixin:
    etl_time: datetime       # ETL执行时间
    source_system: str        # 源系统标识
    source_pk: str            # 源端主键（复合主键用_拼接）
    is_deleted: str           # Y=已删除 N=有效
    dbtime: datetime          # 源系统时间（业务时间）
```

**PI-System ODS设计**：

```sql
CREATE TABLE ods_pi_tags (
    tag         VARCHAR(100),      -- 标签名 M001_FACE_A_WAGAS
    timestamp   TIMESTAMPTZ,      -- 时间戳（UTC）
    value       DOUBLE PRECISION,  -- 测值
    status      INTEGER,           -- PI状态码（-1=缺失）
    mine_code   VARCHAR(10),       -- 矿井编码（M001）
    face_code   VARCHAR(20),       -- 工作面编码
    etl_time    TIMESTAMPTZ,
    source_system VARCHAR(20) DEFAULT 'PI',
    PRIMARY KEY (tag, timestamp)
);
```

### 4.3 主题层（DWD）

设计原则：面向业务实体建模，统一编码体系，建立主数据关联。

**核心主题表**：

| 主题 | 表名 | 说明 |
|------|------|------|
| 销售 | dwd_sales_order | 订单主数据，统一客户/矿井编码 |
| 生产 | dwd_production_tag | 标准化PI标签，矿井名称统一 |
| 煤质 | dwd_coal_quality | LIMS标准化，煤种分类统一 |
| 设备 | dwd_equipment_status | SCADA设备状态标准化 |
| 流程 | dwd_oa_flow | OA流程标准化，编码规则统一 |

**DWD关键处理**：

```python
# 矿井编码标准化映射
MINE_MAPPING = {
    "M001": {"name": "鄂尔多斯一号煤矿", "erp_code": "1001", "pi_code": "M001"},
    "M002": {"name": "榆林李家沟煤矿", "erp_code": "1002", "pi_code": "M002"},
    ...
}

# DWD清洗示例：VBAP关联KNA1，补全客户标准名称
def dwd_sales_order():
    vbak = spark.read.delta(".../ods_sap_vbak")
    kna1 = spark.read.delta(".../ods_sap_kna1")

    df = vbak.join(
        kna1.withColumnRenamed("NAME1", "CUSTOMER_NAME_STANDARD"),
        on="KUNNR",
        how="left"
    )

    # 标记未匹配客户（数据质量问题）
    df = df.withColumn("IS_CUSTOMER_MATCHED",
                       F.when(F.col("CUSTOMER_NAME_STANDARD").isNotNull(), "Y").otherwise("N"))

    return df
```

### 4.4 汇总层（DWM）

设计原则：按分析主题预计算通用指标，减少应用层查询重复计算。

**核心汇总表**：

| 汇总表 | 粒度 | 指标 |
|--------|------|------|
| dwm_production_daily | 矿井_日期 | 日产量、开机率、瓦斯均值/峰值 |
| dwm_sales_daily | 客户_煤种_日期 | 订单量、发货量、回款率 |
| dwm_coal_quality_grade | 矿井_煤种_月份 | 灰分均值、发热量均值、合格率 |
| dwm_alarm_monthly | 矿井_月份 | 报警次数、处置率、平均响应时长 |

### 4.5 应用层（DWA）

设计原则：面向具体业务场景，SQL或API直接可查。

| 应用 | 数据来源 | 使用方 |
|------|---------|--------|
| 产销分析看板 | dws_sales_production | 销售部 |
| 安全预警大屏 | dwd_production_tag | 安全部/调度中心 |
| 煤质结算报表 | dwd_coal_quality | 煤质中心/财务部 |
| 合同追溯查询 | dwd_oa_flow + dwd_sales_order | 法务部/审计部 |

---

## 5. ELT 数据加工

### 5.1 ELT 与 ETL 的本质区别

| 维度 | ETL（Extract-Transform-Load） | ELT（Extract-Load-Transform） |
|------|-----------------------------|------------------------------|
| 转换位置 | 在抽取层完成（独立计算集群） | 在目标库内完成（利用目标库算力） |
| 典型工具 | Informatica / DataStage | dbt / Spark SQL |
| 数据湖场景 | 源数据量大但转换简单 | 复杂业务逻辑，转换在数仓内完成 |
| 本案适用性 | 轻量级清洗（CDC前置） | 主题宽表构建（主要场景） |

**本案 ELT 定位**：以 Delta Lake 为承载，Spark 作为执行引擎，dbt 作为转换编排层（dbt-core 支持 Spark 适配器），实现从 ODS → DWD → DWM 的分层加工。

### 5.2 ELT 分层模型

```
ODS（贴源层）  ──[清洗/去重]──▶  DWD（主题层）  ──[聚合/指标]──▶  DWM（汇总层）
  │                          │                              │
  │ 保持原始结构              │ 统一编码体系                  │ 预计算事实表
  │ CDC审计字段               │ 主数据关联                   │ 维度退化
  │ 无业务逻辑                │ 业务实体建模                 │ 公共指标复用
```

### 5.3 核心 ELT 作业设计

**作业一：矿井生产日榜（ODS_PI → DWD_PRODUCTION）**

```sql
-- dbt model: dwd_production_daily.sql
{{ config(materialized='table', partition_by=['production_date']) }}

WITH source AS (
    SELECT
        tag,
        timestamp::DATE                             AS production_date,
        mine_code,
        face_code,
        AVG(value)                                 AS avg_wagas,
        MAX(value)                                 AS max_wagas,
        COUNTIF(status = 0)                        AS valid_points,
        COUNT(*)                                   AS total_points,
        -- PI系统每5分钟1440点，折算为每日开机时长
        COUNTIF(status = 0) * 5 / 60              AS running_hours
    FROM {{ source('ods_pi', 'tags') }}
    WHERE tag LIKE '%_WAGAS'
      AND timestamp >= '2022-01-01'
    GROUP BY tag, timestamp::DATE, mine_code, face_code
)

SELECT
    production_date,
    mine_code,
    SUM(valid_points)                             AS daily_valid_points,
    SUM(valid_points) * 5 / 60                   AS daily_running_hours,
    MAX(max_wagas)                               AS daily_max_wagas,
    AVG(avg_wagas)                               AS daily_avg_wagas,
    -- 开机率（理论日运行时长24h）
    SUM(valid_points) * 5 / 60 / 24             AS availability_rate,
    CURRENT_TIMESTAMP()                           AS etl_time
FROM source
GROUP BY production_date, mine_code
```

**作业二：产销一体化宽表（DWD层跨系统关联）**

```sql
-- dbt model: dwd_sales_production_wide.sql
{{ config(materialized='incremental', partition_by=['dt']) }}

WITH production AS (
    SELECT
        production_date,
        mine_code,
        SUM(daily_valid_points)   AS pi_valid_points,
        SUM(daily_running_hours)  AS pi_running_hours,
        MAX(daily_max_wagas)     AS pi_max_wagas
    FROM {{ ref('dwd_production_daily') }}
    {% if is_incremental() %}
    WHERE production_date > (SELECT MAX(production_date) FROM {{ this }})
    {% endif %}
    GROUP BY production_date, mine_code
),

lims AS (
    SELECT
        test_date                         AS test_date,
        mine_code,
        AVG(AD)                           AS avg_ash_pct,     -- 灰分
        AVG(QGR_AD)                      AS avg_calorific,    -- 发热量
        COUNT(*)                          AS sample_count
    FROM {{ ref('dwd_coal_quality') }}
    GROUP BY test_date, mine_code
),

orders AS (
    SELECT
        ERDAT                             AS order_date,
        KUNNR                             AS customer_id,
        VKORG                             AS sales_org,
        NETWR                             AS order_amount,
        AUART                             AS order_type
    FROM {{ source('ods_sap', 'vbak') }}
),

SELECT
    p.production_date                     AS dt,
    p.mine_code,
    prod.pi_running_hours,
    prod.pi_max_wagas,
    l.avg_ash_pct,
    l.avg_calorific,
    COALESCE(SUM(o.order_amount), 0)    AS daily_order_amount,
    COUNT(DISTINCT o.customer_id)         AS daily_customer_count
FROM production p
LEFT JOIN lims l
    ON p.production_date = l.test_date
    AND p.mine_code = l.mine_code
LEFT JOIN orders o
    ON p.production_date = o.order_date
GROUP BY p.production_date, p.mine_code,
         prod.pi_running_hours, prod.pi_max_wagas,
         l.avg_ash_pct, l.avg_calorific
```

### 5.4 增量 ELT 策略

| 层级 | 增量策略 | 说明 |
|------|---------|------|
| ODS | CDC（Debezium）或时间戳比对 | 仅追回增量/变更 |
| DWD | 快照全量 + 时间戳过滤 | 主键覆盖，保留历史版本 |
| DWM | 增量物化视图 | 基于 DWD 增量计算当日汇总 |
| DWA | 按需查询 | 不预计算，实时聚合 |

```python
# 增量 ELT 调度逻辑
def elt_daily_run(target_date: str):
    # Step 1: ODS 增量拉取（仅增量）
    ods_pi = extract_pi_incremental(target_date)    # 按 timestamp >= T-1 拉取

    # Step 2: DWD 清洗写入（Merge 模式）
    dwd_prod = transform_production(ods_pi)
    spark.mergeInto(
        table="delta.lake/dwd_production_daily",
        source=dwd_prod,
        condition="source.tag = target.tag AND source.production_date = target.production_date",
        set={"value": "source.value", "etl_time": "current_timestamp()"}
    )

    # Step 3: DWM 增量汇总（当日数据替换）
    dwm_prod = aggregate_production_daily(target_date)
    dwm_prod.write.format("delta").mode("overwrite").partitionBy("production_date")...

    # Step 4: 触发质量检测（ELT任务完成后）
    trigger_quality_check(f"DWD/dwd_production_daily/{target_date}")
```

### 5.5 回溯处理（Backfill）

当主数据标准变更时，需要对历史数据进行回溯重算：

```bash
# 使用 dbt 进行回溯
dbt run --select dwd_sales_production --vars '{"start_date": "2022-01-01", "end_date": "2023-06-30"}'

# 使用 Spark 进行大规模回溯
spark-submit \
    --master yarn \
    --deploy-mode cluster \
    --conf spark.sql.shuffle.partitions=200 \
    elt_backfill.py \
    --layer dwd \
    --table production_daily \
    --start-date 2022-01-01 \
    --end-date 2023-06-30
```

---

## 6. OLAP 多维分析

### 6.1 技术选型：ClickHouse vs Apache Druid vs Doris

| 维度 | ClickHouse | Apache Druid | Apache Doris |
|------|-----------|--------------|--------------|
| **定位** | 列式分析数据库 | 时序OLAP | MPP分析数据库 |
| **写入模式** | 批量+实时 | 实时流优先 | 批量+实时 |
| **SQL支持** | 完整（MySQL兼容） | 有限（扩展SQL） | 完整（MySQL兼容） |
| **Join能力** | 弱（建议宽表） | 弱 | 强 |
| **物化视图** | 支持（物化视图+预聚合） | 支持（数据立方） | 支持 |
| **数据量** | 十亿-万亿级 | 十亿级 | 十亿-千亿级 |
| **生态** | 独立 | 依赖Kafka/HDFS | 独立 |
| **运维复杂度** | 中 | 高 | 低 |
| **本案适用性** | ★★★★ | ★★★ | ★★★★★ |

**选型结论：Apache Doris（原百度 DorisDB）**

理由：
- MySQL 协议兼容，现有 BI 工具（FineBI / Tableau）零改造直连
- 向量化和列式存储兼顾，单节点即可支撑万级 QPS
- Rollup 和物化视图支持查询加速，适合大宽表分析场景
- 部署简单（FE+BE 架构，3节点起步），运维成本低
- 支持 Spark Load 和 Stream Load，Delta Lake 数据可直接导入

**备选**：若未来分析数据量超过 500 亿行，可切换至 ClickHouse（超大规模列存分析能力更强）。

### 6.2 OLAP 数据模型

采用星型模型（Star Schema）：

```
                    ┌─────────────────┐
                    │  dwm_fact_sales │  事实表（产销）
                    │  产销一体化主表  │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐  ┌───────▼──────┐  ┌──────▼──────┐
   │ dim_mine     │  │  dim_time    │  │ dim_customer │
   │ 矿井维度表   │  │  时间维度表  │  │ 客户维度表  │
   └──────────────┘  └──────────────┘  └──────────────┘
```

**事实表（dwm_fact_sales）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| dt | DATE | 日期（分区键） |
| mine_code | VARCHAR(10) | 矿井编码 |
| coal_type | VARCHAR(20) | 煤种 |
| customer_id | VARCHAR(10) | 客户编码 |
| daily_output_t | DECIMAL(15,2) | 日产量（吨） |
| daily_order_t | DECIMAL(15,2) | 日订单量（吨） |
| daily_shipment_t | DECIMAL(15,2) | 日发货量（吨） |
| daily_order_amount_cny | DECIMAL(18,2) | 日订单金额（元） |
| avg_wagas_pct | DECIMAL(6,3) | 日均瓦斯浓度 |
| max_wagas_pct | DECIMAL(6,3) | 日最大瓦斯浓度 |
| avg_ash_pct | DECIMAL(6,2) | 日均灰分 |
| avg_calorific_mjkg | DECIMAL(8,2) | 日均发热量 |
| order_cnt | INT | 日订单笔数 |
| customer_cnt | INT | 日客户数 |

### 6.3 物化视图设计（查询加速）

```sql
-- 月度汇总物化视图（自动刷新）
CREATE MATERIALIZED VIEW mv_sales_monthly
BUILD IMMEDIATE REFRESH COMPLETE
AS
SELECT
    toStartOfMonth(dt)          AS stat_month,
    mine_code,
    coal_type,
    SUM(daily_output_t)         AS total_output_t,
    SUM(daily_order_amount_cny) AS total_amount_cny,
    AVG(avg_wagas_pct)          AS avg_wagas,
    AVG(avg_ash_pct)            AS avg_ash,
    COUNT(DISTINCT customer_id)  AS customer_cnt
FROM dwm_fact_sales
GROUP BY toStartOfMonth(dt), mine_code, coal_type;

-- 订单履约分析物化视图
CREATE MATERIALIZED VIEW mv_order_fulfillment
BUILD IMMEDIATE REFRESH COMPLETE
AS
SELECT
    toStartOfMonth(dt)            AS stat_month,
    mine_code,
    COUNTIF(delivery_date <= promise_date) * 1.0 / COUNT(*) AS fulfillment_rate,
    AVG(delivery_date - promise_date)                        AS avg_delay_days
FROM dwm_fact_sales f
JOIN dim_order o ON f.order_id = o.order_id
GROUP BY toStartOfMonth(dt), mine_code;
```

### 6.4 典型 OLAP 查询场景

**场景一：产销对比（年-月-日钻取）**

```sql
-- ClickHouse / Doris SQL
SELECT
    {% if granularity == 'month' %} toStartOfMonth(dt)
    {% elif granularity == 'day' %} dt
    {% else %} 'ALL'
    {% endif %} AS period,
    mine_code,
    SUM(daily_output_t)       AS output_t,
    SUM(daily_order_amount_cny) / SUM(daily_output_t) AS avg_price_cny_t,
    -- 产销比（>1说明库存积压）
    SUM(daily_order_t) / NULLIF(SUM(daily_output_t), 0) AS sales_output_ratio
FROM dwm_fact_sales
WHERE dt BETWEEN '{{ start_date }}' AND '{{ end_date }}'
  AND mine_code IN ({{ mine_codes }})
GROUP BY
    {% if granularity == 'month' %} toStartOfMonth(dt)
    {% elif granularity == 'day' %} dt
    {% else %} 1
    {% endif %},
    mine_code
ORDER BY period DESC, output_t DESC
```

**场景二：煤质与价格相关性分析**

```sql
SELECT
    coal_type,
    -- 按灰分区间分组
    CASE
        WHEN avg_ash_pct < 8   THEN '优质（灰分<8%）'
        WHEN avg_ash_pct < 12  THEN '良好（8-12%）'
        WHEN avg_ash_pct < 20  THEN '中等（12-20%）'
        ELSE '较差（>20%）'
    END AS ash_grade,
    COUNT(*)                    AS sample_count,
    AVG(daily_order_amount_cny / NULLIF(daily_output_t, 0)) AS avg_price_cny_t,
    CORR(avg_ash_pct, daily_order_amount_cny / NULLIF(daily_output_t, 0)) AS ash_price_corr
FROM dwm_fact_sales
WHERE coal_type IN ('精煤', '原煤')
GROUP BY coal_type, ash_grade
ORDER BY coal_type, ash_grade;
```

**场景三：安全告警趋势（多维度下钻）**

```sql
SELECT
    toStartOfMonth(dt)    AS alarm_month,
    mine_code,
    SUM(CASE WHEN max_wagas_pct > 0.8 THEN 1 ELSE 0 END)  AS wagas_alarm_cnt,
    SUM(CASE WHEN max_wagas_pct > 1.0 THEN 1 ELSE 0 END)  AS wagas_danger_cnt,
    AVG(max_wagas_pct)   AS avg_peak_wagas,
    -- 环比上月
    AVG(max_wagas_pct) /
        LAG(AVG(max_wagas_pct)) OVER (
            PARTITION BY mine_code ORDER BY toStartOfMonth(dt)
        ) - 1                                    AS mom_change_pct
FROM dwm_fact_sales
WHERE dt >= DATE_SUB(CURRENT_DATE, INTERVAL 12 MONTH)
GROUP BY toStartOfMonth(dt), mine_code
ORDER BY alarm_month DESC;
```

### 6.5 BI 可视化集成

```yaml
# Superset 接入配置（通过 Doris MySQL 协议）
database:
  name: doris_dwm
  engine: mysql+pymysql
  host: doris-fe.internal
  port: 9030
  database: dwm
  username: readonly
  password: ***

# 预定义看板（Dashboard）
dashboards:
  - name: 产销分析看板
    charts:
      - 各矿井日产量趋势（折线图）
      - 产销比热力图（矿井×月份）
      - 订单金额分布（饼图）
      - 客户TOP10排名（条形图）

  - name: 安全监控看板
    charts:
      - 瓦斯浓度日峰值曲线（各矿井）
      - 月度告警次数排名（柱状图）
      - 高风险矿井标识（GIS热力图）
```

---

## 7. 核心模块设计

### 7.1 元数据采集与同步

```
源系统 ──> DataHub Hook/SDK ──> DataHub GraphQL API ──> DataHub Metadata Store (MySQL/Postgres)
                                    │
                                    ├──> 自研前端（资产目录展示）
                                    └──> 血缘引擎（血缘构建）
```

**采集策略**：

| 采集方式 | 适用场景 | 实现方式 |
|---------|---------|---------|
| 自动Hook | Spark/Flink作业表级血缘 | Spark Listener API |
| CDC监听 | 源端DDL变更（新增字段/表） | Debezium监控DataHub元数据库 |
| API拉取 | 外部系统元数据（PI资产清单） | 定时任务调用PI REST API |
| 手工录入 | 业务描述/Owner/标签 | 前端表单 |

### 7.2 血缘链路设计

**纵向血缘（表-列级）**：

```json
{
  "guid": "col-guid-001",
  "typeName": "DataSet",
  "attributes": {
    "qualifiedName": "delta.`/lake/ods_sap_vbap` VBELN",
    "name": "VBELN",
    "owner": "销售部"
  },
  "columnMapping": [
    {
      "sourceColumn": "VBELN",
      "targetColumn": "VBELN",
      "transform": "direct"
    },
    {
      "sourceColumn": "MATNR",
      "targetColumn": "MATNR",
      "transform": "direct"
    }
  ]
}
```

**横向血缘（跨系统追溯）**：

```python
# 矿井编码统一映射（跨系统关联的核心）
MINE_LINK = {
    # SAP         # PI            # LIMS
    "M001":    <-> "M001":     <-> "M001",
    "M002":    <-> "M002":     <-> "M002",
    "M003":    <-> "M003":     <-> "M003",
}

# 关联链路：
# PI.tag (含MINE_CODE)  --MINE_LINK-->
# LIMS.MINE_CODE       --CHARG/BATCH-->
# SAP_VBAP.MATNR/CHARG --VBELN-->
# SAP_VBAK.KUNNR       --KUNNR-->
# SAP_KNA1.NAME1       --FLOW_ID-->
# OA.DOC_FLOW
```

### 7.3 数据质量规则引擎

**规则分类**：

| 类别 | 示例 | 触发方式 |
|------|------|---------|
| 完整性 | 非空约束、主键唯一 | 批次/实时 |
| 一致性 | 外键关联、枚举值范围 | 批次 |
| 时效性 | 数据延迟监控（T+1） | 批次 |
| 准确性 | 业务逻辑校验（灰分区间） | 批次/实时 |
| 唯一性 | 重复行检测 | 批次 |

**规则执行流程**：

```
质量规则定义（YAML/JSON）
        │
        ▼
规则引擎解析 ───> Spark/Flink 分布式执行
        │
        ├──> 结果写入 quality_results 表
        │
        ├──> 问题行写入 quality_issues 表（含责任部门）
        │
        └──> 触发告警（Slack/微信/邮件）
```

### 7.4 告警与问题工单

```python
# 告警触发条件
ALERT_RULES = {
    "P0_阻断": {
        "condition": "issue.severity == 'P0'",
        "channels": ["电话", "短信", "微信"],
        "timeout_minutes": 30
    },
    "P1_严重": {
        "condition": "issue.severity == 'P1'",
        "channels": ["微信", "邮件"],
        "timeout_minutes": 240
    },
    "P2_一般": {
        "condition": "issue.severity == 'P2'",
        "channels": ["邮件"],
        "timeout_minutes": 1440
    }
}

# 问题工单状态机
STATE_MACHINE = {
    "NEW":      {"next": ["ASSIGNED", "CLOSED"], "owner": "系统自动分配"},
    "ASSIGNED": {"next": ["RESOLVED", "REOPENED"], "owner": "责任部门"},
    "RESOLVED": {"next": ["CLOSED", "REOPENED"], "owner": "提交人确认"},
    "REOPENED": {"next": ["ASSIGNED"], "owner": "质量管理员"},
    "CLOSED":   {"next": [], "owner": "完结"}
}
```

---

## 8. 安全设计

### 8.1 访问控制模型

采用 RBAC + ABAC 混合模型：

```python
# 角色定义（RBAC）
ROLES = {
    "数据治理管理员": ["*"],                           # 全权限
    "安全管理员":    ["core_assets", "quality_*"],    # 核心资产+质量
    "业务分析师":    ["important_assets", "dwa_*"],   # 重要资产+应用层
    "审计员":        ["*_audit"],                     # 仅审计视图
}

# 属性定义（ABAC）
ABAC_POLICY = {
    "敏感字段脱敏": {
        "fields": ["STCD1", "ID_CARD"],  # 信用代码/身份证
        "roles": ["业务分析师"],
        "action": "mask",                 # 脱敏展示
    },
    "数据导出控制": {
        "max_rows": 10000,
        "roles": ["业务分析师"],
        "requires_approval": True,
    }
}
```

### 8.2 数据分级保护

```
核心资产（PI告警阈值、SCADA控制指令）
  ├─ 加密存储（AES-256）
  ├─ 访问审批流程
  ├─ 操作审计日志（所有人）
  └─ 防批量导出（单次≤100行）

重要资产（订单、LIMS、煤质数据）
  ├─ 访问控制（RBAC）
  ├─ 操作审计（写操作）
  └─ 防批量导出（单次≤10000行，需审批）

一般资产（OA流程、历史归档）
  ├─ 基础访问控制
  └─ 操作审计（可选）
```

---

## 9. 部署架构

### 9.1 基础环境

| 组件 | 规格 | 说明 |
|------|------|------|
| Master节点 × 1 | 8C/32G | 调度/管理服务 |
| Worker节点 × 3 | 16C/64G | 计算/存储 |
| MinIO 节点 × 3 | 4C/16G | 对象存储（纠删码模式） |
| Kafka 集群 × 3 | 8C/32G | 消息队列 |
| TimescaleDB | 8C/64G | 时序存储（PI数据） |

### 9.2 容器化部署

```yaml
# docker-compose.yml（DataHub + 元数据服务）
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:7.17
    environment:
      - discovery.type=single-node
    mem_limit: 2g

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=datahub

  datahub:
    image: acryldata/datahub-frontend-embedded:latest
    depends_on:
      - mysql
      - elasticsearch
    ports:
      - "9002:9002"

  kafka:
    image: confluentinc/cp-kafka:7.4
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
```

---

## 10. 演进路径

> 本节已删除。Phase 实现路径的唯一权威定义在 `docs/Background.md` 第 5 节「后续治理路径」。
> 本文档专注技术选型与架构设计，不重复定义 Phase 计划。
> 如需了解 Phase 2 包含哪些工作（DataHub 接入 / 自动血缘 / GE Checkpoint 化 / DWD 主题层 / 跨系统宽表 / OLAP 引擎 / 可视化看板），请查阅 `docs/Background.md` 第 5 节。
