# module3-lineage-notebook Specification

## Purpose

模块三「数据血缘全链路追溯」教学 notebook（`notebook/module3.ipynb`）及其离线血缘分析能力（`src/dg_education/lineage.py`）。notebook 不直连 GMS/OpenSearch，经 `dg_education.lineage` 离线读 recipe 图，经 `subprocess` 调只读脚本 `query_lineage.py` 获取 DataHub 真图做对比。

## Requirements

### Requirement: module3.ipynb 必须以「痛点故事」cell 开头

`notebook/module3.ipynb` 的第一个 cell MUST 是一个 markdown cell，包含一段两幕对照的"痛点故事"，用于向小白回答"为什么需要数据血缘"。

幕一 MUST 描述**没有血缘**时的痛点场景（如：业务方追问某张订单的煤质数据从哪批样品来，运维要翻 SAP/PI/LIMS 三个系统问三个不同的人，花半天还串不起来）。
幕二 MUST 描述**有血缘**时的顺利场景（在 notebook 或 DataHub UI 中 5 分钟点开血缘图，看到订单→样品→矿井的来源链路）。

两幕对照 MUST 在同一 cell 内呈现。剧本长度 MUST 控制在 200 中文字符以内。

#### Scenario: 痛点故事 cell 存在并位于第一位
- **WHEN** 在 jupyter 中打开 `notebook/module3.ipynb` 并查看第 1 个 cell
- **THEN** 该 cell MUST 是 markdown 类型，且 MUST 包含 "幕一" 与 "幕二" 两个标签

#### Scenario: 故事中包含具体角色与冲突
- **WHEN** 阅读该 cell 的内容
- **THEN** 幕一 MUST 至少包含 1 个具体痛点（如"翻三个系统"或"问三个人"或"串不起来"），幕二 MUST 至少包含 1 个具体正向收益（如"5 分钟"或"点开血缘图"或"来源链路"）

#### Scenario: 故事长度可控
- **WHEN** 统计该 cell 的中文字符数
- **THEN** 总字符数 MUST < 200

### Requirement: module3.ipynb 不得直连 GMS/OpenSearch，联网查询须走只读脚本

`notebook/module3.ipynb` MUST NOT 包含任何直接调用 OpenSearch REST API（如 `29200`）、GMS REST（如 `28080`/`/aspects`）、GMS GraphQL（如 `/api/graphql`）的代码 cell —— 无论用 `requests`、`datahub` SDK 还是其他 HTTP 客户端。notebook 内 MUST NOT 出现 GMS/OpenSearch 的端口号或路径字面量。

需要读取 DataHub 中真实血缘时，notebook MUST 通过 `subprocess` 调用只读脚本 `scripts/query_lineage.py`（输出 JSON），MUST NOT 调用任何写操作脚本（`emit_lineage.py` / `emit_via_rest_emitter.py` / `direct_es_bulk.py`）。写操作由 operator 在 notebook 之外执行。

notebook 的其余代码 MUST 局限于：读取 `lineage_recipe.yaml`、读取 `data/historical/` 与 `data/lakehouse/` 下的 Parquet/Delta、用 pandas/matplotlib/networkx 做离线分析与可视化。

#### Scenario: 全文搜索不应命中 ES/GMS 端点
- **WHEN** 在 `notebook/module3.ipynb` 全文搜索 `29200` 或 `/api/graphql` 或 `28080` 或 `_bulk` 或 `_search` 或 `/aspects`
- **THEN** MUST 0 命中

#### Scenario: 不得直连服务（含 SDK）
- **WHEN** 在 `notebook/module3.ipynb` 全文搜索 `requests` 或 `DatahubRestEmitter` 或 `GraphQLClient` 或 `from datahub`
- **THEN** MUST 0 命中

#### Scenario: 不得在代码 cell 中调用写操作脚本
- **WHEN** 提取 `notebook/module3.ipynb` 中所有 `cell_type=code` 的 cell 源码，搜索 `emit_lineage.py` 或 `emit_via_rest_emitter.py` 或 `direct_es_bulk.py`
- **THEN** MUST 0 命中（markdown cell 中作为 operator 操作说明的文字提及允许，与 module1.ipynb 在 prose 中提及 `direct_es_bulk.py` 的既有惯例一致）

