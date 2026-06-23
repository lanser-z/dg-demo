# dwa-sales-daily Spec

> 对应 DWA 汇总宽表能力：日销售汇总宽表

---

## ADDED Requirements

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

### Requirement: 数据过滤规则
The system SHALL filter out records where ERDAT IS NULL OR ERDAT = '00000000' before aggregation.

### Requirement: 输出格式与存储
The aggregated result SHALL be written to Delta Lake at `data/lakehouse/dwa/sap_erp/dwa_sales_daily/` using `write_deltalake` with `mode="overwrite"`.

### Requirement: 聚合范围
The aggregation SHALL include all historical VBAK data available in `data/historical/sap_erp/vbak_year=*.parquet`. The system SHALL register these Parquet files as a DuckDB view named `vbak_parquet` before querying.

### Requirement: LIMIT 行为
The aggregation SHALL apply a LIMIT of 30 to control output size for teaching purposes. This limit SHALL be configurable via a constant `DWA_SALES_LIMIT = 30` in `build_dwa_models.py`.

---

## Scenarios

#### Scenario: 成功聚合日销售数据
- **WHEN** `build_dwa_sales_daily(conn)` is executed
- **THEN** result contains columns: sale_date, order_count, customer_count, total_amount, avg_order_amount, order_type_count, sales_org_count
- **AND** sale_date is in ascending order
- **AND** row count ≤ 30

#### Scenario: 空日期被过滤
- **WHEN** VBAK contains records with ERDAT = '00000000'
- **THEN** those records are excluded from aggregation
- **AND** NULL ERDAT records are also excluded

#### Scenario: 输出写入 Delta Lake
- **WHEN** `write_delta("dwa/sap_erp/dwa_sales_daily", df)` is called
- **THEN** directory `data/lakehouse/dwa/sap_erp/dwa_sales_daily/` is created
- **AND** Parquet files are written with `_delta_log/` directory present
