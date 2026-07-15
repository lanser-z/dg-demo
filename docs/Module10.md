# 模块十实施步骤：定时质量监控

> **归属**：Background §6.10 / Phase 2
> **演示时长**：10 分钟
> **新增依赖**：`apscheduler>=3.10`
> **新增产物**：`src/dg_platform/quality_checkpoint.py`、`scripts/quality_scheduler.py`、`notebook/module10.ipynb`、`docs/Module10.md`、`data/quality_scores.db`、`data/quality_alerts.json`、`data/quality_trend.png`、`data/quality_reports/*.json`

---

## 1. 模块概述

### 1.1 教学目标

把模块二（Phase 1）演示版的一次性 GE CLI 升级为"定时调度 + 持久化历史 + 阈值告警"三件套，
让学员看到「数据治理从「有评分」到「系统主动通知」的工程化能力」。

### 1.2 与 module2 的关系

| 维度 | module2（Phase 1） | module10（Phase 2 / 6.10） |
|------|-------------------|----------------------------|
| 执行方式 | 手动跑 `scripts/run_great_expectations.py` | APScheduler 每日 08:30 自动跑 + `--run-once` 手动 |
| 报告存储 | CLI 输出 + 单次 JSON | SQLite 时序表 `data/quality_scores.db` |
| 告警 | 无 | `score < 70` 写 `data/quality_alerts.json` + `logging.warning` |
| 趋势 | 无 | matplotlib 5 系统折线 `data/quality_trend.png` |
| 规则源 | `RULES` 字典 | **同一份** `RULES`（不重写） |
| 引入的真实服务 | 无 | 无（SQLite + APScheduler + matplotlib 全部 Python 内置） |

### 1.3 评分等级

`QualityCheckpoint` 使用与 module2 CLI 不同的 grade 阈值（**这是有意为之，不是 bug**）：

| 等级 | 分数范围 | 含义 |
|------|----------|------|
| A | ≥ 90 | 优秀，数据可直接使用 |
| B | 80 ~ 89 | 良好，少量质量问题 |
| C | 70 ~ 79 | 及格，存在较多问题需关注 |
| D | < 70 | **不及格，自动告警**（`data/quality_alerts.json`） |

> module2 CLI 沿用 ≥ 95/85 旧阈值；module10 升级到 ≥ 90/80 新阈值（与 `Background.md §6.10` 一致）。

### 1.4 告警阈值

`ALERT_THRESHOLD = 70`（可被环境变量 `CHECKPOINT_THRESHOLD` 覆盖）。

| 事件 | 行为 |
|------|------|
| `score >= 70` | 无操作 |
| `score < 70`  | `logging.warning` 输出 + 追加 alert JSON 到 `data/quality_alerts.json` |

---

## 2. 文件清单

```
dg-demo/
├── pyproject.toml                                # +apscheduler>=3.10
├── scripts/
│   ├── run_great_expectations.py                 # 6.10 docstring 升级
│   └── quality_scheduler.py                      # 新增：APScheduler + SQLite + 告警 + 趋势图
├── src/dg_platform/
│   └── quality_checkpoint.py                     # 新增：QualityCheckpoint 抽象
├── notebook/
│   └── module10.ipynb                            # 新增：4 cells 教学
├── docs/
│   ├── Module10.md                               # 本文件
│   └── Background.md §6.10                       # 状态：已上线
└── data/                                         # 全部 .gitignore 排除
    ├── quality_scores.db                         # SQLite 时序表
    ├── quality_alerts.json                       # 阈值告警累计
    ├── quality_trend.png                         # 5 系统折线
    └── quality_reports/<system>__<table>.json    # 单表详细报告
```

---

## 3. SQLite 时序表

### 3.1 表结构

`data/quality_scores.db` 单表 `quality_scores`，主键 `(run_date, system, "table")`：

| 列 | 类型 | 说明 |
|----|------|------|
| `run_date` | TEXT | 形如 `2026-07-15` |
| `system` | TEXT | `sap_erp` / `pi_system` / `lims` / `oa` |
| `"table"` | TEXT | `vbak` / `vbap` / `tags` 等 |
| `score` | REAL | 0–100 |
| `grade` | TEXT | `A` / `B` / `C` / `D` |
| `passed` | INTEGER | 通过的规则数 |
| `failed` | INTEGER | 失败的规则数 |
| `duration_s` | REAL | Checkpoint 耗时（秒） |

> `"table"` 加引号是因为 `table` 是 SQLite 保留字。

### 3.2 写入契约

`scripts/quality_scheduler.py::_write_scores` 用 `INSERT OR REPLACE`：
同一 `(run_date, system, table)` 重复跑会覆盖旧行（重跑场景）。

### 3.3 容量估算

5 系统 × 6 表 × 1 年/天 = **1800 行/年**。
SQLite 单文件 ~10KB（实测运行一次后 `data/quality_scores.db` 12KB），
够 demo 阶段 5+ 年使用。

---

## 4. 调度模式

### 4.1 守护模式（默认）

```bash
uv run python scripts/quality_scheduler.py
# scheduler started, next run: 08:30 (Ctrl+C to exit)
```

