# scheduled-quality-monitoring Specification

## Purpose

把 `scripts/run_great_expectations.py` 的一次性 GE 风格规则检测升级为定时调度 + 阈值告警的能力。覆盖 `QualityCheckpoint` 抽象、APScheduler 守护模式、`--run-once` CLI、阈值告警（console + JSON 文件）四件套。

## ADDED Requirements

### Requirement: QualityCheckpoint 抽象输出结构化 CheckpointResult

`src/dg_platform/quality_checkpoint.py` MUST 提供 `QualityCheckpoint` 类，接收 `RULES` 字典与 data path，输出 `CheckpointResult(score: float, grade: str, passed: int, failed: int, duration_s: float, system: str, table: str, report_path: str)`。MUST 复用 `scripts/run_great_expectations.py` 的 `RULES` 与 `expect_*` 函数，**不重写规则引擎**。

#### Scenario: CheckpointResult 字段齐全
- **WHEN** 调用 `QualityCheckpoint(system="sap_erp", table="vbak").run()`
- **THEN** 返回的 CheckpointResult MUST 含 7 字段：score (float 0-100), grade (A/B/C/D), passed (int), failed (int), duration_s (float), system (str), table (str), report_path (str)

#### Scenario: 复用现有 RULES
- **WHEN** 检查 `src/dg_platform/quality_checkpoint.py` 源码
- **THEN** MUST 含 `from scripts.run_great_expectations import RULES` 或 `from dg_education.quality import ...` 等价的 import，**MUST NOT** 重新定义 expect_* 函数

#### Scenario: 单个 rule 失败不阻断
- **WHEN** Checkpoint 内某条 rule 抛异常
- **THEN** MUST 标记该 rule failed 并继续执行后续 rules，最终 score MUST 反映成功/失败比例

### Requirement: APScheduler 守护模式每日 08:30 触发

`scripts/quality_scheduler.py` MUST 提供 APScheduler `BlockingScheduler`，注册 cron 任务每日 08:30 触发（`CronTrigger(hour=8, minute=30)`），执行 `run_all_systems()` 函数。

#### Scenario: 守护模式启动注册 cron 任务
- **WHEN** 执行 `uv run python scripts/quality_scheduler.py`（无 `--run-once`）
- **THEN** MUST 注册一个名为 `quality_daily` 的 cron job，调度为每日 08:30，函数引用为 `run_all_systems`

#### Scenario: 守护模式 Ctrl+C 优雅退出
- **WHEN** 守护进程收到 SIGINT（Ctrl+C）
- **THEN** MUST 调用 `scheduler.shutdown(wait=False)` 退出，无 traceback

### Requirement: --run-once CLI 模式

`scripts/quality_scheduler.py` MUST 支持 `--run-once` 参数，单次执行后立即退出，不启动守护循环。

#### Scenario: --run-once 退出码 0
- **WHEN** 执行 `uv run python scripts/quality_scheduler.py --run-once` 全部系统无异常
- **THEN** exit code 0，stdout 输出 `✅ quality check done: {n} systems checked in {s}s`

#### Scenario: --run-once 退出码非 0
- **WHEN** 5 系统中 ≥ 1 个抛未捕获异常
- **THEN** exit code 1，stderr 输出失败的 system 名称

### Requirement: 阈值 < 70 触发告警

Checkpoint 结果 score < 70 时 MUST 触发告警：1) `logging.warning` 输出到 stderr；2) 追加 JSON 对象到 `data/quality_alerts.json`（数组追加）。

#### Scenario: 阈值 70 触发
- **WHEN** `system="sap_erp"` 的 `score = 65.0`
- **THEN** MUST 写一条 alert 到 `data/quality_alerts.json`，结构 `{"timestamp": "2026-07-15T08:30:00", "system": "sap_erp", "score": 65.0, "grade": "D"}`，并 stderr 输出 `WARNING  quality_alert system=sap_erp score=65.0`

#### Scenario: 阈值 70 不触发
- **WHEN** `system="lims"` 的 `score = 92.5`
- **THEN** MUST NOT 写 alert 到 `data/quality_alerts.json`，不输出 warning

#### Scenario: alerts.json 文件不存在时创建
- **WHEN** `data/quality_alerts.json` 不存在
- **THEN** MUST 自动创建并写入第一条 alert（不需要预先 `touch`）

### Requirement: 教学 notebook 演示完整闭环

`notebook/module10.ipynb` MUST 含 4 个 cell 演示：1) import + `--run-once` 触发；2) 查 SQLite 历史 Top-5 最低分；3) matplotlib 趋势图渲染并展示；4) 模拟 1 个 score < 70 触发告警（写 alerts.json）。

#### Scenario: notebook 4 cells 顺序正确
- **WHEN** 执行 `notebook/module10.ipynb` 顺序 4 cells
- **THEN** cell 1 输出 `✅ quality check done`，cell 2 输出 sqlite 查询结果 DataFrame，cell 3 输出 PNG 路径 `data/quality_trend.png`，cell 4 输出 alerts.json 路径与新 alert 内容

#### Scenario: 模拟告警不污染真实数据
- **WHEN** cell 4 模拟 score=60 告警
- **THEN** alerts.json MUST 含 1 条新 alert，quality_scores.db MUST NOT 含 score=60 的真实行（模拟数据不入库）
