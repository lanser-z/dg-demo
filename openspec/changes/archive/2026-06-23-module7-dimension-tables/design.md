## Context

当前 Phase 1 各系统字面统一（矿井编码 `M001`、客户编码 `KUNNR`），但字段名不统一（PI 用 `mine`，LIMS 用 `MINE_CODE`，SAP 字段名为 `WERKS` 等）。跨系统产销分析时 JOIN 条件复杂，Module7 维表是模块十二（dwa_sales_production）的必要前置。

**当前可用数据源**：

| 系统 | 路径 | 关键字段 |
|------|------|----------|
| SAP KNA1 | `data/lakehouse/dwd/sap_erp/kna1/` | KUNNR, NAME1, ORT01, STCD1 |
| PI Tags | `data/lakehouse/dwd/pi_system/dwd_tags/` | tag, mine, face |
| LIMS Samples | `data/lakehouse/dwd/lims/dwd_samples/` | MINE_CODE, MINE_NAME |
| SAP VBAK/VBAP | `data/lakehouse/dwd/sap_erp/dwd_vbak/` | VBELN, KUNNR, MATNR |

**利益相关者**：数据分析师（构建产销宽表）、模块十二实施者

## Goals / Non-Goals

**Goals:**
- 建立 3 张轻量维表（矿井/客户/物料），解决跨系统 JOIN 的字段名映射问题
- 维表数据存储为 Delta Lake，路径 `data/lakehouse/dwd/_dimensions/`
- 提供教学 notebook 演示维表价值

**Non-Goals:**
- 不建独立 MDM 系统（DataHub Logical Models 留待维表物理实现后作为扩展）
- 不修改现有 Phase 1 DWD 清洗逻辑
- 不引入新的外部依赖（仅使用 `uv` 管理 Python 包）

## Decisions

### Decision 1：维表数据源使用 DWD 层而非原始 parquet

**选择**：从 `data/lakehouse/dwd/` 各系统读取已清洗数据，而非 `data/historical/` 原始 parquet

**理由**：
- DWD 层已做统一编码（字面值一致），避免原始数据的格式不一致问题
- DWD 层字段名更规范（如 `MINE_CODE` vs 原始可能的 `mine_code`）
- 复用已有清洗逻辑，维表构建脚本更简洁

**备选**：直接从 `data/historical/` 读取原始 parquet
- ❌ 原始数据格式不一致，构建脚本需要处理多种格式，增加复杂度

### Decision 2：去重策略

**矿井维表**：`DISTINCT mine_code`，按 `MINE_CODE` 分组取第一条（name 以 DWD 为准）

**客户维表**：`DISTINCT KUNNR`，按 KUNNR 分组取 NAME1（取最新 ERDAT）

**物料维表**：见 Open Question 3

### Decision 3：Delta Lake 格式 vs Parquet 直接写入

**选择**：Delta Lake（`data/lakehouse/dwd/_dimensions/` 下各维表目录）

**理由**：
- Delta Lake 支持 ACID 事务，维表数据一致性有保障
- 便于后续增量更新（`generate_incremental.py` 模式）
- 与现有 DWD 层架构一致

**备选**：直接写入 Parquet 文件
- ❌ 无事务保障，增量更新逻辑复杂

### Decision 4：构建脚本架构

```
scripts/build_dimension_tables.py
  ├── build_dim_mine()    → read DWD → distinct → write Delta Lake
  ├── build_dim_customer() → read DWD → distinct → write Delta Lake
  └── build_dim_material() → read DWD → distinct → write Delta Lake
```

**理由**：
- 三个函数独立运行，互不依赖，某一维表失败不影响其他
- 每个函数可单独执行，支持按需重建单个维表

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|------|------|----------|
| MARA 缺失 | Demo 环境无 SAP MARA 物料主数据，`dim_material` 无法从 MARA 构建 | 使用 VBAK/VBAP 的 MATNR 字段作为物料编码来源，展示"可用数据优先"原则，诚实声明待 MARA 接入后补充 |
| 维表数据覆盖 | 重复运行脚本会覆盖已有 Delta Lake 数据 | Delta Lake 支持时间旅行（time travel），可从 `./_delta_log/` 恢复历史版本 |
| 维表为空 | 源 DWD 数据缺失导致维表行数为 0 | 构建前用 `df.count()` 验证源数据非空，不符合预期则抛出明确错误 |

## Open Questions

1. **MARA 数据缺失**：`data/historical/sap_erp/` 下无 `mara.parquet`，当前 demo 环境缺少物料主数据。`dim_material` 暂时使用 VBAK/VBAP 的 MATNR 字段作为物料编码来源（唯一可用），待 MARA 接入后重建。

2. **信用等级映射**：`credit_level`（信用等级）在 KNA1 中无直接对应字段。当前方案：设为 `NULL` 或固定值 `'UNKNOWN'`，待与业务方确认映射规则。

3. **维表更新策略**：Module7 维表构建为一次性初始化（Batch），暂不实现增量更新。理由：主数据变更频率低，教学演示无需实时同步。增量更新可在模块十二前作为扩展任务补充。

4. **模块十二依赖对齐**：`dwa_sales_production` 的 JOIN 逻辑需与维表字段名对齐（`dim_mine.mine_code` vs 各系统 `mine`/`MINE_CODE`），建议在模块十二规范中明确引用本模块维表。
