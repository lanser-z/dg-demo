# cross-system-dwa Specification

## Purpose

跨系统 4 表 JOIN 宽表 `dwa_sales_production`，用 DuckDB 替代 ClickHouse/Doris（10 分钟 demo 约束），演示 6.11 主题域重组的跨主题 JOIN 价值。

## ADDED Requirements

### Requirement: scripts/build_dwa_sales_production.py 实现 4 表 JOIN

`scripts/build_dwa_sales_production.py` MUST 用 DuckDB 4 表 LEFT JOIN 跨主题（vbak + kna1 + tags + samples），按 `mine_code` 跨主题关联键，写入 `data/lakehouse/dwa/dwa_sales_production/` Delta Lake 表。业务代码改动 ≤ 5 行/入口。

#### Scenario: 4 表 JOIN SQL 模板
- **WHEN** 检查 `scripts/build_dwa_sales_production.py` 源码
- **THEN** MUST 含 `CREATE TABLE dwa_sales_production AS SELECT ... FROM vbak v LEFT JOIN kna1 k ON v.KUNNR=k.KUNNR LEFT JOIN tags t ON v.MINE_CODE=t.mine LEFT JOIN samples s ON t.mine=s.MINE_CODE GROUP BY ...` 模式

#### Scenario: 读 subject-分区
- **WHEN** 检查 SQL 中的 read_parquet 路径
- **THEN** MUST 含 4 个 read_parquet：`dwd/sales/dwd_vbak/`、`dwd/sales/dwd_kna1/`、`dwd/production/dwd_tags/`、`dwd/coal_quality/dwd_samples/`，**MUST NOT** 含 `dwd/{sap_erp,pi_system,lims,oa}/` 旧 system-分区

#### Scenario: 写入 Delta Lake 持久化
- **WHEN** 跑完脚本
- **THEN** `data/lakehouse/dwa/dwa_sales_production/_delta_log/` 与 parquet files MUST 存在，且 DuckDB 重新查询同一宽表 **< 1 秒**（验证物化）

### Requirement: 旧 3 张 DWA 切换上游到 subject-分区

`scripts/build_dwa_models.py` 中 `build_dwa_sales_daily()` / `build_dwa_tag_alarm()` / `build_dwa_coal_quality()` 三个函数 MUST 把 SQL 引用从 `dwd/{sap_erp,pi_system,lims}/*` 切换到 `dwd/{sales,production,coal_quality}/*`（兑现 6.11 delta 承诺）。

#### Scenario: 3 个 DWA 函数 SQL 引用切换
- **WHEN** 检查 `scripts/build_dwa_models.py` 中 3 个 DWA 函数的 read_parquet 调用
- **THEN** MUST 含 `dwd/sales/dwd_vbak`、`dwd/production/dwd_tags`、`dwd/coal_quality/dwd_samples` 路径，**MUST NOT** 含 `dwd/sap_erp/dwd_vbak`、`dwd/pi_system/dwd_tags`、`dwd/lims/dwd_samples` 旧路径

#### Scenario: 跑 build_dwa_models.py 仍出 3 张宽表
- **WHEN** 跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** MUST 仍生成 dwa_sales_daily / dwa_tag_alarm / dwa_coal_quality 3 张宽表（行数与 6.11 时一致，因为 subject-分区与 system-分区数据相同）

### Requirement: 4 个分析场景 SQL 模板

`scripts/build_dwa_sales_production.py` MUST 提供 4 个分析场景的 SQL 模板（注释 / docstring 形式），覆盖产销对比 / 煤质定价 / 安全趋势 / 订单履约 4 维度。

#### Scenario: 4 SQL 模板存在
- **WHEN** 检查 `scripts/build_dwa_sales_production.py` 源码
- **THEN** MUST 含 4 个 SQL 常量：`SQL_PRODUCTION_SALES`、`SQL_COAL_PRICING`、`SQL_SAFETY_TREND`、`SQL_ORDER_FULFILLMENT`

#### Scenario: SQL 模板语义正确
- **WHEN** 跑 `duckdb -c "$(cat scripts/build_dwa_sales_production.py | grep -A5 SQL_PRODUCTION_SALES | head -6)"`
- **THEN** MUST 输出非空结果（每矿井的日产销量 + 煤质平均 + 客户数）

### Requirement: notebook module12.ipynb 3 cells 演示

`notebook/module12.ipynb` MUST 含 3 cells：1) 跑 `build_dwa_sales_production.py` 生成宽表；2) 4 个分析场景 SQL 示例输出；3) matplotlib 渲染产销对比图（按矿井折线 + 煤质叠加）。

#### Scenario: cell 1 跑完出宽表
- **WHEN** 执行 cell 1
- **THEN** 输出 `✅ dwa_sales_production written: {n} rows, {m} columns`

#### Scenario: cell 2 输出 4 个场景
- **WHEN** 执行 cell 2（4 个 SQL 模板依次跑）
- **THEN** MUST 输出 4 个非空 DataFrame（产销对比、煤质定价、安全趋势、订单履约）

#### Scenario: cell 3 渲染图
- **WHEN** 执行 cell 3
- **THEN** 生成 `notebook/step_images/module12_4table_join.png`（含产销折线 + 煤质叠加）

### Requirement: 4 表 JOIN lineage 边（6.9 路径）

`scripts/build_dwa_sales_production.py` MUST 通过 6.9 `LineageEmitter` 上下文管理器 emit lineage 事件，含 inputs（4 张 DWD）+ outputs（dwa_sales_production）。

#### Scenario: LineageEmitter 包装
- **WHEN** 检查 `scripts/build_dwa_sales_production.py` 源码
- **THEN** MUST 含 `with LineageEmitter("dwa_sales_production", sql=SQL_4TABLE_JOIN) as e:` 上下文，且 `e.emit_output("urn:li:dataset:(urn:li:dataPlatform:dwa,dwa_sales_production,PROD)", df)` 调用

#### Scenario: lineage 写入 GMS
- **WHEN** 跑脚本 + `python scripts/verify_auto_lineage.py`
- **THEN** MUST 输出 dwa_sales_production job 的 inputs 含 4 张 DWD 表，outputs 含 1 张 dwa_sales_production
