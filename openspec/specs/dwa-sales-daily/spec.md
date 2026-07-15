# dwa-sales-daily Spec

> 对应 DWA 汇总宽表能力：日销售汇总宽表

## Purpose

日销售汇总宽表 `dwa_sales_daily` 由 SAP VBAK 数据按销售日期聚合生成，输出 7 个标准字段，存储到 Delta Lake。
## Requirements
### Requirement: 日销售汇总宽表字段规范
dwa-sales-daily SHALL aggregate SAP VBAK data by ERDAT (sales date) and output the following fields:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| sale_date | DATE | 销售日期（来自 ERDAT） |
| order_count | BIGINT | 当日订单数量 |
| customer_count | BIGINT | 当日参与客户数（去重 KUNNR） |
| total_amount | DOUBLE | 当日订单总金额（NETWR 求和） |
| avg_order_amount | DOUBLE | 当日订单平均金额 |
| order_type_count | BIGINT | 当日订单类型种类数（AUART 去重） |
| sales_org_count | BIGINT | 当日销售组织数（VKORG 去重） |

#### Scenario: 成功聚合日销售数据
- **WHEN** `build_dwa_sales_daily(conn)` is executed
- **THEN** result contains columns: sale_date, order_count, customer_count, total_amount, avg_order_amount, order_type_count, sales_org_count
- **AND** sale_date is in ascending order
- **AND** row count ≤ 30

### Requirement: 数据过滤规则
The system SHALL filter out records where ERDAT IS NULL OR ERDAT = '00000000' before aggregation.

#### Scenario: 空日期被过滤
- **WHEN** VBAK contains records with ERDAT = '00000000'
- **THEN** those records are excluded from aggregation
- **AND** NULL ERDAT records are also excluded

### Requirement: 输出格式与存储
The aggregated result SHALL be written to Delta Lake at `data/lakehouse/dwa/sap_erp/dwa_sales_daily/` using `write_deltalake` with `mode="overwrite"`.

#### Scenario: 输出写入 Delta Lake
- **WHEN** `write_delta("dwa/sap_erp/dwa_sales_daily", df)` is called
- **THEN** directory `data/lakehouse/dwa/sap_erp/dwa_sales_daily/` is created
- **AND** Parquet files are written with `_delta_log/` directory present

### Requirement: 聚合范围
The aggregation SHALL include all historical VBAK data available in `data/historical/sap_erp/vbak_year=*.parquet`. The system SHALL register these Parquet files as a DuckDB view named `vbak_parquet` before querying.

#### Scenario: 多年度数据聚合
- **WHEN** vbak_year=2022.parquet and vbak_year=2023.parquet are both available
- **THEN** aggregation covers sales dates from both years

### Requirement: LIMIT 行为
The aggregation SHALL apply a LIMIT of 30 to control output size for teaching purposes. This limit SHALL be configurable via a constant `DWA_SALES_LIMIT = 30` in `build_dwa_models.py`.

#### Scenario: LIMIT 30 应用
- **WHEN** aggregation produces more than 30 unique sale_date values
- **THEN** final result is limited to 30 rows

### Requirement: 6.11 升级后 DWA 暂不切换 subject-分区上游（演示阶段）

`dwa_sales_daily` 宽表在 6.11 主题域重组后 MUST 继续读 `dwd/sap_erp/dwd_vbak/`（旧 system-分区），不切换到 `dwd/sales/dwd_vbak/`。6.12 跨主题 JOIN 时再统一切换。

#### Scenario: 演示阶段上游路径不变
- **WHEN** 6.11 变更归档后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_sales_daily` 宽表的 SQL 仍引用 `dwd/sap_erp/dwd_vbak/`

#### Scenario: 文档说明延迟切换
- **WHEN** 阅读 `docs/Module11.md` 第 4 节
- **THEN** MUST 含说明"DWA 切换是 6.12 范围"

