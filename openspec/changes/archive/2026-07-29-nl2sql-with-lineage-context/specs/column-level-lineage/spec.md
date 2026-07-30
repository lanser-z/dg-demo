## ADDED Requirements

### Requirement: 列级血缘配置格式

`lineage_recipe.yaml` SHALL 支持在每条 lineage relationship 中添加可选的 `columnMappings` 字段，声明 downstream 列与 upstream 列的映射。格式为列表，每项含 `downstream_column`、`upstream_column`、`transformation`（可选，描述转换逻辑如"SUM"/"AVG"/"直接映射"）。

#### Scenario: DWA 字段溯源配置

- **WHEN** 检查 `lineage_recipe.yaml` 中 `dwa_coal_quality` 的 relationship
- **THEN** MUST 含 `columnMappings`，其中 `avg_ash_content` 映射自 `lims.samples.AD`，`transformation: "AVG"`

#### Scenario: 列级映射为可选字段

- **WHEN** 某条 relationship 未声明 `columnMappings`
- **THEN** `emit_lineage.py` MUST 跳过列级写入，仅写表级 `upstreamLineage`，不报错

### Requirement: 列级血缘写入 GMS

`scripts/emit_lineage.py` SHALL 在表级 `upstreamLineage` 写入基础上，对声明了 `columnMappings` 的 relationship 追加写入 `upstreamColumnLineage` aspect（或 `schemaMetadata` 的 fieldRef）。写入 MUST 使用 `DatahubRestEmitter` 官方 SDK，MUST NOT 使用裸 `requests.post`。

#### Scenario: GMS 收到列级 aspect

- **WHEN** 执行 `uv run python scripts/emit_lineage.py` 且 recipe 含 columnMappings
- **THEN** GMS `/aspects` 接口 MUST 收到 `upstreamColumnLineage` aspect 写入

#### Scenario: 不破坏表级血缘

- **WHEN** 执行 `uv run python scripts/emit_lineage.py`
- **THEN** 原有 8 条表级 `upstreamLineage` 边 MUST 继续正常写入，不受列级扩展影响
