## Why

模块 3 演示版血缘仅维护 5 条手工边（`lineage_recipe.yaml`），随 5 系统 × N 主题域规模扩张不可扩展。Phase 2 需要让 ETL 任务在跑完后**自动**向 DataHub 上报 lineage，业务代码改动 ≤ 5 行；新增 DWD/DWA 表零配置即出现在血缘图。同时保留手工 `lineage_recipe.yaml` 作为跨系统业务 JOIN 的兜底通道。

## What Changes

- **新增 `LineageEmitter` 上下文管理器**：ETL 入口插入 3 行（`with LineageEmitter("dwd_vbak") as e: e.from_sql("..."); e.to_dataset("dwd.sap_erp.vbak")`）
- **SQL 解析器**：用 `sqlglot` 从 `FROM` / `JOIN` 子句推导 inputs，无需求用户声明
- **OpenLineage 事件格式**：emit `START` / `COMPLETE` 事件到 Kafka topic `openlineage.events`
- **DataHub actions 消费**：复用 module8 的 `datahub-actions` 服务，加一个 `openlineage_kafka_sync` 动作
- **GMS 兼容验证**：DataHub v1.6.0 `upstreamLineage` aspect ↔ OpenLineage 1-1 映射测试，失败时降级到自定义 emitter
- **保留** `scripts/emit_lineage.py` + `lineage_recipe.yaml`（业务跨系统 JOIN 走此路径）
- **新增** `notebook/module9.ipynb` 演示 1 条手工边 + 1 条自动边视觉对比
- **BREAKING** 无（纯增量）

## Capabilities

### New Capabilities
- `auto-lineage-collection`: ETL 任务从 SQL 解析自动 emit OpenLineage 事件，DataHub actions 消费后写入 GMS `upstreamLineage` aspect

### Modified Capabilities
- `data-lineage-ingestion`: 增加 "支持 auto-emitted 边与 manual 边共存" 的需求；`lineage_recipe.yaml` 明确为兜底通道而非唯一来源

## Impact

- **代码**：`scripts/ingest_to_deltalake.py`、`scripts/build_dwa_models.py`、`scripts/build_dimension_tables.py` 各插入 `LineageEmitter` 上下文（≤ 5 行/脚本）
- **新增脚本**：`src/dg_platform/lineage_emitter.py`（核心 emitter）、`scripts/verify_auto_lineage.py`（验证）
- **配置**：`datahub-actions.yml` 增加 `openlineage_kafka_sync` 动作
- **依赖**：`pyproject.toml` 新增 `openlineage-python>=1.0`、`sqlglot>=20.0`（无 Spark/Flink 依赖）
- **Kafka**：新建 topic `openlineage.events`（replication=1, partitions=3）
- **DataHub**：复用现有 v1.6.0 stack，无版本升级
- **教学**：新增 `notebook/module9.ipynb`；更新 `notebook/module8.ipynb` 引用新动作
- **回滚**：删除 `openlineage.events` topic + 移除 ETL 入口的 `LineageEmitter` 上下文（≤ 1 小时）；手工 `lineage_recipe.yaml` 通道不受影响