#### Scenario: 联网查询仅经 query_lineage.py
- **WHEN** 在 `notebook/module3.ipynb` 全文搜索 `subprocess`
- **THEN** 所有命中 MUST 仅指向 `scripts/query_lineage.py`，MUST NOT 指向其他脚本

### Requirement: module3.ipynb 通过 dg_education.lineage 离线读取血缘图，并可与 DataHub 真图对比

`notebook/module3.ipynb` 中基于 recipe 的血缘图操作 MUST 通过 `dg_education.lineage` 子模块（`load_lineage_graph` / `upstream` / `downstream` / `blast_radius` / `render_ascii`）完成，数据源为 `lineage_recipe.yaml`。MUST NOT 在 notebook 内手写 GMS 查询。

当需要展示 DataHub 中真实写入的血缘时，notebook MUST 通过 `subprocess` 调用 `scripts/query_lineage.py` 获取 JSON 结果再离线渲染，并至少在 1 个 cell 中将「recipe 自建图」与「DataHub 真图」做对比（确认二者边一致）。

#### Scenario: 使用 lineage 子模块
- **WHEN** 在 `notebook/module3.ipynb` 全文搜索 `load_lineage_graph` 或 `from dg_education.lineage` 或 `dg_education.lineage`
- **THEN** MUST 至少 1 次命中

#### Scenario: 调用 query_lineage.py 获取真图
- **WHEN** 在 `notebook/module3.ipynb` 全文搜索 `query_lineage.py`
- **THEN** MUST 至少 1 次命中（经 subprocess 调用）

### Requirement: module3.ipynb 必须演示上下游双向追溯

`notebook/module3.ipynb` MUST 在「步骤 2」中分别演示：
1. **上游追溯（追根溯源）**：从 `lims.samples` 节点出发，沿血缘图向上找到其上游 `sap_erp.vbak`/`sap_erp.vbap`
2. **下游追溯（影响评估）**：从 `pi_system.tags` 或 `lims.samples` 出发，向下找到 `dwd.*` 或 `dwa_*` 下游

每个方向 MUST 配 1 段「业务影响」白话翻译（参考 module1/2 风格），说明追溯结果在业务上的含义。

#### Scenario: 上游追溯
- **WHEN** 检查 module3.ipynb 步骤 2
- **THEN** MUST 调用 `upstream` 或等价遍历从 `lims.samples` 取得上游，并展示 `sap_erp.vbak`

#### Scenario: 下游追溯
- **WHEN** 检查 module3.ipynb 步骤 2
- **THEN** MUST 调用 `downstream` 或等价遍历取得下游节点

### Requirement: module3.ipynb 必须诚实声明跨系统全链为待解数据孤岛

`notebook/module3.ipynb` MUST 在步骤 3 或总结中明确说明：当前血缘图只覆盖 8 条边，PI→LIMS（CHARG）→SAP→KNA1→OA 的跨系统产销全链**尚未建立**，原因是源系统间无字面共享关联键（数据孤岛），属 Phase 2 / 模块七（主数据标准化）范围。MUST NOT 声称已实现全链追溯。

#### Scenario: 包含诚实声明
- **WHEN** 在 `notebook/module3.ipynb` 全文搜索「数据孤岛」或「Phase 2」或「主数据」或「CHARG」或「全链」
- **THEN** MUST 至少 1 次命中

#### Scenario: 不得声称已完成全链
- **WHEN** 阅读步骤 3 与总结
- **THEN** MUST NOT 出现「全链路已实现」「产销全链已完成」等断言

### Requirement: module3.ipynb 末尾必须引用 module1/module2 notebook

`notebook/module3.ipynb` 的最后 1-3 个 cell 之一 MUST 包含 markdown 引用 `notebook/module1.ipynb` 与 `notebook/module2.ipynb`，让小白知道模块三与前置模块的关系（模块一看资产 → 模块二找问题 → 模块三追血缘）。

#### Scenario: 末尾包含前置模块引用
- **WHEN** 打开 `notebook/module3.ipynb` 查看最后一个 cell 或最末几 cell 之一
- **THEN** MUST 同时包含 `module1.ipynb` 与 `module2.ipynb` 的引用
