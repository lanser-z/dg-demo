## 1. 依赖与基础设施

- [ ] 1.1 在 `pyproject.toml` dependencies 新增 `apscheduler>=3.10`，`uv sync` 验证
- [ ] 1.2 SQLite 由 Python 内置 `sqlite3` 提供，无需新依赖

## 2. QualityCheckpoint 抽象

- [ ] 2.1 创建 `src/dg_platform/quality_checkpoint.py`：`QualityCheckpoint` 类 + `CheckpointResult` dataclass
- [ ] 2.2 复用 `from scripts.run_great_expectations import RULES`（不动原文件）
- [ ] 2.3 `run()` 方法遍历 RULES 调用现有 `expect_*` 函数，累加 passed/failed，输出 `score = passed / (passed + failed) * 100`
- [ ] 2.4 grade 映射：≥90 A, ≥80 B, ≥70 C, <70 D

## 3. SQLite 时序存储

- [ ] 3.1 `data/quality_scores.db` 自动创建表 `quality_scores(run_date, system, table, score, grade, passed, failed, duration_s)` 主键 `(run_date, system, table)`
- [ ] 3.2 `INSERT OR REPLACE` 写入
- [ ] 3.3 提供 `query_history(days=30) -> pd.DataFrame` 函数

## 4. APScheduler 调度器

- [ ] 4.1 创建 `scripts/quality_scheduler.py`：`run_all_systems()` 遍历 5 系统 → 跑 Checkpoint → 写 SQLite → 触发告警 → 渲染趋势图
- [ ] 4.2 `--run-once` CLI 模式：单次执行后 exit
- [ ] 4.3 守护模式：APScheduler `BlockingScheduler` + `CronTrigger(hour=8, minute=30)` 注册 `quality_daily` job
- [ ] 4.4 SIGINT 优雅退出（`scheduler.shutdown(wait=False)`）

## 5. 阈值告警

- [ ] 5.1 score < 70 时 `logging.warning` 输出 `quality_alert system={s} score={n}`
- [ ] 5.2 追加 JSON 对象到 `data/quality_alerts.json`（数组形式），文件不存在时自动创建
- [ ] 5.3 alert 结构 `{"timestamp": ISO, "system": str, "score": float, "grade": "D"}`

## 6. 趋势图渲染

- [ ] 6.1 `plot_trend_lines(days=30)` 从 SQLite 读历史，matplotlib 5 系统折线，X 轴日期，Y 轴 0-100
- [ ] 6.2 保存 `data/quality_trend.png`
- [ ] 6.3 中文字体设置 `plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans']`
- [ ] 6.4 空历史跳过 plot（不崩溃）

## 7. 教学 notebook

- [ ] 7.1 创建 `notebook/module10.ipynb` 4 cells：
  - cell 1: import + 调 `run_all_systems()` 单次
  - cell 2: 查 SQLite 历史 `query_history(days=30)`
  - cell 3: 渲染趋势图 + display PNG
  - cell 4: 模拟 1 个 score=60 触发告警（不入 DB）
- [ ] 7.2 跑 notebook 验证 4 cells 都成功执行

## 8. 文档

- [ ] 8.1 创建 `docs/Module10.md`（与 module1-8 平级）
- [ ] 8.2 更新 `scripts/run_great_expectations.py` 顶部 docstring 加 "6.10 升级" 注释
- [ ] 8.3 更新 `docs/Background.md §6.10` 标"已上线"
- [ ] 8.4 更新 `README.md` 路径 B notebook 列表：加 `module10.ipynb`（**影响学习路径 B**）

## 9. 验证与归档

- [ ] 9.1 跑 `uv run python scripts/quality_scheduler.py --run-once` 验证 5 系统全部出分
- [ ] 9.2 跑 `uv run python scripts/quality_scheduler.py` 守护模式 30 秒，`Ctrl+C` 验证退出码
- [ ] 9.3 验证 `data/quality_scores.db` 含 5 行
- [ ] 9.4 验证 `data/quality_trend.png` 文件大小 ≥ 10 KB
- [ ] 9.5 `openspec validate module10-scheduled-quality-monitoring` 通过
- [ ] 9.6 `openspec archive module10-scheduled-quality-monitoring --yes` 归档
