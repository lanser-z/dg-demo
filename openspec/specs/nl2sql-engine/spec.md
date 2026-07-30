# nl2sql-engine Specification

## Purpose

NL2SQL 智能问数引擎，通过 OpenAI 兼容协议调用 LLM 生成 SQL，DuckDB 执行查询 Delta Lake / Parquet 文件，返回结果 + 血缘解释。

## Requirements

### Requirement: LLM 客户端 OpenAI 兼容协议

`src/dg_nl2sql/llm_client.py` SHALL 通过 OpenAI 兼容协议调用 LLM（`POST {api_url}/chat/completions`），支持配置 `api_key`、`api_url`、`model`。MUST 使用 `requests` 库（项目已有依赖），MUST NOT 引入 `openai` SDK 新依赖。

#### Scenario: 生成 SQL

- **WHEN** engine 调用 `llm_client.chat(system_prompt, user_message)`
- **THEN** 返回 LLM 生成的 SQL 字符串

#### Scenario: API 错误处理

- **WHEN** LLM API 返回非 200 状态码或超时（默认 30s）
- **THEN** llm_client 抛出异常，engine 捕获并返回错误信息给用户

### Requirement: NL2SQL 引擎端到端流程

`src/dg_nl2sql/engine.py` SHALL 实现"问题 -> 上下文 -> LLM 生成 SQL -> DuckDB 执行 -> 结果 + 血缘解释"完整流程。

#### Scenario: 成功生成并执行 SQL

- **WHEN** 用户输入"各矿井精煤灰分排名"
- **THEN** engine 返回 SQL 字符串 + DuckDB 查询结果 + 血缘解释（数据来自 `dwa_coal_quality <- lims.samples`）

#### Scenario: SQL 语法错误自动修正

- **WHEN** LLM 生成的 SQL 在 DuckDB 执行报错
- **THEN** engine 带错误信息再调 LLM 修正（最多 1 次），用修正后 SQL 重试执行

#### Scenario: 修正后仍失败

- **WHEN** 修正后 SQL 仍执行失败
- **THEN** engine 返回错误信息 + 原始 SQL + 修正 SQL，MUST NOT 无限重试

### Requirement: DuckDB SQL 执行器

`src/dg_nl2sql/engine.py` SHALL 使用 DuckDB 执行生成的 SQL，查询 Delta Lake / Parquet 文件。SQL 中的表名 MUST 通过表名映射（如 `dwa_coal_quality` -> `read_parquet('data/lakehouse/dwa/coal_quality/dwa_coal_quality/*.parquet')`）定位到实际文件路径。

#### Scenario: 查询 DWA 表

- **WHEN** SQL 包含 `FROM dwa_coal_quality`
- **THEN** DuckDB 通过 `read_parquet` 读取对应 Parquet 文件并返回结果

#### Scenario: 只读安全

- **WHEN** LLM 生成的 SQL 包含 `INSERT`/`UPDATE`/`DELETE`/`DROP`/`CREATE` 写操作
- **THEN** engine MUST 拒绝执行并返回错误（只允许 `SELECT` 语句）

### Requirement: 血缘解释生成

engine SHALL 在返回结果时附带血缘解释，说明数据来源表和加工链路。解释信息 MUST 从 context 的 `lineage_edges` 中提取。

#### Scenario: 结果附带来源

- **WHEN** 查询 `dwa_coal_quality` 成功
- **THEN** 返回结果中含 `lineage_explanation` 字段，值为"数据来自: dwa_coal_quality <- lims.samples (加工血缘: AVG聚合)"
