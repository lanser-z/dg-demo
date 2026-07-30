## Why

煤炭数据治理 Demo 已完成 DataHub 血缘录入（8 条边）、DWA 宽表构建、质量检测，但数据消费仍停留在"写 SQL 查 DWA"的工程师模式。业务人员（销售部/安全部/煤质中心）无法自助问数。DataHub 血缘图蕴含的表关系、JOIN 键、加工链路等元数据，若结构化为 LLM 上下文，可显著提升 NL2SQL 的表选择准确率和 JOIN 路径推断能力，让血缘图从"可视化资产"升级为"AI 可消费的语义图谱"。

## What Changes

1. **新增字段业务词典**：为 12 张表的字段补中文别名 + 业务术语映射（如"精煤"=`SAMPLE_TYPE:'精煤'`），写入 DataHub `glossaryTerms` aspect
2. **扩展列级血缘**：在关键路径（DWA←DWD←ODS）补充字段级映射，扩展 `lineage_recipe.yaml` + `emit_lineage.py` 支持 `columnMappings`
3. **新增 NL2SQL 上下文构建器**：从 DataHub GMS GraphQL 拉取血缘图 + schema + 词典，结构化为 LLM 可消费的 context JSON
4. **新增 NL2SQL 引擎**：OpenAI 兼容协议调用 LLM（MiniMax-M2.7），Prompt 注入血缘上下文，DuckDB 执行 SQL 查 Delta Lake，返回结果 + 血缘解释
5. **新增测试验证**：6-8 个覆盖单表/JOIN/跨系统/聚合/歧义的测试问题，端到端跑通

## Capabilities

### New Capabilities

- `field-business-glossary`: 字段级业务词典（中文别名 + 术语->字段值映射），写入 DataHub glossaryTerms，为 NL2SQL 提供术语消解能力
- `column-level-lineage`: 关键路径列级血缘（DWA←DWD←ODS 字段映射），扩展血缘 recipe 支持 columnMappings
- `nl2sql-context-builder`: 从 DataHub GMS 拉取血缘图+schema+词典，结构化为 LLM 上下文 JSON
- `nl2sql-engine`: NL2SQL 引擎（LLM 客户端 + Prompt 工程 + DuckDB 执行 + 血缘解释）
- `nl2sql-test-suite`: 测试问题集 + 端到端验证脚本

### Modified Capabilities

- `data-lineage-ingestion`: 扩展支持列级血缘写入（`upstreamColumnLineage` aspect），在表级 `upstreamLineage` 基础上追加字段级映射

## Impact

**受影响模块**：
- 新增模块：`src/dg_nl2sql/`（context_builder + engine + llm_client）
- 新增脚本：`scripts/emit_glossary.py`、`scripts/nl2sql_cli.py`、`scripts/nl2sql_demo.py`
- 修改脚本：`scripts/emit_lineage.py`（支持列级血缘写入）
- 修改配置：`lineage_recipe.yaml`（追加 `columnMappings` 字段）
- 修改依赖：`pyproject.toml`（新增 `openai` 或 `httpx`；`duckdb` 已在用但需显式声明）

**受影响系统**：
- DataHub GMS：新增 `glossaryTerms` + `upstreamColumnLineage` aspect（只增不改，不影响已有功能）
- Delta Lake：只读查询（DuckDB SELECT），无写入

**回滚计划**：
- 新增模块独立，删除 `src/dg_nl2sql/` + `scripts/nl2sql_*.py` + `scripts/emit_glossary.py` 即可完全回滚
- DataHub 新增 aspect 不影响已有功能；如需清理，通过 GMS REST API 按 URN 删除对应 aspect
- `lineage_recipe.yaml` 的 `columnMappings` 为可选字段，回滚时删除该字段即可，表级血缘不受影响
- `pyproject.toml` 依赖回滚：移除新增条目后 `uv sync` 即可
