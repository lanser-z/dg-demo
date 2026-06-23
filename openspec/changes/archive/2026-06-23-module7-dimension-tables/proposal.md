## Why

当前 Phase 1 各系统的矿井/客户/物料编码字面统一（如 `M001`），但字段名不统一（`mine`/`mine_code`/`WERKS`），导致跨系统产销分析需要大量 WHERE 子句映射，SQL 可维护性差、JOIN 条件不直观。Module7 维表是模块十二跨系统产销宽表（dwa_sales_production）的必要前置依赖。

## What Changes

1. **新增** `scripts/build_dimension_tables.py`：从 `data/historical/` 各系统 parquet 聚合、去重，写入 3 张维表（Delta Lake 格式）到 `data/lakehouse/dwd/_dimensions/`
2. **新增** 3 张维表 Delta Lake 目录：
   - `dim_mine/` — 矿井维表，字段：mine_code, mine_name, mine_type, sap_mine_field, pi_mine_field, lims_mine_field
   - `dim_customer/` — 客户维表，字段：kunnr, customer_name, region, credit_level
   - `dim_material/` — 物料维表，字段：matnr, mat_desc, mat_type
3. **新增** `notebook/module7.ipynb`：教学 notebook，对比有维表 vs 无维表的 JOIN 差异
4. **不影响** 现有 Phase 1 的 DWA 宽表（dwa_sales_daily / dwa_coal_quality / dwa_tag_alarm）

## Capabilities

### New Capabilities

- `dim-mine`: 矿井维表。从 SAP/PI/LIMS 的原始 parquet 提取矿井编码和名称，去重后写入 `data/lakehouse/dwd/_dimensions/dim_mine/`。源：KNA1（SAP）、dwd_pi_tags（PI）、dwd_lims_samples（LIMS）。
- `dim-customer`: 客户维表。从 KNA1 parquet 提取客户编码、名称、区域、信用等级，去重后写入 `data/lakehouse/dwd/_dimensions/dim_customer/`。
- `dim-material`: 物料维表。从 MARA parquet 提取物料编码、描述、类型，去重后写入 `data/lakehouse/dwd/_dimensions/dim_material/`。
- `module7-notebook`: 教学 notebook。痛点故事 + 3 维表构建演示 + 有/无维表 JOIN 对比 SQL + 诚实声明。位于 `notebook/module7.ipynb`。

### Modified Capabilities

（无——Module7 维表为新增独立能力，不修改现有规范行为）

## Impact

- **新增文件**：`scripts/build_dimension_tables.py`、`notebook/module7.ipynb`
- **新增目录**：`data/lakehouse/dwd/_dimensions/dim_mine/`、`dim_customer/`、`dim_material/`（Delta Lake）
- **依赖**：`data/historical/sap_kna1.parquet`、`data/historical/pi_tags.parquet`、`data/historical/lims_samples.parquet`、`data/historical/sap_mara.parquet`
- **被依赖**：模块十二产销宽表（`dwa_sales_production`）的 PI + LIMS + SAP + KNA1 四表 JOIN 依赖本模块维表
- **回滚**：删除 `data/lakehouse/dwd/_dimensions/` 下 3 个维表目录，并删除 `scripts/build_dimension_tables.py` 及 `notebook/module7.ipynb` 即可完成回滚，无数据破坏风险
