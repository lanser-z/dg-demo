# module6-sql-templates Spec

> 对应 SQL 模板能力：4 个分析场景的可执行 SQL 示例

---

## Purpose

TBD

---

## MODIFIED Requirements

### Requirement: SQL 模板文件位置
module6-sql-templates SHALL be provided in `docs/Module6.md`，not in source code.

#### Scenario: 文档位置正确
- **WHEN** business user looks for SQL templates
- **THEN** templates are found in `docs/Module6.md` section 6

### Requirement: 场景 1 SQL 模板（销售趋势）
The SQL template for sales trend SHALL query `dwa_sales_daily` and include:

```sql
SELECT
    sale_date,
    order_count,
    customer_count,
    total_amount,
    avg_order_amount
FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily/'
ORDER BY sale_date DESC
LIMIT 30;
```

#### Scenario: 场景 1 SQL 可执行
- **WHEN** business user copies scenario 1 SQL and runs in DuckDB
- **THEN** result contains sale_date, order_count, customer_count, total_amount columns
- **AND** results are sorted by sale_date descending

### Requirement: 场景 2 SQL 模板（告警排名）
The SQL template for alarm ranking SHALL query `dwa_tag_alarm` and include:

```sql
SELECT
    mine,
    face,
    tag,
    high_value_count,
    avg_value,
    stddev_value
FROM 'data/lakehouse/dwa/pi_system/dwa_tag_alarm/'
ORDER BY high_value_count DESC
LIMIT 20;
```

#### Scenario: 场景 2 SQL 可执行
- **WHEN** business user copies scenario 2 SQL and runs in DuckDB
- **THEN** result contains mine, face, tag, high_value_count columns
- **AND** results are sorted by high_value_count descending

### Requirement: 场景 3 SQL 模板（月度煤质）
The SQL template for coal quality SHALL query `dwa_coal_quality` and include:

```sql
SELECT
    MINE_CODE,
    month,
    SAMPLE_TYPE,
    sample_count,
    avg_ash_content,
    avg_gross_calorific
FROM 'data/lakehouse/dwa/lims/dwa_coal_quality/'
ORDER BY month DESC, MINE_CODE
LIMIT 50;
```

#### Scenario: 场景 3 SQL 可执行
- **WHEN** business user copies scenario 3 SQL and runs in DuckDB
- **THEN** result contains MINE_CODE, month, SAMPLE_TYPE, avg_ash_content columns

### Requirement: 场景 4 SQL 模板（产销对比）
The SQL template for production-sales comparison SHALL be marked with ⚠️ warning and explicitly state:
- 当前为单系统宽表，跨系统产销对比需 Phase 2
- 示例 SQL SHALL include LEFT JOIN skeleton with comment placeholders

#### Scenario: 场景 4 诚实声明
- **WHEN** business user reads scenario 4 SQL template
- **THEN** ⚠️ warning is visible
- **AND** comment explains cross-system JOIN requires Phase 2

### Requirement: SQL 模板可执行性
All SQL templates SHALL be directly executable in DuckDB CLI or Python API without modification.

#### Scenario: SQL 模板可执行性
- **WHEN** business user copies any SQL template and runs in DuckDB
- **THEN** the query executes without syntax error
- **AND** results are returned
