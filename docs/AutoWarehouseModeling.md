# 自动化数仓分层建模方案调研

> 场景：从原始 MySQL 数据库（600+ 表、6000+ 字段）自动构造 ODS -> DWD -> DWM -> DWA 数仓分层。
>
> 本文基于 2025-2026 年公开资料 + 开源仓库源码分析，对比主流方案并给出推荐。

---

## 1. 核心结论

**没有任何开源/商业工具能全自动从源库 Schema 生成完整 ODS -> DWD -> DWM -> DWA 分层。** 所有工具都只做 ODS 层（数据同步），DWD 及以上需要人工建模或 LLM 辅助。

| 自动化程度 | 方案 | 说明 |
|---|---|---|
| 95% 自动（商业） | WhereScape RED | 元数据驱动，端到端代码生成 |
| 80% 自动（商业） | Datavault Builder / Coalesce | AI agent + 模板 |
| 50-60% 半自动（开源） | **dbt + codegen + LLM**（推荐） | staging 半自动，DWD/DWA 用 LLM 骨架 |
| 30% 自动（开源） | SeaTunnel / DataX / Hop | 仅 ODS 同步 |
| 实验性 | 纯 LLM 驱动 | 上下文窗口 + 业务语义瓶颈 |

---

## 2. 方案对比矩阵

| 方案 | 类型 | ODS | DWD | DWM/DWA | 600表可行 | 开源 |
|---|---|---|---|---|---|---|
| WhereScape RED | 商业 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ❌ |
| Datavault Builder | 商业 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | ❌ |
| Coalesce | 商业 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ | ❌ |
| 阿里 DataWorks | 商业 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ | ❌ |
| **dbt + codegen + LLM** | **开源** | **⭐⭐⭐** | **⭐⭐** | **⭐** | **✅** | **✅** |
| SeaTunnel / DataX | 开源 | ⭐⭐⭐⭐ | ❌ | ❌ | ✅ | ✅ |
| Apache Hop / InLong | 开源 | ⭐⭐⭐ | ⭐ | ❌ | ✅ | ✅ |
| 纯 LLM 驱动 | 实验性 | ⭐⭐ | ⭐ | ❌ | ⚠️ | ✅ |

---

## 3. 推荐方案：dbt + codegen + LLM + SeaTunnel CDC

### 选择理由

1. **全开源**，无商业许可成本
2. **dbt 生态最大**，社区活跃，600 表规模有企业实践（dbt Summit 700+ 源案例）
3. **codegen 可半自动生成 ODS staging**，LLM 辅助生成 DWD/DWA SQL 骨架
4. **与 DataHub 集成**，dbt 血缘自动写入 DataHub GMS

### 架构

```
MySQL 600+ 表
    │
    ▼  SeaTunnel CDC (generate_sink_sql + CREATE_SCHEMA_WHEN_NOT_EXIST)
ODS 层 (目标仓库 / Delta Lake)
    │
    ▼  dbt codegen generate_base_model (批量生成 staging SQL)
dbt Staging (ODS 镜像，列重命名/类型转换)
    │
    ▼  LLM 生成清洗 SQL 骨架 -> 人工审核
dbt Intermediate (DWD 清洗层)
    │
    ▼  LLM 生成聚合 SQL 骨架 -> 人工审核
dbt Mart (DWM/DWA 宽表)
    │
    ▼  dbt run (DAG 编排)
DataHub (dbt artifact -> 血缘自动采集)
```

### 各层自动化策略

| 层 | 工具 | 自动化 | 人工介入 |
|---|---|---|---|
| ODS | SeaTunnel CDC `generate_sink_sql=true` + `CREATE_SCHEMA_WHEN_NOT_EXIST` | 90% | 仅配连接串 |
| Staging | dbt codegen `generate_base_model` | 80% | 审核列重命名 |
| DWD | LLM 生成清洗 SQL 骨架 + dbt 模型 | 50% | 审核清洗规则 |
| DWM/DWA | LLM 生成聚合 SQL 骨架 + dbt 模型 | 30% | 设计维度/度量 |

### dbt 分层与国内数仓对应

