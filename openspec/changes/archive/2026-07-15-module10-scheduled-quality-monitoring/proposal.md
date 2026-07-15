## Why

模块 2 演示版质量检测每次只能手动跑 `scripts/run_great_expectations.py`，报告丢在终端或单次 JSON 文件里，无趋势、无告警。6.10 目标是把 GE 风格规则升级为**定时调度 + 持久化历史 + 阈值告警**三件套，业务可观测从"看到分数低"进化为"系统主动通知"。

## What Changes

- **新增 `QualityCheckpoint` 抽象**：`src/dg_platform/quality_checkpoint.py` 包装现有 pandas 规则，输出结构化 `CheckpointResult`（score / passed / failed / duration / report_path）
- **新增 APScheduler 守护模式**：`scripts/quality_scheduler.py` 默认每日 08:30 跑一次；支持 `--run-once` CLI 手动触发
- **新增 SQLite 时序存储**：`data/quality_scores.db` 单表 `quality_scores(run_date, system, score, grade, passed, failed, duration_s)`，每年 1800 行
- **新增阈值告警**：`data/quality_alerts.json` 累计所有 score < 70 的告警；console warning 立即输出
- **新增趋势图渲染**：matplotlib 5 系统折线图 → `data/quality_trend.png`
- **新增教学 notebook**：`notebook/module10.ipynb` 4 cells 演示完整闭环
- **新增 docs**：`docs/Module10.md`（与 module1-8 平级）+ Background.md §6.10 状态更新
- **保留** `scripts/run_great_expectations.py`（pandas 引擎）作为 rule set 单一来源

## Capabilities

### New Capabilities
- `scheduled-quality-monitoring`: APScheduler + Checkpoint 抽象 + 阈值告警
- `quality-score-history`: SQLite 时序存储 + 趋势图渲染

### Modified Capabilities
- `module2-quality-detection`: 增加"6.10 升级到 Checkpoint + 调度"需求，明确 `run_great_expectations.py` 仍为 rule set 源

## Impact

- **代码**：
  - 新增 `src/dg_platform/quality_checkpoint.py`（~120 行）
  - 新增 `scripts/quality_scheduler.py`（~80 行）
  - 改 `notebook/module10.ipynb`（新建）
  - 改 `scripts/run_great_expectations.py`（**不改**，仅 import 其 RULES 常量）
- **配置**：无新增环境变量；APScheduler 调度时间硬编码（08:30 daily）可改
- **依赖**：
  - `pyproject.toml` 加 `apscheduler>=3.10`（SQLite Python 内置，matplotlib 已有）
- **数据**：
  - 新增 `data/quality_scores.db`（SQLite 文件，被 .gitignore 排除）
  - 新增 `data/quality_alerts.json`（被 .gitignore 排除）
  - 新增 `data/quality_trend.png`（被 .gitignore 排除）
- **文档**：
  - `docs/Module10.md` 新增
  - `docs/Background.md §6.10` 状态更新（**已上线**）
  - `README.md` 路径 B notebook 列表：加 `module10.ipynb`（**影响学习路径 B**）
- **回滚**（≤ 30 分钟）：
  1. `rm data/quality_scores.db data/quality_alerts.json data/quality_trend.png`
  2. `rm src/dg_platform/quality_checkpoint.py scripts/quality_scheduler.py notebook/module10.ipynb`
  3. `uv remove apscheduler`
  4. 现有 `run_great_expectations.py` 不受影响
