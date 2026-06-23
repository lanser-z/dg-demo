## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 业务分析师 | 「我只想看日销售趋势，等 IT 排期要 3~5 天」，每次临时取数都要走需求流程 |
| 业务部门负责人 | 各部门自己用 Excel 从原始数据拼报表，口径不一致，互相质疑数据准确性 |
| 数据分析师 | 做跨系统分析（产销对比）要写 5 个 JOIN，矿井编码在 PI/SAP/LIMS 里还不统一，关联不上 |
| 运维工程师 | 现有 ETL 是批量夜维（T+1），想看当天数据只能等第二天早上 |
| 财务专员 | 月末结账时需要从 SAP 导出数据、人工核对 LIMS 煤质，手工活多、容易出错 |

---

## Ideas

- [ ] 想法 1：**构建 DWA 单系统汇总宽表** — 在 DWD 清洗层之上，按业务主题预聚合日销售汇总（`dwa_sales_daily`）、传感器告警排名（`dwa_tag_alarm`）、月度煤质报告（`dwa_coal_quality`），业务人员直接查宽表不用等 IT 排期
- [ ] 想法 2：**构建跨系统产销宽表** — 将 PI 生产实绩 × LIMS 煤质 × SAP 销售订单 × KNA1 客户主数据四表 JOIN，输出 `dwa_sales_production`，实现产销实时对比分析
- [ ] 想法 3：**升级 OLAP 引擎** — 用 ClickHouse 或 Doris 物化视图替代 DuckDB CLI，实现亚秒级查询响应 + 自动定时刷新
- [ ] 想法 4：**引入 Superset 可视化看板** — 业务人员自己拖拽维度切片，替代手工 Excel 报表，支持订阅和分享
- [ ] 想法 5：**构建定时 ETL 调度** — 从 T+1 升级为每小时增量，将数据延迟从 24 小时压缩到 1 小时以内
- [ ] 想法 6：**构建矿井/客户/物料维表** — 统一跨系统的编码体系（矿井 M001-M005 / 客户 KUNNR / 物料 MATNR），消除 JOIN 障碍
- [ ] 想法 7：**构建历史数据回溯重处理** — 当清洗规则调整时，自动用新规则重算历史 ODS 数据，无需重新抽取源系统

### 🔍 搜索验证结果

#### 关于 Idea 3（ClickHouse vs Doris）