| dbt 官方分层 | 职责 | 国内数仓对应 |
|---|---|---|
| Staging | 轻量清洗、列重命名、一对一映射源表 | ODS / DWD 原始层 |
| Intermediate | 模块化业务逻辑、跨表联合、通用转换 | DWD 明细层 |
| Mart | 最终交付，维度/事实宽表 | DWM / DWA 汇总层 |

---

## 4. 600 表实施路径

### Phase 1: ODS 自动化（1-2 周）

SeaTunnel CDC 一次配置，600 表自动同步：

```hocon
source {
  MySQL-CDC {
    server-id = "5400-5404"
    username = "root"
    password = "xxx"
    table-names = ["db.*"]          # 通配 600+ 表
    base-url = "jdbc:mysql://..."
  }
}
sink {
  jdbc {
    generate_sink_sql = true         # 自动生成 INSERT
    schema_save_mode = "CREATE_SCHEMA_WHEN_NOT_EXIST"  # 自动建表
  }
}
```

### Phase 2: Staging 半自动（1 周）

dbt codegen 批量生成 staging SQL：

```bash
# 单表生成
dbt run-operation codegen.generate_base_model \
  --args '{"source_name":"mysql_src","table_name":"orders"}'

# Python 脚本批量调 600 次
```

### Phase 3: LLM 辅助 DWD/DWA 生成（2-4 周）

自研脚本：MySQL schema + LLM -> dbt model SQL

```python
for table in mysql_tables:
    schema = read_mysql_schema(table)         # information_schema
    prompt = build_dwd_prompt(schema, table)  # 清洗规则骨架
    sql = llm.chat(prompt)                    # LLM 生成
    save(f"models/dwd/{table}.sql", sql)      # 人工审核后入库
```

### Phase 4: DataHub 集成（1 周）

dbt run -> dbt artifact (manifest.json) -> DataHub dbt connector -> 血缘自动入 GMS

---

## 5. 各工具详细评估

### 5.1 dbt + codegen

| 维度 | 评估 |
|---|---|
| 自动生成 Staging（ODS） | ⭐⭐⭐ codegen 可生成，需先定义 source |
| 自动生成 Intermediate（DWD） | ⭐⭐ 跨表 JOIN 和业务逻辑无法自动推断 |
| 自动生成 Mart（DWA） | ⭐ 维度建模完全依赖人工 |
| MySQL 直连 | ⭐⭐ MySQL 非 dbt native adapter，需 CDC 中转 |
| 600 表规模 | ⭐⭐⭐ codegen + 自研脚本可规模化 |
| LLM 辅助 | ⭐⭐⭐ 目前仅辅助生成描述，可扩展生成 SQL 骨架 |

**codegen 核心宏**：
- `generate_source`：从已注册 source 生成 sources.yml
- `generate_base_model`：生成 staging SQL 模板
- `generate_model_yaml`：生成 schema.yml 属性文件

**企业案例**：dbt Summit 分享过 700+ 源自动化实践（YAML 配置模板 + Python 脚本 + GitHub Action PR）

### 5.2 WhereScape RED（商业标杆）

| 维度 | 评估 |
|---|---|
| 自动化程度 | 85-100% 代码自动生成 |
| 建模方式 | 元数据驱动，模板化（Stage/Dimension/Fact/Satellite/Hub/Link） |
| 支持架构 | Kimball 维度建模 + Data Vault 2.0 |
| 源 Schema 探测 | ✅ 捕获源元数据，自动 profiling |
| 目标平台 | Snowflake / SQL Server / Oracle / Teradata / Databricks |
| 文档 | 自动生成 + 版本化 lineage |
| 开源 | ❌ 商业产品 |

### 5.3 SeaTunnel / DataX / Hop（数据集成层）

| 工具 | ODS 同步 | 自动建表 | DWD 清洗 | JOIN | CDC |
|---|---|---|---|---|---|
| SeaTunnel | ✅ CDC + 批量 | ✅ `CREATE_SCHEMA_WHEN_NOT_EXIST` | ⚠️ 轻量（字段映射/过滤） | ❌ 单表 SQL only | ✅ |
| DataX | ✅ 批量 | ❌ 需目标表存在 | ❌ | ❌ | ❌ |
| Apache Hop | ✅ | ❌ | ⚠️ 模板 + 元数据注入 | ✅ | ✅ |
| Apache InLong | ✅ 批量+实时 | ✅ | ⚠️ TransformNode（人工规则） | ✅ | ✅ Flink-based |

