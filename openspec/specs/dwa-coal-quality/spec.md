# dwa-coal-quality Spec

> 对应 DWA 汇总宽表能力：月度煤质汇总宽表

---

## Purpose

TBD

---

## ADDED Requirements

### Requirement: 月度煤质汇总宽表字段规范
dwa-coal-quality SHALL aggregate LIMS samples data by mine and month and output the following fields:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| MINE_CODE | VARCHAR | 矿井编码 |
| MINE_NAME | VARCHAR | 矿井名称 |
| month | VARCHAR | 汇总月份（格式：YYYY-MM） |
| SAMPLE_TYPE | VARCHAR | 煤种类型 |
| sample_count | BIGINT | 样品数量 |
| avg_ash_content | DOUBLE | 平均灰分（AD） |
| avg_volatile_content | DOUBLE | 平均挥发分（VD） |
| avg_sulfur_content | DOUBLE | 平均全硫（St） |
| avg_gross_calorific | DOUBLE | 平均发热量（QGR_AD） |
| min_ash_content | DOUBLE | 灰分最小值 |
| max_ash_content | DOUBLE | 灰分最大值 |
| lab_count | BIGINT | 涉及实验室数量（去重 TEST_LAB） |

### Requirement: 月份字段生成
The system SHALL derive the month field from SAMPLING_DATE using `SUBSTR(SAMPLING_DATE, 1, 7)` to produce YYYY-MM format.

### Requirement: 过滤规则
The aggregation SHALL filter out records where SAMPLING_DATE IS NULL OR MINE_CODE IS NULL.

### Requirement: 输出限制
The result SHALL be limited to 50 rows (`LIMIT 50`), sorted by month then MINE_CODE ascending.

### Requirement: 数据源
The aggregation SHALL read from `data/historical/lims/samples_year=2022.parquet`, registered as DuckDB view `lims_samples`, with a row limit of 200,000.

### Requirement: 输出格式与存储
The result SHALL be written to `data/lakehouse/dwa/lims/dwa_coal_quality/` using Delta Lake overwrite mode.

---

## Scenarios

#### Scenario: 成功聚合月度煤质数据
- **WHEN** `build_dwa_coal_quality(conn)` is executed
- **THEN** result contains all 12 columns listed in the field specification
- **AND** month field is in YYYY-MM format
- **AND** rows are sorted by month, MINE_CODE ascending
- **AND** row count ≤ 50

#### Scenario: NULL 值被过滤
- **WHEN** LIMS samples contain records with NULL SAMPLING_DATE or NULL MINE_CODE
- **THEN** those records are excluded from aggregation

#### Scenario: 煤质指标计算正确
- **WHEN** LIMS samples contain AD values: 10.5, 11.2, 10.8 for the same mine/month/type
- **THEN** avg_ash_content SHALL be (10.5 + 11.2 + 10.8) / 3 ≈ 10.83

#### Scenario: 输出写入 Delta Lake
- **WHEN** `write_delta("dwa/lims/dwa_coal_quality", df)` is called
- **THEN** directory `data/lakehouse/dwa/lims/dwa_coal_quality/` is created with Delta Lake format
