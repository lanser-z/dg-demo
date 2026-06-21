# data-lineage-ingestion Specification

## Purpose

通过 DataHub GMS 官方 SDK 写入 `upstreamLineage` 血缘 aspect 的能力，覆盖血缘 recipe 配置、写入脚本（`emit_lineage.py`）、真验证脚本（`verify_lineage.py`）与只读查询脚本（`query_lineage.py`）。教学 notebook 不直连 GMS，经 `query_lineage.py` 获取 DataHub 真图。

## Requirements

### Requirement: 血缘通过 GMS 官方 SDK 模式写入 upstreamLineage aspect

`scripts/emit_lineage.py` MUST 使用 `datahub.emitter.rest_emitter.DatahubRestEmitter` + `datahub.emitter.mcp.MetadataChangeProposalWrapper` + `datahub.metadata.schema_classes.UpstreamLineageClass`/`UpstreamClass` 写入血缘，MUST NOT 使用裸 `requests.post` 手写 GMS 调用。

每个 `UpstreamClass` 的 URN 字段 MUST 是 `dataset`（非 `upstreamEntity`），`type` MUST 取 `COPY`/`TRANSFORMED`/`VIEW` 之一。`auditStamp` 可缺省（SDK 填默认）。

#### Scenario: 不含 upstreamEntity 错误字段名
- **WHEN** 在 `scripts/emit_lineage.py` 中搜索 `upstreamEntity=` 赋值（即把 URN 错误地传给 `upstreamEntity` 参数）
- **THEN** MUST 0 命中（docstring 中以「非 upstreamEntity」方式说明正确字段名的文字提及允许）

#### Scenario: 不含裸 requests 手写 GMS 调用
- **WHEN** 在 `scripts/emit_lineage.py` 全文搜索 `requests.post` 或 `import requests`
- **THEN** MUST 0 命中

#### Scenario: 使用官方 SDK
- **WHEN** 在 `scripts/emit_lineage.py` 全文搜索 `DatahubRestEmitter` 与 `MetadataChangeProposalWrapper` 与 `UpstreamLineageClass`
- **THEN** 三者 MUST 均至少 1 次命中

### Requirement: emit_lineage.py 不得残留 Neo4j 代码

`scripts/emit_lineage.py` MUST NOT 包含 `import neo4j`、`from neo4j`、`write_lineage_to_neo4j` 函数、或任何 Neo4j fallback 分支（与 `docs/Module1.md`「已移除 Neo4j」声明一致）。docstring/注释中描述「移除 Neo4j」的文字说明允许。

#### Scenario: 无 neo4j 导入与函数
- **WHEN** 在 `scripts/emit_lineage.py` 全文搜索 `import neo4j` 或 `from neo4j` 或 `write_lineage_to_neo4j`
- **THEN** MUST 0 命中（docstring 中描述移除历史的文字提及允许）

### Requirement: 血缘写入后必须有真验证脚本断言 aspect 非空

`scripts/verify_lineage.py` MUST 对 `lineage_recipe.yaml` 中每条有 upstream 的边，调用 `GET /aspects/<urlencoded_urn>?aspect=upstreamLineage` 查询 GMS，并断言返回的 `upstreams` 数组非空且包含预期的上游 dataset URN。任一断言失败 MUST 以非零退出码退出。

#### Scenario: 验证脚本存在并可执行
- **WHEN** 执行 `uv run python scripts/verify_lineage.py`
- **THEN** 对每条 recipe 边输出断言结果，全部通过时退出码 0，任一失败时退出码非 0

#### Scenario: 查询 GMS aspect
- **WHEN** 检查 `scripts/verify_lineage.py` 源码
- **THEN** MUST 包含对 `http://localhost:28080/aspects/` 的 GET 请求与 `aspect=upstreamLineage` 参数

### Requirement: 提供只读查询脚本供 notebook 获取 DataHub 真图

`scripts/query_lineage.py` MUST 是一个只读脚本（MUST NOT 写入任何 GMS/OpenSearch 数据），查询 DataHub 中已写入的血缘：对 `lineage_recipe.yaml` 中每条有 upstream 的边，`GET /aspects/<urlencoded_urn>?aspect=upstreamLineage` 取真实上游，输出 JSON 到 stdout（结构含 `{dataset, upstreams: [...]}` 列表）。notebook 通过 `subprocess` 调用它获取「DataHub 真图」。

#### Scenario: 脚本只读
- **WHEN** 检查 `scripts/query_lineage.py` 源码
- **THEN** MUST NOT 包含 `POST`、`UPSERT`、`emit`、`write` 等写操作；MUST 仅包含对 `GET /aspects/` 的只读查询

#### Scenario: 输出 JSON
- **WHEN** 执行 `uv run python scripts/query_lineage.py`
- **THEN** stdout MUST 输出合法 JSON，含每条边的 dataset 与其 upstreams 列表

### Requirement: 血缘边总数与语义

`lineage_recipe.yaml` 中有 upstream 的边 MUST 共 8 条：
- 2 条业务血缘：`sap_erp.vbak → lims.samples`、`sap_erp.vbap → lims.samples`
- 3 条加工血缘（ODS→DWD）：`sap_erp.vbak → dwd.vbak`、`pi_system.tags → dwd.tags`、`lims.samples → dwd.samples`
- 3 条加工血缘（DWD/ODS→DWA）：`dwd.vbak → dwa_sales_daily`、`pi_system.tags → dwa_tag_alarm`、`lims.samples → dwa_coal_quality`

#### Scenario: 8 条边
- **WHEN** 执行 `uv run python -c "import yaml; r=yaml.safe_load(open('lineage_recipe.yaml')); print(sum(len(x['upstream']) for x in r['lineage_relationships'] if x.get('upstream')))"`
- **THEN** 输出 MUST 为 8（一条 relationship 可含多个 upstream，每对 upstream→downstream 计 1 条边；`lims.samples` 含 2 个 upstream 即 2 条边）

#### Scenario: DWA 三张表有上游边
- **WHEN** 检查 `lineage_recipe.yaml`
- **THEN** MUST 包含 downstream 为 `dwa_sales_daily`、`dwa_tag_alarm`、`dwa_coal_quality` 的各 1 条边

### Requirement: 业务血缘边的 join_key 不得使用不存在的列

`lineage_recipe.yaml` 中 `sap_erp.vbak/vbap → lims.samples` 两条业务血缘边 MUST NOT 声明 `join_key: KUNNR`（因 `lims.samples` 表无 KUNNR 列、`sap_erp.vbak` 无 MINE_CODE 列，两表无字面共享列）。该边的跨系统关系 MUST 在 `description` 字段中如实说明为「声明式业务关系，非可执行 JOIN」。

#### Scenario: 不含错误的 KUNNR join_key
- **WHEN** 在 `lineage_recipe.yaml` 中检查 `vbak`/`vbap` → `lims.samples` 两条边
- **THEN** MUST NOT 出现 `join_key: KUNNR`

#### Scenario: description 说明为声明式关系
- **WHEN** 阅读这两条边的 `description`
- **THEN** MUST 包含「声明式」或「非可执行」或「无字面共享列」之一
