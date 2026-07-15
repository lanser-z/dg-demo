# dwa-tag-alarm Spec

> 对应 DWA 汇总宽表能力：传感器告警汇总宽表

## Purpose

传感器告警汇总宽表 `dwa_tag_alarm` 由 PI System 时序标签数据按矿井 / 工作面 / tag 聚合生成，输出 10 个标准字段（含告警统计），存储到 Delta Lake。
## Requirements
### Requirement: 传感器告警汇总宽表字段规范
dwa-tag-alarm SHALL aggregate PI tags data and output the following fields:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| mine | VARCHAR | 矿井编码（来自 tag 路径中的 mine 字段） |
| face | VARCHAR | 工作面编码 |
| tag | VARCHAR | 传感器类型（WAGAS/TEMP/CO） |
| total_records | BIGINT | 该 tag 的总记录数 |
| missing_count | BIGINT | 异常记录数（status = -1 的数量） |
| high_value_count | BIGINT | 高值告警数（value > 8000 的数量） |
| avg_value | DOUBLE | 平均值 |
| stddev_value | DOUBLE | 标准差 |
| min_value | DOUBLE | 最小值 |
| max_value | DOUBLE | 最大值 |

#### Scenario: 成功聚合传感器告警数据
- **WHEN** `build_dwa_tag_alarm(conn)` is executed
- **THEN** result contains all 10 columns: mine, face, tag, total_records, missing_count, high_value_count, avg_value, stddev_value, min_value, max_value
- **AND** rows are sorted by high_value_count descending
- **AND** row count ≤ 20

### Requirement: 告警判定规则
The system SHALL define high_value alarm as `value > 8000` and missing status as `status = -1`.

#### Scenario: 高值告警阈值正确
- **WHEN** PI tags data contains value = 9000
- **THEN** that record is counted in high_value_count for its tag
- **AND** value = 5000 is NOT counted in high_value_count

#### Scenario: 缺失状态判定
- **WHEN** PI tags data contains status = -1
- **THEN** that record is counted in missing_count for its tag

### Requirement: 排序与 Top N
The aggregated result SHALL be sorted by `high_value_count DESC` and limited to top 20 tags (`LIMIT 20`).

#### Scenario: Top 20 限制
- **WHEN** aggregation produces more than 20 unique mine/face/tag combinations
- **THEN** final result is limited to 20 rows sorted by high_value_count descending

### Requirement: 数据源
The aggregation SHALL read from `data/historical/pi_system/tags_year=2022_month=01.parquet` and register as DuckDB view `pi_tags` in `build_dwa_models.py`. The system SHALL apply a row limit of 500,000 to control compute cost.

#### Scenario: 读取 PI 历史数据
- **WHEN** DuckDB view `pi_tags` is registered from `data/historical/pi_system/tags_year=2022_month=01.parquet`
- **THEN** source contains up to 500,000 rows of PI tag readings

### Requirement: 输出格式与存储
The result SHALL be written to `data/lakehouse/dwa/pi_system/dwa_tag_alarm/` using Delta Lake overwrite mode.

#### Scenario: 输出写入 Delta Lake
- **WHEN** `write_delta("dwa/pi_system/dwa_tag_alarm", df)` is called
- **THEN** directory `data/lakehouse/dwa/pi_system/dwa_tag_alarm/` is created with Delta Lake format

### Requirement: 6.11 升级后 DWA 暂不切换 subject-分区上游（演示阶段）

`dwa_tag_alarm` 宽表在 6.11 主题域重组后 MUST 继续读 `dwd/pi_system/dwd_tags/`（旧 system-分区），不切换到 `dwd/production/dwd_tags/`。6.12 跨主题 JOIN 时再统一切换。

#### Scenario: 演示阶段上游路径不变
- **WHEN** 6.11 变更归档后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_tag_alarm` 宽表的 SQL 仍引用 `dwd/pi_system/dwd_tags/`

#### Scenario: 文档说明延迟切换
- **WHEN** 阅读 `docs/Module11.md` 第 4 节
- **THEN** MUST 含说明"DWA 切换是 6.12 范围"

