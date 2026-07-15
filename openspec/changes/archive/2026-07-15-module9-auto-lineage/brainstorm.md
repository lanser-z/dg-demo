## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 教学讲师（Background.md 6.3 节） | 6.3 演示版血缘 "5 条边手工维护，无法扩展到 N×M 规模"；6.9 节明确 "升级为 Spark/Flink 任务从 SQL 解析 FROM/JOIN 自动产出" |
| 学员（模块 3 notebook 实操） | 手工 YAML 维护成本高，"改一个表要去 3 个地方同步：SQL、YAML、emit_lineage.py" |
| 运维（生产环境假想） | 5 系统 × N 张表规模下 "手工模式不可扩展"；ES 与 GMS 可能短暂不一致 |
| DataHub UI 用户 | "业务人员读血缘图谱：当前 DataHub v1.6 UI 是英文 + 工程师视角"（未解） |

## Ideas

- [ ] **Idea 1**：ETL 任务完成后自动 emit OpenLineage 事件（START/COMPLETE）到 Kafka topic `openlineage.events`；DataHub actions 服务消费后写 GMS `upstreamLineage` aspect
- [ ] **Idea 2**：在 `scripts/ingest_to_deltalake.py` / `build_dwa_models.py` / `build_dimension_tables.py` 三个 ETL 入口插入轻量级 `LineageEmitter` 上下文管理器（OpenLineage Python client）
- [ ] **Idea 3**：解析每个 ETL SQL 的 `FROM`/`JOIN` 子句自动推导 `inputs` / `outputs`；无需用户写 YAML
- [ ] **Idea 4**：保留 `lineage_recipe.yaml` 作为兜底通道——auto-discovery 不出来的跨系统业务 JOIN（如 `sap_erp.vbak → lims.samples` 按 KUNNR 关联）走手工路径
- [ ] **Idea 5**：用 Playwright 截图 module9 demo 前后血缘图对比，沉淀到 `notebook/step_images/`
- [ ] **Idea 6**：用 `DataHub v1.6.0` 的 `upstreamLineage` aspect 标准格式 + OpenLineage 1-1 映射表，验证兼容性（已知风险点）
- [ ] **Idea 7**：CI 钩子：每次新加 DWD/DWA 表时，自动检查 lineage 是否覆盖（无主表 → 报警）
- [ ] **Idea 8**：血缘查询 API：在 module9 notebook 里同时查 1 条手工边 + 1 条自动边的可视化对比

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1 | 可维护性 / 可观测性 | 0 → N×M 边自动发现；新增表零配置 | ✅ 是 |
| 2 | 开发者体验 | 业务代码改动 ≤ 5 行；ETL 脚本看不出"在打点" | ✅ 是 |
| 3 | 可观测性 | 真实反映 SQL 实际执行的依赖图，比手工声明更准 | ✅ 是 |
| 4 | 鲁棒性 | 业务跨系统 JOIN 不依赖 SQL 解析（SQL 解析对这种语义不友好） | ✅ 是 |
| 5 | 教学性 | 学员能看到"auto vs manual" 对比的截图证据 | ✅ 是 |
| 6 | 风险验证 | Background.md 6.9 末尾"待验证风险"的直接回应 | ✅ 是 |
| 7 | 可观测性 / 治理成熟度 | 把"血缘覆盖率"纳入数据资产 SLA 评分卡 | ❌ 否（超 Phase 2 范围） |
| 8 | 教学性 | 一节 notebook 演示两种采集方式 | ✅ 是 |

---

## Plan

### 立即实现
- **Idea 编号**：1 + 2 + 3 + 4 + 6 + 8（合为 6.9 主变更）
- **初步方案**：
  1. 在 ETL 入口插 `LineageEmitter` 上下文管理器（Idea 2）
  2. SQL 解析器从 `FROM` / `JOIN` 推导 inputs（Idea 3）
  3. emit OpenLineage 事件到 Kafka（Idea 1）
  4. DataHub actions 消费并写 GMS（Idea 1）
  5. 保留 `lineage_recipe.yaml` 兜底（Idea 4）
  6. 验证 v1.6.0 aspect 兼容性（Idea 6）
  7. module9 notebook 演示 auto + manual 对比（Idea 8）
- **负责人/角色**：教学工程师
- **预计耗时**：2 周（与 Background.md 6.9 Phase 2 估时一致）

### 等待观察
- **Idea 编号**：7
- **等待原因**：血缘覆盖率 SLA 评分卡是 Phase 3 质量运营范畴
- **触发条件**：DataHub 接入稳定运行 ≥ 1 个月后，参考 Phase 3 启动节奏

## 变更产出（可选）

已创建 `openspec/changes/module9-auto-lineage/` 承载本变更的 proposal / design / specs / tasks 产物。
