# quality-score-history Specification

## Purpose
TBD - created by archiving change module10-scheduled-quality-monitoring. Update Purpose after archive.
## Requirements
### Requirement: SQLite 表结构与写入契约

`data/quality_scores.db` MUST 含 `quality_scores` 表，列：`run_date TEXT`、`system TEXT`、`table TEXT`、`score REAL`、`grade TEXT`、`passed INTEGER`、`failed INTEGER`、`duration_s REAL`，主键 `(run_date, system, table)`。每次 Checkpoint.run() 跑完 MUST 用 `INSERT OR REPLACE` 写入。

#### Scenario: 首次创建表
- **WHEN** `data/quality_scores.db` 不存在
- **THEN** MUST 自动创建 `quality_scores` 表（带 8 列 + 主键），不抛异常

#### Scenario: INSERT OR REPLACE
- **WHEN** 同一 `(run_date, system, table)` 已存在行
- **THEN** MUST 覆盖旧行（不是新增第二条）

#### Scenario: grade 取值约束
- **WHEN** 写入新行
- **THEN** `grade` 字段 MUST ∈ `{"A", "B", "C", "D"}`（按 score 阈值：≥90 A, ≥80 B, ≥70 C, <70 D）

### Requirement: 趋势图渲染 5 系统折线

`scripts/quality_scheduler.py` MUST 提供 `plot_trend_lines()` 函数，从 SQLite 读最近 30 天所有 `(run_date, system, score)`，matplotlib 渲染 5 条系统折线，X 轴日期，Y 轴 0-100，保存 `data/quality_trend.png`。

#### Scenario: 空历史不崩溃
- **WHEN** `quality_scores` 表无数据
- **THEN** MUST 跳过 plot，输出 `INFO quality_trend: no history yet, skipping` 退出，无异常

#### Scenario: 单日 5 系统折线
- **WHEN** DB 含 1 天的 5 系统记录
- **THEN** MUST 渲染 1 个 X 轴点、5 条不同颜色折线，PNG ≥ 10 KB

#### Scenario: Y 轴固定 0-100
- **WHEN** plot 渲染
- **THEN** `ax.set_ylim(0, 100)` MUST 调用（保证 grade D 阈值可见）

### Requirement: Notebook 趋势图 cell 演示

`notebook/module10.ipynb` 第 3 cell MUST 调用 `plot_trend_lines()` 后用 IPython `display(Image(...))` 或 `matplotlib inline` 展示。

#### Scenario: PNG 路径输出
- **WHEN** cell 3 执行
- **THEN** MUST 输出 `data/quality_trend.png` 绝对路径，文件大小 ≥ 10 KB

