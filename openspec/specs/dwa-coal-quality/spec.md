# dwa-coal-quality Spec

> 对应 DWA 汇总宽表能力：月度煤质汇总宽表

## Purpose

月度煤质汇总宽表 `dwa_coal_quality` 由 LIMS 样品数据按矿井 / 月份聚合生成，输出 12 个标准字段，存储到 Delta Lake。
## Requirements
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

#### Scenario: 成功聚合月度煤质数据
- **WHEN** `build_dwa_coal_quality(conn)` is executed
- **THEN** result contains all 12 columns listed in the field specification
- **AND** month field is in YYYY-MM format
- **AND** rows are sorted by month, MINE_CODE ascending
- **AND** row count ≤ 50

### Requirement: 月份字段生成
The system SHALL derive the month field from SAMPLING_DATE using `SUBSTR(SAMPLING_DATE, 1, 7)` to produce YYYY-MM format.

#### Scenario: 月份格式正确
- **WHEN** SAMPLING_DATE = "2022-05-15"
- **THEN** derived month = "2022-05"

### Requirement: 过滤规则
The aggregation SHALL filter out records where SAMPLING_DATE IS NULL OR MINE_CODE IS NULL.

#### Scenario: NULL 值被过滤
- **WHEN** LIMS samples contain records with NULL SAMPLING_DATE or NULL MINE_CODE
- **THEN** those records are excluded from aggregation

### Requirement: 输出限制
The result SHALL be limited to 50 rows (`LIMIT 50`), sorted by month then MINE_CODE ascending.

#### Scenario: 输出行数限制
- **WHEN** source contains more than 50 unique mine/month/type combinations
- **THEN** result contains exactly 50 rows

### Requirement: 数据源
The aggregation SHALL read from `data/historical/lims/samples_year=2022.parquet`, registered as DuckDB view `lims_samples`, with a row limit of 200,000.

#### Scenario: 读取 LIMS 历史数据
- **WHEN** DuckDB view `lims_samples` is registered from `data/historical/lims/samples_year=2022.parquet`
- **THEN** source contains up to 200,000 rows of LIMS samples

### Requirement: 输出格式与存储
The result SHALL be written to `data/lakehouse/dwa/lims/dwa_coal_quality/` using Delta Lake overwrite mode.

#### Scenario: 输出写入 Delta Lake
- **WHEN** `write_delta("dwa/lims/dwa_coal_quality", df)` is called
- **THEN** directory `data/lakehouse/dwa/lims/dwa_coal_quality/` is created with Delta Lake format

### Requirement: 6.11 升级后 DWA 暂不切换 subject-分区上游（演示阶段）

`dwa_coal_quality` 宽表在 6.11 主题域重组后 MUST 继续读 `dwd/lims/dwd_samples/`（旧 system-分区）作为上游，不切换到 `dwd/coal_quality/dwd_samples/`（新 subject-分区）。6.12 跨主题 JOIN 时再统一切换。

#### Scenario: 演示阶段上游路径不变
- **WHEN** 6.11 变更归档后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_coal_quality` 宽表的 SQL 仍引用 `dwd/lims/dwd_samples/`，**不**引用 `dwd/coal_quality/dwd_samples/`

#### Scenario: 文档说明延迟切换
- **WHEN** 阅读 `docs/Module11.md` 第 4 节
- **THEN** MUST 含一段说明"DWA 宽表上游切换到 subject-分区是 6.12 范围；6.11 仅重组 DWD 与 lineage，DWA 仍读旧路径"

### Requirement: 6.12 切换上游到 subject-分区

`dwa_coal_quality` 宽表上游 MUST 从 `dwd/lims/dwd_samples/` 切换到 `dwd/coal_quality/dwd_samples/`（6.11 主题域重组后兑现）。

#### Scenario: 切换后 SQL 引用
- **WHEN** 检查 `scripts/build_dwa_models.py` 中 `build_dwa_coal_quality()` 的 read_parquet 调用
- **THEN** MUST 含 `dwd/coal_quality/dwd_samples/`，**MUST NOT** 含 `dwd/lims/dwd_samples/`

#### Scenario: 切换后宽表行数一致
- **WHEN** 6.12 切换后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_coal_quality` 宽表行数与 6.11 时一致（subject-分区与 system-分区数据相同）

#### Scenario: 文档说明切换完成
- **WHEN** 阅读 `docs/Module12.md` 第 3 节
- **THEN** MUST 含"dwa_coal_quality / dwa_sales_daily / dwa_tag_alarm 在 6.12 切到 subject-分区上游"说明

