# nl2sql-context-builder Specification

## Purpose

从 DataHub GMS REST API **真实查询**血缘（表级 + 列级 fineGrainedLineages）、业务术语（glossaryTerms）、字段 schema（从 Parquet 真实读取），结构化为 LLM 可消费的 context JSON。**严禁使用 `lineage_recipe.yaml` 作为 fallback**（那是模拟的声明式配置，不是 GMS 真实图）。

## Requirements

### Requirement: 从 DataHub GMS 真实拉取血缘上下文

`src/dg_nl2sql/context_builder.py` SHALL 通过 DataHub GMS REST API `GET /aspects/{urn}?aspect=upstreamLineage&version=0` 真实查询表级 + 列级血缘（`fineGrainedLineages`），`GET /aspects/{urn}?aspect=glossaryTerms&version=0` 查询业务术语。schema 因 GMS `schemaMetadata` 为空，从 Parquet 文件用 `pyarrow` 真实读取。context JSON MUST 包含 `tables`、`lineage_edges`、`glossary`、`source` 四个顶层字段。

#### Scenario: GMS 可用时真实查询

- **WHEN** GMS 健康（`is_alive()` 返回 True）
- **THEN** context_builder 通过 REST API 拉取真实血缘 + 术语，schema 从 Parquet 读取，返回 context JSON（`source: "gms"`）

#### Scenario: GMS 不可用时报错退出

- **WHEN** GMS 宕机（`is_alive()` 返回 False）
- **THEN** context_builder MUST 抛出 `RuntimeError`，**严禁 fallback 到 `lineage_recipe.yaml`**（那是模拟值，非 GMS 真实图）

### Requirement: 上下文相关性裁剪

系统 SHALL 根据问题关键词 + 血缘邻接表筛选 top-N 相关表（默认 N=5），包含 1-2 跳血缘邻居，控制 Prompt token 总量在合理范围。

#### Scenario: 问题相关性筛选

- **WHEN** 问题包含"煤质"/"灰分"关键词
- **THEN** context_builder 返回 `dwa_coal_quality` + `lims.samples` + `dwd.samples`（1-2 跳血缘邻居），MUST NOT 返回无关表如 `oa.meeting`

#### Scenario: 无匹配时返回全量

- **WHEN** 问题关键词无匹配任何字段/术语
- **THEN** context_builder 返回全部 DWA 表 schema（作为默认候选），MUST 在 JSON 中标记 `relevance: "low"`