- `BlockingScheduler` + `CronTrigger(hour=8, minute=30)` 注册 `quality_daily` job
- 时区 `Asia/Shanghai`
- `max_instances=1` + `coalesce=True`：错过 1 次不会补跑多次
- SIGINT/SIGTERM → `scheduler.shutdown(wait=False)` → 退出码 0

### 4.2 单次模式（教学 / CI）

```bash
uv run python scripts/quality_scheduler.py --run-once
# ✅ quality check done: 4 systems checked, 6 rows in 3.4s
# trend chart: /path/to/data/quality_trend.png
```

### 4.3 退出码

| 场景 | 退出码 |
|------|--------|
| 5 系统全部跑通 | 0 |
| 1 个 system 抛未捕获异常 | 1（仍写其他系统的 DB 行） |

---

## 5. 教学 notebook

`notebook/module10.ipynb` 4 cells：

| Cell | 内容 | 验证点 |
|------|------|--------|
| 1 | `run_all_systems()` | `✅ quality check done: 6 tables checked` |
| 2 | `query_history(days=30)` | DataFrame 6 行 × 8 列 |
| 3 | `plot_trend_lines()` + `IPython.display.Image` | PNG ≥ 10 KB |
| 4 | 模拟 score=60 告警 | alerts.json +1 条，DB 不污染 |

### 5.1 跑法

```bash
cd notebook/
uv run jupyter lab module10.ipynb
```

### 5.2 关键 API

```python
from dg_platform.quality_checkpoint import QualityCheckpoint, CheckpointResult
from scripts.quality_scheduler import run_all_systems, query_history, plot_trend_lines

# 跑一次所有系统
results = run_all_systems()        # list[CheckpointResult]

# 查历史（默认 30 天）
df = query_history(days=30)        # pd.DataFrame

# 渲染趋势图
png = plot_trend_lines(days=30)    # Path | None
```

---

## 6. CLI 用法汇总

```bash
# ── 教学 / CI ──
uv run python scripts/quality_scheduler.py --run-once

# ── 守护（生产 / demo 演示）──
uv run python scripts/quality_scheduler.py
# Ctrl+C 优雅退出

# ── 单独跑一次 Checkpoint（绕过调度器）──
uv run python -c "
import sys; sys.path.insert(0, 'src')
from dg_platform.quality_checkpoint import QualityCheckpoint
r = QualityCheckpoint('sap_erp', 'vbak').run()
print(r)
"

# ── 查 SQL 历史 ──
sqlite3 data/quality_scores.db \
  "SELECT run_date, system, score, grade FROM quality_scores WHERE score < 70"
```

---

## 7. 故障排查

| 症状 | 原因 | 修复 |
|------|------|------|
| `ImportError: cannot import name 'RULES' from 'scripts.run_great_expectations'` | `scripts/` 缺 `__init__.py` | 已规避：`quality_checkpoint.py` 用 `sys.path.insert` 注入 |
| `sqlite3.OperationalError: near "table": syntax error` | SQL 关键字未引号 | 已修复：`"table"` 加引号 |
| `TypeError: Object of type int64 is not JSON serializable` | pandas/numpy 类型 | 已修复：`_json_default` 用 `.item()` 转换 |
| 趋势图中文字体方块化 | 缺中文字体 | 已设置 `Noto Sans CJK SC`；如缺字体降级到 `DejaVu Sans` |
| `scheduler.shutdown(wait=False)` 不退 | SIGTERM 默认动作 | 已注册 SIGINT/SIGTERM handler |
| 重复跑 1 天产生多行 | 用 `INSERT` 而非 `INSERT OR REPLACE` | 已用 `INSERT OR REPLACE` |

---

## 8. 演进路径（Phase 3 写入但不实现）

> 见 `openspec/changes/module10-scheduled-quality-monitoring/design.md` 第 6 节。

替换 `_run_pandas()` → 真 `great_expectations` Checkpoint：
1. `pyproject.toml` 加 `great-expectations>=1.0`
2. `RULES` 字典 → `ExpectationSuite` YAML
3. APScheduler → Airflow `GXValidateCheckpointOperator`
4. 告警 → Slack/Email
5. SQLite → ClickHouse

---

## 9. 验证清单

```bash
# 1. 依赖
uv run python -c "import apscheduler; print(apscheduler.__version__)"  # ≥ 3.10

# 2. 单次跑通
uv run python scripts/quality_scheduler.py --run-once
# 预期：✅ quality check done: 4 systems checked, 6 rows in <Xs
# 预期：data/quality_scores.db / data/quality_alerts.json / data/quality_trend.png 都生成

# 3. 守护模式 SIGINT 退出码
(uv run python scripts/quality_scheduler.py & PID=$!; sleep 2; kill -INT $PID; wait $PID; echo $?)
# 预期：exit=0，无 traceback

# 4. Notebook 4 cells 全部执行
uv run jupyter nbconvert --to notebook --execute notebook/module10.ipynb --output /tmp/check.ipynb
# 预期：成功，无 traceback
```
