## ADDED Requirements

### Requirement: 字段中文别名录入

系统 SHALL 通过 `scripts/emit_glossary.py` 为 12 张表的核心字段提供中文别名，写入 DataHub `glossaryTerms` / `datasetProperties` aspect。词典数据 MUST 维护在 `data/glossary_terms.yaml` 中，字段包括 `platform`、`table`、`column`、`cn_name`、`description`、`business_terms`（业务术语列表）。

#### Scenario: 词典文件存在且格式合法

- **WHEN** 执行 `uv run python -c "import yaml; d=yaml.safe_load(open('data/glossary_terms.yaml')); assert len(d['glossary'])>0"`
- **THEN** MUST 成功，且每条记录含 `platform`/`table`/`column`/`cn_name` 字段

#### Scenario: 写入 DataHub glossaryTerms

- **WHEN** 执行 `uv run python scripts/emit_glossary.py`
- **THEN** MUST 通过 GMS REST API 写入 `glossaryTerms` aspect，退出码 0

### Requirement: 业务术语到字段值映射

系统 SHALL 在 `data/glossary_terms.yaml` 中维护业务术语到字段值的映射（如煤种术语：精煤/原煤/中煤/矸石/洗煤 -> `SAMPLE_TYPE` 字段值），供 NL2SQL 上下文构建器消费。

#### Scenario: 煤种术语消解

- **WHEN** NL2SQL 上下文构建器收到包含"精煤"的问题
- **THEN** 从 glossary_terms.yaml 查得 `SAMPLE_TYPE` 字段 + 对应值"精煤"，注入 LLM context

#### Scenario: 矿井术语消解

- **WHEN** 问题包含"鄂尔多斯一号矿"
- **THEN** 上下文构建器映射到 `MINE_CODE='M001'`，注入 context
