## Why

模块一让小白「看见资产」，模块二让小白「定位问题」。但当前模块三「数据血缘全链路追溯」**根本跑不起来**——`scripts/emit_lineage.py` 用裸 `requests` 手写的 GMS 调用协议是错的：

| 项 | DataHub v1.6 官方要求（deepwiki 核实） | `emit_lineage.py` 现状 |
|----|--------------------------------------|----------------------|
| 端点 | `POST /aspects?action=ingestProposal`，包 `proposal` 外层 | 裸 `POST /aspects`，无外层 ❌ |
| `aspect` 字段 | `{"value":"<json string>","contentType":"application/json"}` | 直接对象 ❌ |
| 上游 URN 字段名 | `dataset` | `upstreamEntity` ❌ |
| `auditStamp` | required（有默认值，不会被拒） | 缺省 ⚠️ |

后果：脚本可能返回 200 但 upstream URN 被静默丢弃为 null，血缘写进 MySQL 却是空的，**DataHub UI Lineage 标签页永远不出现边**。`docs/Module1.md` 里「✅ 实测 GMS 上游 lineage 可正常写入」「已移除 Neo4j fallback」是**未经核实的作者断言**——全项目没有任何脚本真正查询 GMS 的 `upstreamLineage` aspect 并断言其非空（`verify_datahub_ui.py` / `snapshot_datahub_ui.py` 只是 UI 截图工具）。

同时 `scripts/emit_lineage.py` 仍 `import neo4j` 且保留 `write_lineage_to_neo4j()` 死代码，与 Module1.md「已移除 Neo4j」自相矛盾，学员看到 `import neo4j` 会困惑。

本变更实现模块三：**先把血缘层真正修对**（重写为官方 SDK 模式，参照同项目已验证可用的 `scripts/emit_via_rest_emitter.py`），再补 3 条 DWA 加工血缘边，最后建一个**离线**的教学 notebook 让小白理解血缘。用 OpenSpec 流程追踪，避免重蹈「写完声称能用、实则没验证」的覆辙。

## What Changes

- **重写 `scripts/emit_lineage.py`**：弃用裸 `requests`，改用 `DatahubRestEmitter` + `MetadataChangeProposalWrapper` + `schema_classes.UpstreamLineageClass`（与 `emit_via_rest_emitter.py` 同一已验证模式）；删除 `import neo4j` 与 `write_lineage_to_neo4j()` 死代码与 fallback 分支
- **修正 `lineage_recipe.yaml`**：`sap_erp.vbak/vbap → lims.samples` 的 `join_key` 由错误的 `KUNNR` 改为诚实的语义说明（LIMS 无 KUNNR 字段，跨系统真实关联键 MINE_CODE 也不在 vbak；此边是**声明式业务关系**而非字面 JOIN，description 中写明）
- **扩展 `lineage_recipe.yaml`**：新增 3 条 DWA 加工血缘边（`dwd.vbak → dwa_sales_daily` / `pi_system.tags → dwa_tag_alarm` / `lims.samples → dwa_coal_quality`），与 `scripts/build_dwa_models.py` 真实聚合派生一致
- **扩展 `scripts/emit_via_rest_emitter.py`**（或新增注册逻辑）：把 3 张 DWA 表也注册为 dataset 实体（当前仅注册 12 张源表，DWA 表未注册，血缘边会指向悬空节点）
- **新增 `scripts/verify_lineage.py`**：查询 GMS `upstreamLineage` aspect 断言非空 + 查 OpenSearch 索引确认同步，作为「真验证」工具（替代当前缺失的 aspect 断言）
- **新增 `scripts/query_lineage.py`**（只读）：查询 GMS 已写入血缘并输出 JSON，供 notebook 经 `subprocess` 调用获取「DataHub 真图」与 recipe 自建图对比（notebook 不直连服务，联网查询走此脚本）
- **新增 `notebook/module3.ipynb`**：离线教学 notebook，沿用模块一/二「痛点故事 → 3 步学习节奏 → 业务影响白话」风格；**不得**直接调 GMS/OpenSearch（遵循 module1/module2 spec 约束）
- **新增 `src/dg_education/lineage.py`**：notebook 友好的离线血缘 API（从 `lineage_recipe.yaml` 读图、上下游遍历、ASCII 可视化、blast-radius 计算）
- **更新 `src/dg_education/visualization.py`**：新增 1-2 个血缘图可视化函数
- **更新 `src/dg_education/__init__.py`**：导出新 API
- **更新 `docs/Module3.md`**：把「疑点已澄清」后的正确实现步骤写回（端点、字段名、verify 脚本、诚实的关系语义）

**BREAKING**：`emit_lineage.py` 的函数签名与 CLI 行为改变（调用方仍只是 `uv run python scripts/emit_lineage.py`，无外部消费者）；`lineage_recipe.yaml` 的 `join_key` 语义变更。

## Capabilities

### New Capabilities

- `data-lineage-ingestion`：通过 GMS REST（官方 SDK 模式）写入 `upstreamLineage` aspect 的血缘录入能力，含 recipe 配置、写入脚本、真验证脚本
- `module3-lineage-notebook`：模块三教学 notebook + 离线血缘分析 API

### Modified Capabilities

- `asset-metadata-ingestion`：12 张源表 → 扩展为 15 张（新增 3 张 DWA 表的 dataset 注册），DWA 表 URN 形如 `urn:li:dataset:(urn:li:dataPlatform:dwa,<dwa_table>,PROD)`

## Impact

**受影响模块**：
- 模块一（`asset-metadata-ingestion`）：DWA 表注册属增量，不破坏 12 张源表现有 spec
- 模块二（`module2-quality-detection`）：其 spec 仅负向提及 `emit_lineage.py`（notebook 不得调用），本变更不触及 module2.ipynb
- 模块三（本变更）：新增

**代码影响**：
- 重写：`scripts/emit_lineage.py`（~280 行 → ~120 行，删 neo4j 死代码）
- 修改：`lineage_recipe.yaml`（修正 join_key + 加 3 条 DWA 边）、`scripts/emit_via_rest_emitter.py`（加 3 张 DWA 表注册）或等价逻辑、`src/dg_education/visualization.py`、`src/dg_education/__init__.py`、`docs/Module3.md`
- 新增：`scripts/verify_lineage.py`、`scripts/query_lineage.py`、`src/dg_education/lineage.py`、`notebook/module3.ipynb`
- 依赖：`datahub` SDK（`acryldata/datahub`）已在 `emit_via_rest_emitter.py` 使用，需确认 `pyproject.toml` 已声明；`networkx`（血缘图遍历）如未声明需新增

**数据影响**：
- 写入 GMS：8 条血缘边（原 5 修正 + 新增 3 DWA）+ 3 张 DWA 表的 dataset 注册
- 不修改 `data/historical/` 与 `data/lakehouse/` 任何源数据
- notebook 仅读 `data/historical/` Parquet 与 `lineage_recipe.yaml`

**下游影响**：
- 模块四/五（清洗/ELT）notebook 可复用 `dg_education.lineage` API
- Phase 2 自动血缘（模块九）以本变更修正后的 recipe 格式为基线

**回滚计划**：
- `git revert` 本次 commit
- GMS 侧：`verify_lineage.py` 可加 `--purge` 选项删除写入的 upstreamLineage aspect 与 DWA dataset（幂等清理）
- 模块一/二 notebook 与现有脚本不受影响（emit_lineage.py 无外部消费者）
