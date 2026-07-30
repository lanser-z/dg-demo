## ADDED Requirements

### Requirement: 列级血缘写入 upstreamColumnLineage aspect

`scripts/emit_lineage.py` SHALL 在表级 `upstreamLineage` 写入基础上，对 `lineage_recipe.yaml` 中声明了 `columnMappings` 的 relationship 追加写入 DataHub `upstreamColumnLineage` aspect（或等价的 `schemaMetadata` fieldRef）。列级写入 MUST 使用 `DatahubRestEmitter` 官方 SDK，MUST NOT 使用裸 `requests.post`。

#### Scenario: 列级 aspect 写入

- **WHEN** 执行 `uv run python scripts/emit_lineage.py` 且 recipe 含 columnMappings
- **THEN** GMS MUST 收到 `upstreamColumnLineage` aspect 写入，含 downstream 列与 upstream 列的映射

#### Scenario: 不破坏表级血缘

- **WHEN** 执行 `uv run python scripts/emit_lineage.py`
- **THEN** 原有 8 条表级 `upstreamLineage` 边 MUST 继续正常写入，退出码 0，不受列级扩展影响

#### Scenario: columnMappings 为可选

- **WHEN** 某条 relationship 未声明 `columnMappings`
- **THEN** `emit_lineage.py` MUST 跳过列级写入，仅写表级 `upstreamLineage`，不报错