**共同结论**：全部停留在 ODS 同步 + 轻量转换，DWD/DWA 聚合需下游工具（dbt / Flink SQL / Spark SQL）。

### 5.4 阿里 DataWorks（商业一站式）

- 内置五层：ODS / DIM / DWD / DWS / ADS
- 维度建模工具 + 检查器（命名规范自动校验）
- 数据集成（CDC + 批量）+ 数据开发（MaxCompute SQL）+ 调度
- 模板导入（开箱即用的行业模板）
- **但分层建模仍需人工设计**，工具只做执行和规范校验

### 5.5 纯 LLM 驱动（实验性）

| 挑战 | 说明 |
|---|---|
| 上下文窗口 | 600 表 + 6000 字段 schema 无法一次性喂给 LLM |
| 业务语义 | LLM 不理解"煤种""发热量"等业务概念 |
| 质量不稳定 | 数仓分层是连续变换，输出需大量人工校正 |
| 评估困难 | 生成的模型质量无客观标准 |

**最有希望的方向**：Data Vault + LLM（MDPI 2025 论文验证），Data Vault 的规则化建模（Hub/Satellite/Link）比 Kimball 维度建模更适合 LLM 生成。

### 5.6 DataHub 的角色

**DataHub 不能自动推荐分层**，定位是元数据存储 + 血缘记录层：

| 能做 | 不能做 |
|---|---|
| 接入 MySQL schema，拉取 600+ 表元数据 | 自动推荐"这张表该放哪层" |
| 记录表级 + 列级血缘（通过 dbt 集成） | 自动发现 MySQL 外键 -> JOIN 路径 |
| 手工打 ODS/DWD/DWA 标签，下游自动继承 | 自动推断"哪些表该合成 DWD 宽表" |
| 通过 dbt artifact 拿到转换 SQL | 自动生成 DWD -> DWA 聚合逻辑 |

**结论**：DataHub = 分层结果的可视化和查询层，不是分层逻辑的生产者。

---

## 6. 对比当前项目

| 维度 | 当前 Demo | 推荐方案 |
|---|---|---|
| ODS | 手动 glob Parquet | SeaTunnel CDC 自动同步 |
| DWD 清洗 | 硬编码 if-elif（cleaning.py） | dbt SQL 模型 + LLM 骨架 |
| DWA 聚合 | 硬编码 SQL 常量 | dbt SQL 模型 + LLM 骨架 |
| 新增 source | 2-3 小时（改 4 个文件） | 30 分钟（codegen + LLM） |
| 调度 | 手动 CLI | dbt run DAG |
| 血缘 | 手写 recipe YAML | dbt artifact 自动入 DataHub |
| 配置分散 | 4 个文件（cleaning + ingest + restructure + register） | 1 个 dbt project |

---

## 7. 参考资源

| 资源 | 说明 |
|---|---|
| [dbt codegen](https://github.com/dbt-labs/dbt-codegen) | 官方代码生成宏包 |
| [dbt Summit 700+ 源自动化](https://github.com/dbt-labs/dbt-core/discussions/5101) | 企业级规模实践 |
| [WhereScape RED](https://www.wherescape.com) | 商业 DWA 标杆（95% 代码生成） |
| [Datavault Builder](https://datavault-builder.com) | AI agent + Data Vault |
| [SeaTunnel generate_sink_sql](https://seatunnel.apache.org) | CDC + 自动建表 |
| [MDPI 2025: Data Vault + LLM](https://www.mdpi.com/2079-8954/13/9/811) | LLM 生成 Data Vault DDL 论文 |
| [SQLMorpher (LBNL 2023)](https://sdm.lbl.gov/oapapers/bigdata23-sharma.pdf) | LLM 做 schema mapping |
| [阿里 DataWorks 数仓分层](https://help.aliyun.com/zh/dataworks/user-guide/data-warehouse-layering) | 内置五层 + 维度建模 |
