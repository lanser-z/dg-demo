## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 教学讲师（Background.md 6.10） | "从「一次性 GE CLI」升级为「定时任务 + 持久化报告 + Owner 通知」"；原"看到分数低自己判断"流程不可扩展 |
| 学员（module2 实操） | "跑一次 GE 之后，报告丢了就没"；"看不出分数趋势"；"5 系统独立跑，没有统一面板" |
| 运维（生产环境假想） | "Airflow 部署成本高"；"ClickHouse 引入额外基础设施"；"邮件 + MinIO 报告存储对 demo 太重" |
| 现有 run_great_expectations.py | 是 pandas 模拟的 GE 风格规则（**未 import great_expectations**），用 CLI 输出 + JSON 文件报告 |

## Ideas

- [ ] **Idea 1**：把现有 pandas 规则包装为 `QualityCheckpoint` 抽象（不引真 GE 库），保留 `run_great_expectations.py` 不变
- [ ] **Idea 2**：用 **APScheduler** Python 库做调度（无 Docker 容器，30 秒启动），替代 Airflow standalone
- [ ] **Idea 3**：用 **SQLite** 存质量分数历史（1800 行/年，单文件 ~10KB），替代 ClickHouse
- [ ] **Idea 4**：分数 < 70 阈值时写 `data/quality_alerts.json` + console warning，替代邮件（demo 阶段）
- [ ] **Idea 5**：matplotlib 渲染分数趋势图（5 系统折线，X 轴时间），写入 `data/quality_trend.png`
- [ ] **Idea 6**：`scripts/quality_scheduler.py` 提供 `--run-once` CLI 模式（手动触发）+ `apscheduler` 守护模式
- [ ] **Idea 7**：6.9 调研的"GE Checkpoint 真 API"（ephemeral context）作为未来升级路径写入 design，不在本次实现
- [ ] **Idea 8**：新增 `notebook/module10.ipynb` 演示：1) 手动触发 Checkpoint → 2) 查 SQLite 历史 → 3) 渲染趋势图 → 4) 模拟告警

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1 | 可维护性 / 学习曲线 | 保留 demo 用 pandas，规则不动；生产升级真 GE 仅替换 Checkpoint 抽象 | ✅ 是 |
| 2 | 部署成本 / 演示时长 | 30 秒启动 vs Airflow 5 分钟，10 分钟 demo 内能跑通 | ✅ 是 |
| 3 | 部署成本 / 查询能力 | 1 文件 0 配置，pandas + matplotlib 原生支持 | ✅ 是 |
| 4 | 教学性 / 成本 | console + JSON 文件模拟邮件；学生能看到"告警流" | ✅ 是 |
| 5 | 教学性 | 5 系统折线图能直观体现"哪个系统分数在下降" | ✅ 是 |
| 6 | 灵活性 | `--run-once` 适合教学 + 调试；守护模式适合生产 | ✅ 是 |
| 7 | 演进路径 | 写明未来怎么从 pandas 切到真 GE 库 | ✅ 是 |
| 8 | 教学性 | 与 module2（一次性 GE）、module6（DWA 即席）、module9（auto lineage）形成完整教学闭环 | ✅ 是 |

---

## Plan

### 立即实现
- **Idea 编号**：1 + 2 + 3 + 4 + 5 + 6 + 7 + 8（合为 6.10 主变更）
- **初步方案**：
  1. `src/dg_platform/quality_checkpoint.py`：Checkpoint 抽象（接收 rule set + data path → CheckpointResult）
  2. `scripts/quality_scheduler.py`：APScheduler + SQLite + matplotlib 趋势图
  3. `notebook/module10.ipynb`：4 cells 演示
  4. `data/quality_scores.db`：SQLite 表
  5. `data/quality_alerts.json`：阈值告警记录
  6. `docs/Module10.md`：新增（与 Module1-8 平级）
  7. `docs/Background.md §6.10`：加"已上线"状态
  8. `README.md` 路径 B notebook 列表：加 `module10.ipynb`
- **负责人/角色**：教学工程师
- **预计耗时**：1.5 周（与 Background.md 6.10 Phase 2 估时一致）

### 等待观察
- **Idea 编号**：无（idea 7 是写明演进路径，不在本变更实现）
- **触发条件**：背景 6.10 已完成时，6.11/6.12 可能复用 SQLite 历史表做质量对比

## 变更产出（可选）

已创建 `openspec/changes/module10-scheduled-quality-monitoring/` 承载本变更的 proposal / design / specs / tasks 产物。
