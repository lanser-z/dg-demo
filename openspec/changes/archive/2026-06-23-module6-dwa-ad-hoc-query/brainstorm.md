# 模块六：DWA 宽表分析 + DuckDB 即席查询 — 变更发掘

## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 业务分析师 | 「等 IT 排期 3 天才能拿到数据」，临时分析需求响应太慢 |
| 项目负责人 | 模块五产出了 3 张 DWA 宽表，但没验证业务人员能不能直接用起来 |
| 运维/数据工程师 | 当前没有即席查询能力，所有分析都要写正式 ETL 任务 |
| 业务部门领导 | 想看「10 月各矿井日产量」这样的临时数据，需要能快速自助查询 |

## Ideas

- [ ] 想法 1：**在 module5.ipynb 中补充即席查询验证步骤**。复用 `build_dwa_models.py` 的 DuckDB 连接，在 notebook 中展示步骤 2~5 的即席查询代码（销售趋势 / 告警排名 / 月度煤质 / 产销对比），验证 3 张 DWA 表能直接出数。

- [ ] 想法 2：**用 DuckDB CLI 替代 notebook 作为即席查询入口**。业务人员不需要打开 Jupyter，直接在终端执行 `duckdb -c "SELECT ..."` 即可查 DWA 表。提供快速命令速查表。

- [ ] 想法 3：**补充 4 个分析场景的 SQL 模板**，放在 `docs/Module6.md` 中供业务人员参考，降低自己写 SQL 的门槛。

- [ ] 想法 4：**补充 4 个分析场景的 SQL 模板**，放在 `docs/Module6.md` 中供业务人员参考，降低自己写 SQL 的门槛。

- [ ] 想法 5：**给 3 张 DWA 表补充探索性分析**（如 `dwa_sales_daily` 的日环比、`dwa_tag_alarm` 的告警趋势），不只展示聚合结果，还展示数据分布特征。

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1 | 用户体验 / 可观测性 | 业务人员能自助验证数据可用性，无需等 IT；模块五的教学闭环完整 | ✅ 是 |
| 2 | 用户体验 / 可维护性 | CLI 查询零门槛，业务人员打开终端就能查；减少对 Jupyter 的依赖 | ✅ 是（与 Idea 1 并行） |
| 3 | 可维护性 / 可扩展性 | SQL 模板降低业务人员写 JOIN 的难度，减少无效 SQL 求助 | ✅ 是（低实现成本） |
| 4 | 性能 / 可扩展性 | 根据 [Tavily 搜索](https://motherduck.com/learn/fastest-olap-databases-compared)，DuckDB 在单节点 <100GB 规模下性能优于 ClickHouse，2025 年 10 月 ClickBench 排名第一。本项目教学数据规模（约 1GB Parquet）完全在 DuckDB 舒适区，在 notebook 中补充「为什么用 DuckDB 而不是 ClickHouse」的性能对比说明，能帮业务人员理解选型逻辑。**补充：** DataHub 是元数据管理平台，不直接执行 SQL 查询，其 MCP Server 和 AI 集成（如 `get_dataset_queries`）是辅助生成 SQL，不是即席查询引擎。因此即席查询能力必须由独立 OLAP 引擎（DuckDB/ClickHouse/Doris）提供，不能依赖 DataHub。 | ✅ 是（值当前做，无需等 Phase 2） |
| 5 | 可观测性 / 数据质量 | 探索性分析能帮助发现 DWA 表聚合逻辑的问题，是数据验证的一部分 | ✅ 是（补充 Idea 1） |

---

## Plan

### 立即实现

- **Idea 编号**：Idea 1 + Idea 3 + Idea 4（性能对比说明）
- **初步方案**：
  1. 在 `notebook/module5.ipynb` 中补充模块六的痛点故事和 4 个分析场景验证 cell
  2. 在 `docs/Module6.md` 中补充 SQL 模板和快速命令速查
  3. 在文档中补充「为什么用 DuckDB」的性能说明（基于 ClickBench 数据）
- **关联 artifact**：`notebook/module5.ipynb`（已有步骤 2~5 的即席查询代码）、`docs/Module6.md`（刚创建）
- **预计耗时**：0.5 天

### 等待观察

- **Idea 编号**：Idea 2（DuckDB CLI 速查）、Idea 5（探索性分析补充）
- **等待原因**：可以随 Idea 1 一起实现，不阻塞；探索性分析需要先跑一遍即席查询确认数据质量再补充
- **触发条件**：业务人员反馈「不知道终端怎么查」时提供 CLI 速查；即席查询跑通后补充探索性分析

## 变更产出

本 brainstorming 产生的「立即实现」Idea 对应：

- **Change Proposal**：模块六 DWA 宽表即席查询验证
- **内容**：在 `notebook/module5.ipynb` 中补齐模块六的痛点故事和 4 个场景验证；在 `docs/Module6.md` 中补充 SQL 模板、快速命令和性能对比说明
