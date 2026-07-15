## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 教学讲师（Background.md 6.12） | "4 表 JOIN 宽表 + 物化视图 + 看板"；原 plan "Phase 1 出口条件：4 个分析场景可在 OLAP 看板中切换维度实时出数" |
| 学员（module6 实操） | "跨 3 系统 JOIN 写 SQL 复杂"；"想用宽表直接查"；"想点按钮筛选维度（矿井/煤种/时间）" |
| 运维（生产环境） | "ClickHouse / Doris 5+ 分钟启动"；"Superset 部署链路过长"；"对 10 分钟 demo 框架过重" |
| 现有 DWA 3 张单系统宽表 | 已存在（dwa_sales_daily / dwa_tag_alarm / dwa_coal_quality）但**不跨主题** |

## Ideas

- [ ] **Idea 1**：用 DuckDB（已在 `pyproject.toml`）替代 ClickHouse/Doris — 0 setup，< 1s 跑 4 表 JOIN
- [ ] **Idea 2**：从 6.11 新主题目录读：`dwd/sales/dwd_vbak` + `dwd/sales/dwd_kna1` + `dwd/production/dwd_tags` + `dwd/coal_quality/dwd_samples`
- [ ] **Idea 3**：用 `mine_code` 作为跨主题 bridge key（vbak.MINE_CODE → tags.mine → samples.MINE_CODE → kna1 cross-ref）
- [ ] **Idea 4**：用 `CREATE TABLE dwa_sales_production AS SELECT ...` 模拟物化视图（写入 Delta Lake 持久化）
- [ ] **Idea 5**：保留 3 张旧 DWA 宽表 + 新增 1 张 `dwa_sales_production` 跨系统宽表（4 张并存）
- [ ] **Idea 6**：4 个分析场景 SQL 模板：产销对比 / 煤质定价 / 安全趋势 / 订单履约
- [ ] **Idea 7**：Superset 仅在 design 写演进路径（不实现）；demo 用 DuckDB CLI + matplotlib 替代
- [ ] **Idea 8**：`notebook/module12.ipynb` 演示：1) 跑 4 表 JOIN 写 dwa_sales_production；2) 4 个 SQL 场景示例；3) matplotlib 渲染关键指标图

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1 | 部署成本 / 演示时长 | 0 Docker 容器，10 分钟 demo 完整跑通 | ✅ 是 |
| 2 | 可发现性 / 教学性 | 跨主题 JOIN 自然，6.11 主题重组的回报显现 | ✅ 是 |
| 3 | 教学性 / 业务理解 | `mine_code` 是核心跨域关联键，演示后学员理解数据治理的核心 | ✅ 是 |
| 4 | 性能 / 简单 | 一次计算持久化，多次查询秒级响应 | ✅ 是 |
| 5 | 兼容性 / 平滑切换 | 旧 3 张 DWA 仍可用，6.12 是 additive | ✅ 是 |
| 6 | 教学性 / 即学即用 | 学员抄 4 个 SQL 模板即可分析新数据 | ✅ 是 |
| 7 | 演进路径 / 现实主义 | demo 阶段不重蹈 ClickHouse 5 分钟启动覆辙 | ✅ 是 |
| 8 | 教学性 / 完整闭环 | 跑 JOIN + 跑分析 + 渲染图 = 完整 demo | ✅ 是 |

---

## Plan

### 立即实现
- **Idea 编号**：1 + 2 + 3 + 4 + 5 + 6 + 7 + 8（合为 6.12 主变更）
- **初步方案**：
  1. `scripts/build_dwa_sales_production.py`：DuckDB 4 表 JOIN → 写 Delta Lake
  2. `data/lakehouse/dwa/dwa_sales_production/`：宽表存储
  3. `notebook/module12.ipynb` 3 cells 演示
  4. `docs/Module12.md` 文档
  5. 文档化 ClickHouse + Superset 演进路径
- **负责人/角色**：教学工程师
- **预计耗时**：1.5 周（与 Background.md 6.12 估时一致）

### 等待观察
- **Idea 编号**：7（Superset 部署）
- **触发条件**：6.12 稳定运行 ≥ 1 月后，Phase 3 启动节奏引入 ClickHouse + Superset