**来源**：[State of Open Source Real-Time OLAP Systems 2025](https://www.pracdata.io/p/state-of-open-source-read-time-olap-2025)、[Velodb benchmark](https://www.velodb.io/blog/ultimate-olap-showdown-apache-doris-clickhouse-snowflake)

- **ClickHouse**：面向 OLAP 极致性能，单 binary 部署，运维简单；纯分析场景性能领先
- **Apache Doris**：基于 Google Mesa / Impala 血统，MySQL 兼容协议；JOIN 场景比 ClickHouse 快 **2.5 倍**（14 亿行规模）；支持 Iceberg；成本是 Snowflake/ClickHouse 的 **10~20%**
- **结论**：两者均是 Phase 2 OLAP 升级的有效选项。若分析场景 JOIN 多（产销宽表多表关联），Doris 优势明显；若追求运维极简，ClickHouse 更合适。**当前 Phase 1 DuckDB 验证可行性是正确选择，无需提前引入运维复杂度。**

#### 关于 Idea 5（Flink vs Spark Structured Streaming）

**来源**：[AWS Big Data Blog](https://aws.amazon.com/blogs/big-data/a-side-by-side-comparison-of-apache-spark-and-apache-flink-for-common-streaming-use-cases)、[OpenLineage Flink](https://openlineage.io/blog/flink-native-support)

- **Flink**：原生流处理，毫秒级延迟，支持事件时间和状态管理；Flink 2.0（2024.11）已支持 OpenLineage 原生集成
- **Spark Structured Streaming**：微批处理模式，延迟高于 Flink；但与现有 Spark 生态（Spark SQL / Delta Lake）高度兼容，运维复杂度低
- **结论**：对于 **T+1 → 小时级增量**的场景，Spark Structured Streaming 足够且运维成本更低；若后续升级到 Phase 3 实时告警（毫秒级），Flink 是必选项。**当前 Idea 5 描述"Flink 流式处理"对于"小时级批调度"是过度设计，应用 Spark Structured Streaming 更务实。**

#### 关于 DataHub 自动血缘采集（Background.md § 6.9 提到"待验证"）

**来源**：[DataHub OpenLineage 文档](https://docs.datahub.com/docs/lineage/openlineage)、DeepWiki 核查

- **已确认支持**：DataHub 通过 `acryl-spark-lineage` 插件支持 **Spark 任务自动血缘采集**（表级 + **列级**）；Flink 任务通过 OpenLineage 集成（v1.15~v1.18）；REST 端点可直接接收 OpenLineage 事件
- **重要澄清**：Background.md § 6.9 "待验证风险：DataHub v1.6 的 upstreamLineage aspect 是否支持 OpenLineage 格式"——**经核实已支持**，非待办项
- **结论**：模块三（module3.ipynb）中"自动血缘采集"从"手工 YAML"升级为"Spark 自动产出"是**可实现的**，非技术障碍，仅是落地工作量问题

---

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1    | **用户体验 / 可用性** | 业务取数从等待 3~5 天降至即时查询，用户满意度显著提升；消除部门间数据口径不一致问题 | ✅ 是 |
| 2    | **可扩展性 / 数据质量** | 跨系统产销宽表是 Phase 2 核心交付物，但依赖 Idea 6（主数据标准化）先行；当前矿井编码字面已一致可先做 PI×SAP 两表 JOIN 试点 | ⚠️ 条件满足后立即做 |
| 3    | **性能 / 可扩展性** | ClickHouse/Doris 向量化执行比 DuckDB 快 10~100 倍，支持亿级数据 OLAP；Doris 在 JOIN 场景快 2.5 倍且成本仅 10~20%；Phase 2 升级，当前 Phase 1 用 DuckDB 验证可行性是正确选择 | ⚠️ Phase 2 做 |
| 4    | **用户体验 / 可维护性** | 业务人员自助分析，释放 IT 重复做报表的人力；Superset 开源免费，与现有架构兼容 | ✅ 是 |
| 5    | **时效性** | 小时级增量已将数据延迟从 24h 压缩到 1h；Spark Structured Streaming（而非 Flink）即可满足，运维成本低；Flink 仅在 Phase 3 毫秒级实时告警时才需要 | ⚠️ Phase 2/3 做（Spark 即可，Flink 留 Phase 3） |
| 6    | **可维护性 / 数据质量** | 统一编码体系是跨系统分析的前提；当前各系统编码字面已一致（如 M001），实际落地无需建维表，但跨系统 JOIN 仍需标准化 | ⚠️ Phase 2 做 |
| 7    | **可维护性** | Delta Lake Time Travel 已支持历史回溯，但当前 DWA 只跑最新 ETL，历史重算需额外调度；价值高但实现复杂度中等 | ❌ 暂缓（Delta Time Travel 已部分满足） |

---

## Plan

### 立即实现

- **Idea 编号**：想法 1 + 想法 4
- **初步方案**：
  - 想法 1（核心）：在现有 `scripts/build_dwa_models.py` 基础上，补全 3 张 DWA 宽表的构建逻辑（日销售 / 传感器告警 / 月度煤质），落 Delta Lake，验证业务查询可用性
  - 想法 4（配套）：构建教学 notebook（`notebook/module5.ipynb`），演示 DuckDB 即席查询 4 个分析场景（销售趋势 / 告警排名 / 煤质报告 / 产销对比），为后续 Superset 看板铺垫
- **产出**：
  - `notebook/module5.ipynb`（教学 notebook）
  - `docs/Module5.md`（实施步骤文档）
  - 3 张 DWA Delta Lake 表（`dwa_sales_daily` / `dwa_tag_alarm` / `dwa_coal_quality`）
- **预计耗时**：1~2 天（代码已有，实现教学 notebook 为主）

### 等待观察

- **Idea 编号**：想法 2（跨系统产销宽表）
- **等待原因**：需要 Idea 6（主数据标准化）先建立矿井/客户编码统一映射表，当前各系统编码虽字面一致但无统一维表，JOIN 仍需业务人员自己处理映射
- **触发条件**：模块七（主数据编码标准化）交付后激活

- **Idea 编号**：想法 3（OLAP 引擎升级）
- **等待原因**：Phase 1 用 DuckDB 已足够验证数据可用性；ClickHouse/Doris 引入额外运维成本，需 Phase 2 再根据 JOIN 密集度选择（Doris 多表 JOIN 场景更优）
- **触发条件**：Phase 2 开始时激活，优先选 Doris（如 JOIN 多）

- **Idea 编号**：想法 5（定时 ETL 调度升级）
- **等待原因**：小时级增量调度用 Spark Structured Streaming 即可满足，无需引入 Flink；Phase 2 可先做小时级调度，Phase 3 再上 Flink 实时告警
- **触发条件**：Phase 2 初期激活（Spark Structured Streaming），Phase 3 再升级 Flink

## 变更产出（可选）

本次 brainstorming 直接对应 Background.md § 6.5 模块五的范围，建议在 proposal.md 中引用本文档作为价值发掘依据。

> **🔍 搜索修正补充**：Background.md § 6.9 "自动血缘采集"的"待验证风险"经核实为**已支持**（DataHub v1.6 支持 OpenLineage 格式），该风险已消除，相关升级路径（手工 YAML → Spark 自动采集）为**可实现**非技术障碍。模块三教学中应更新该风险说明。
