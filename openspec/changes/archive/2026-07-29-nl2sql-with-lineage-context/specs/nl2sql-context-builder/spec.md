## ADDED Requirements

### Requirement: 从 DataHub GMS 拉取血缘上下文

`src/dg_nl2sql/context_builder.py` SHALL 通过 DataHub GMS GraphQL API 拉取表级 + 列级血缘、dataset schema、glossaryTerms，结构化为 context JSON。context JSON MUST 包含 `tables`（表列表含 schema）、`lineage_edges`（血缘边含 join_key/columnMappings）、`glossary`（业务术语映射）三个顶层字段。

#### Scenario: GMS 可用时拉取

- **WHEN** GMS 健康（`is_alive()` 返回 True）
- **THEN** context_builder 通过 GraphQL 拉取元数据，返回结构化 context JSON

#### Scenario: GMS 不可用时 fallback

- **WHEN** GMS 宕机（`is_alive()` 返回 False）
- **THEN** context_builder fallback 到本地 `lineage_recipe.yaml` + `pyarrow` 读 Parquet schema，返回 context JSON，MUST 在 JSON 中标记 `source: "fallback"`

### Requirement: 上下文相关性裁剪

系统 SHALL 根据问题关键词 + 血缘邻接表筛选 top-N 相关表（默认 N=5），包含 1-2 跳血缘邻居，控制 Prompt token 总量在合理范围。

#### Scenario: 问题相关性筛选

- **WHEN** 问题包含"煤质"/"灰分"关键词
- **THEN** context_builder 返回 `dwa_coal_quality` + `lims.samples` + `dwd.samples`（1-2 跳血缘邻居），MUST NOT 返回无关表如 `oa.meeting`

#### Scenario: 无匹配时返回全量

- **WHEN** 问题关键词无匹配任何字段/术语
- **THEN** context_builder 返回全部 DWA 表 schema（作为默认候选），MUST 在 JSON 中标记 `relevance: "low"`
