## 1. 字段业务词典补齐

- [x] 1.1 创建 `data/glossary_terms.yaml`，为 12 张表核心字段补中文别名 + 业务术语映射（煤种: 精煤/原煤/中煤/矸石/洗煤 -> SAMPLE_TYPE；矿井: 鄂尔多斯一号矿 -> M001 等；订单类型等）
- [x] 1.2 创建 `scripts/emit_glossary.py`，读取 YAML 并通过 GMS REST API 写入 `glossaryTerms` aspect
- [x] 1.3 验证：执行 `uv run python scripts/emit_glossary.py` 退出码 0；GMS 可查到 glossaryTerms aspect

## 2. 关键路径列级血缘

- [x] 2.1 扩展 `lineage_recipe.yaml`，为 DWA←DWD/ODS 的 3 条边添加 `columnMappings`（dwa_sales_daily / dwa_tag_alarm / dwa_coal_quality 的字段溯源映射）
- [x] 2.2 修改 `scripts/emit_lineage.py`，支持读取 `columnMappings` 并写入 GMS `upstreamColumnLineage` aspect（使用 `DatahubRestEmitter` SDK，不裸调 requests.post）
- [x] 2.3 验证：执行 `uv run python scripts/emit_lineage.py` 退出码 0，原有 8 条表级边不受影响，GMS 收到列级 aspect

## 3. NL2SQL 上下文构建器

- [x] 3.1 创建 `src/dg_nl2sql/` 模块（`__init__.py`）
- [x] 3.2 实现 `src/dg_nl2sql/context_builder.py`：从 GMS GraphQL 拉取血缘 + schema + glossary，结构化为 context JSON（含 `tables`/`lineage_edges`/`glossary` 三字段）
- [x] 3.3 实现 GMS 不可用时直接报错退出（**不 fallback 到 lineage_recipe.yaml**——那是模拟值，非 GMS 真实图），schema 从 Parquet 真实读取
- [x] 3.4 实现相关性裁剪：根据问题关键词 + 血缘邻接表筛选 top-5 相关表（1-2 跳邻居）
- [x] 3.5 验证：context_builder 返回合法 JSON，含三字段；GMS 宕机时 fallback 正常

## 4. NL2SQL 引擎实现

- [x] 4.1 实现 `src/dg_nl2sql/llm_client.py`：OpenAI 兼容协议调用 LLM（`requests` 库，配置 `api_key`/`api_url`/`model`，超时 30s）
- [x] 4.2 实现 `src/dg_nl2sql/engine.py`：ContextBuilder + LLMClient + DuckDB 执行 + SQL 修正（最多 1 次）+ 血缘解释
- [x] 4.3 实现表名 -> 文件路径映射（如 `dwa_coal_quality` -> `read_parquet('data/lakehouse/dwa/coal_quality/dwa_coal_quality/*.parquet')`）
- [x] 4.4 实现只读安全校验（拒绝 INSERT/UPDATE/DELETE/DROP/CREATE 等写操作，只允许 SELECT）
- [x] 4.5 创建 `scripts/nl2sql_cli.py` 命令行入口，支持 `uv run python scripts/nl2sql_cli.py "问题"`
- [x] 4.6 验证：单条问题端到端跑通，返回 SQL + 结果 + 血缘解释

## 5. 测试验证

- [x] 5.1 创建 `scripts/nl2sql_demo.py`，包含 6-8 个测试问题（单表聚合 / 多表 JOIN / 跨系统歧义 / 术语消解 / 时间筛选 / Top-N 排序）
- [x] 5.2 执行批量测试，输出每题 SQL / 结果前 5 行 / 血缘解释 / PASS-FAIL + 汇总（N passed, M failed）
- [x] 5.3 验证：至少 5/8 题通过（PASS），跨系统歧义题正确识别并提示"无可执行 JOIN"
