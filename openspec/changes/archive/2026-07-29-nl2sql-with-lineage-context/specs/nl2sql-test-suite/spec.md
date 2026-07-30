## ADDED Requirements

### Requirement: 测试问题集覆盖多场景

`scripts/nl2sql_demo.py` SHALL 包含 6-8 个测试问题，覆盖以下场景：单表聚合查询、多表 JOIN、跨系统歧义（数据孤岛）、业务术语消解、时间范围筛选、排序 Top-N。

#### Scenario: 单表聚合查询

- **WHEN** 测试问题"最近30天的销售额趋势"
- **THEN** NL2SQL 生成查 `dwa_sales_daily` 的 SQL，按 `sale_date` 排序

#### Scenario: 业务术语消解

- **WHEN** 测试问题"各矿井精煤的灰分排名"
- **THEN** NL2SQL 通过 glossary 将"精煤"映射为 `SAMPLE_TYPE='精煤'`，查 `dwa_coal_quality` 并按 `avg_ash_content` 排序

#### Scenario: 跨系统歧义识别

- **WHEN** 测试问题"销售订单对应的煤质化验数据"
- **THEN** NL2SQL 识别 `sap_erp.vbak` 与 `lims.samples` 无字面共享列，返回提示"两表为声明式业务关系，无可执行 JOIN，需主数据标准化后才能跨系统查询"

#### Scenario: 传感器告警 Top-N

- **WHEN** 测试问题"告警次数最多的10个传感器"
- **THEN** NL2SQL 生成查 `dwa_tag_alarm` 的 SQL，按 `high_value_count` 降序 LIMIT 10

### Requirement: 端到端验证脚本输出报告

`scripts/nl2sql_demo.py` SHALL 批量执行测试问题，对每个问题输出：问题原文、生成的 SQL、查询结果（前 5 行）、血缘解释、是否成功（PASS/FAIL）。

#### Scenario: 批量执行

- **WHEN** 执行 `uv run python scripts/nl2sql_demo.py`
- **THEN** 输出每个问题的 SQL/结果/血缘解释/状态，最后输出汇总（N passed, M failed）

#### Scenario: 失败不中断

- **WHEN** 某个测试问题执行失败
- **THEN** 脚本 MUST 记录失败原因并继续执行下一个问题，MUST NOT 因单题失败中断
