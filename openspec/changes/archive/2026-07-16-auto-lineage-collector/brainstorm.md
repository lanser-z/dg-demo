# auto-lineage-collector — 探索阶段

## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 开发者（代码审查） | `build_dwa_models.py` 的 3 个 DWA ETL 函数（`build_dwa_sales_daily` / `build_dwa_tag_alarm` / `build_dwa_coal_quality`）没有接 `LineageEmitter`，auto 通道只覆盖了 `build_dwa_sales_production.py` 这 1 个入口 |
| Module3 文档 | 声称 "auto 通道已完成"（`docs/Module3.md` §6.9），但实际上只有 `dwa_sales_production` 接了 |
| `verify_auto_lineage.py` | 定义了 6 个 ETL job（`ingest_dwd` / 3 个 DWA / 3 个 dim），但 `build_dwa_models.py` 的 3 个函数从未被 LineageEmitter 包装过 |

## Ideas

- [ ] 想法 1：为 `build_dwa_models.py` 的 3 个 DWA ETL 函数接入 `LineageEmitter`（`build_dwa_sales_daily` / `build_dwa_tag_alarm` / `build_dwa_coal_quality`）
- [ ] 想法 2：为 `build_dimension_tables.py` 的 3 个 dim 函数接入 `LineageEmitter`（`build_dim_mine` / `build_dim_customer` / `build_dim_material`）
- [ ] 想法 3：为 `ingest_to_deltalake.py` --layer dwd 接入 `LineageEmitter`（ODS → DWD 加工血缘）
- [ ] 想法 4：抽取共享的 lineage emit 辅助函数，减少 ETL 入口的代码重复
- [ ] 想法 5：更新 `verify_auto_lineage.py` 对接新接入的 job

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 想法 1 | 可观测性 / 数据治理完整性 | 完成 auto 通道对 3 个 DWA ETL 的覆盖，Module3 文档描述与实际一致；`verify_auto_lineage.py` 中 6 个 job 全部有 lineage emit | ✅ 是 |
| 想法 2 | 可观测性 | 3 个 dim 函数目前是 ETL 任务但无 lineage，补充后血缘链路更完整（ODS → DWD → dim） | ✅ 是 |
| 想法 3 | 可观测性 | ODS→DWD 加工血缘当前只靠 `lineage_recipe.yaml` 的 `processing_lineage` 兜底；接入 auto 通道后自动发现更可靠 | ⚠️ 可选（当前 yaml 够用） |
| 想法 4 | 可维护性 | 3 个函数都要写 `emit_output` + `__exit__` 调用，抽取共享函数降低重复 | ✅ 是（减少代码重复） |
| 想法 5 | 可维护性 | `verify_auto_lineage.py` 已有框架，更新 EXPECTED_INPUT_FRAGMENTS 即可 | ✅ 是 |

---

## Plan

### 立即实现

- **Idea 编号**：想法 1 + 想法 4（打包实现）
- **初步方案**：
  1. 在 `build_dwa_models.py` 的 `main()` 中，用 `with LineageEmitter(job, sql=SQL)` 包装每个 DWA ETL 函数
  2. 抽取共享的 `emit_and_close(emitter, output_urn)` 辅助函数，减少每个入口的 boilerplate
  3. 更新 `verify_auto_lineage.py` 的 `EXPECTED_INPUT_FRAGMENTS`，确认 6 个 job 全部被覆盖
- **预计耗时**：约 2 小时（已摸清现状，只需接入 + 验证）

### 等待观察

- **Idea 编号**：想法 2（dim 函数）+ 想法 3（ingest_to_deltalake）
- **等待原因**：当前 `verify_auto_lineage.py` 中 `ingest_dwd` job 没有实际 emit（`ingest_to_deltalake.py` 完全没有接 LineageEmitter），需要单独实现；dim 函数是可选的完善项
- **触发条件**：想法 1 验证通过后继续实现想法 2；想法 3 需要额外评估价值

## 变更产出

创建 **Change Proposal**：将想法 1 + 想法 4 打包为正式变更，实现 `build_dwa_models.py` 的 3 个 DWA ETL 入口完整接入 LineageEmitter auto 通道。
