# auto-lineage-collection Specification

## Purpose

ETL 任务从 SQL 解析自动 emit OpenLineage 事件，DataHub actions 服务消费后写入 GMS `upstreamLineage` aspect 的能力。覆盖 LineageEmitter 上下文管理器、SQL 解析器、OpenLineage client、Kafka 事件传输、DataHub actions 消费者、兼容性降级路径与教学 notebook。

## ADDED Requirements

### Requirement: ETL 入口通过 LineageEmitter 上下文管理器上报血缘

ETL 入口脚本（`scripts/ingest_to_deltalake.py`、`scripts/build_dwa_models.py`、`scripts/build_dimension_tables.py`）MUST 在主函数入口使用 `with LineageEmitter("job_name", sql="...") as e:` 上下文管理器，ETL 跑完自动 emit START 与 COMPLETE 事件，业务代码改动 MUST ≤ 5 行/入口。

#### Scenario: 上下文管理器存在并被 ETL 调用
- **WHEN** 检查 `scripts/ingest_to_deltalake.py` / `scripts/build_dwa_models.py` / `scripts/build_dimension_tables.py` 三文件全文搜索 `with LineageEmitter(`
- **THEN** 三个文件 MUST 各至少 1 次命中

#### Scenario: 业务代码改动不超过 5 行
- **WHEN** 统计每个 ETL 入口中 LineageEmitter 相关代码行数（从 `with LineageEmitter(` 到 `e.emit_output(` 闭包）
- **THEN** 每个文件 MUST ≤ 5 行

### Requirement: LineageEmitter 用 sqlglot 从 SQL 解析 inputs

`LineageEmitter` 解析 `sql` 参数时 MUST 用 `sqlglot` 从 `FROM` / `JOIN` 子句推导 `inputs` 列表（dataset URN 形式），解析失败 MUST 降级为 `inputs=[]` 不阻断事件上报。

#### Scenario: sqlglot 库被声明为依赖
- **WHEN** 检查 `pyproject.toml`
- **THEN** MUST 包含 `"sqlglot>=20.0"` 依赖

#### Scenario: 解析 SQL 提取 inputs
- **WHEN** 调用 `LineageEmitter("test", sql="SELECT * FROM sap_erp.vbak JOIN lims.samples ON ...")`
- **THEN** 上下文退出时 emit 的 COMPLETE 事件 MUST 包含 `inputs=["sap_erp.vbak", "lims.samples"]`（URN 形式可后续映射）

#### Scenario: 解析失败降级
- **WHEN** 传入 `sql="INVALID SQL GARBAGE"`，sqlglot 抛 `ParseError`
- **THEN** 上下文 MUST 仍 emit COMPLETE 事件且 `inputs=[]` 不抛异常

### Requirement: OpenLineage 事件 emit 到 Kafka topic openlineage.events

`LineageEmitter` 内部 MUST 用 `openlineage-python` 官方 SDK（`OpenLineageClient` + `LineageEvent`）emit START 与 COMPLETE 事件到 Kafka topic `openlineage.events`，事件 schema MUST 符合 OpenLineage 1.x 规范。

#### Scenario: openlineage-python 依赖
- **WHEN** 检查 `pyproject.toml`
- **THEN** MUST 包含 `"openlineage-python>=1.0"` 依赖

#### Scenario: Kafka topic 配置
- **WHEN** 检查 `LineageEmitter` 源码或环境变量
- **THEN** MUST 包含 Kafka transport 配置，topic 名 MUST 为 `openlineage.events`

#### Scenario: 事件 schema 包含 job + inputs + outputs
- **WHEN** 调用 `e.emit_output("dwd.sap_erp.vbak", df)` 后 emit 的 COMPLETE 事件
- **THEN** MUST 含 `job.name="dwd_vbak"`、`outputs[0].name="dwd.sap_erp.vbak"`、`inputs` 列表与 SQL 解析结果一致

### Requirement: DataHub actions 消费 openlineage.events 写 GMS upstreamLineage aspect

`datahub-actions.yml` MUST 配置 `openlineage_kafka_sync` 动作消费 topic `openlineage.events`，将每条 OpenLineage 事件转换为 GMS `MetadataChangeProposalWrapper` + `UpstreamLineageClass` 写入 GMS。

#### Scenario: actions 配置文件存在
- **WHEN** 检查 `datahub-actions.yml`
- **THEN** MUST 包含 `openlineage_kafka_sync` 动作定义与 Kafka topic `openlineage.events` 订阅

#### Scenario: GMS 兼容性降级
- **WHEN** `datahub-actions` 启动时发现 GMS v1.6.0 `upstreamLineage` aspect 不接受 OpenLineage 标准 facet
- **THEN** MUST 降级为直接 emit `UpstreamLineageClass`（跳过 OpenLineage 转换），日志输出 "openlineage fallback to direct emit"

### Requirement: 新建 DWD/DWA 表 30 秒内出现在 DataHub 血缘图

ETL 任务跑完到对应 dataset 在 DataHub UI Lineage 标签页出现上游/下游边，latency MUST ≤ 30 秒（P95）。

#### Scenario: 端到端延迟验证
- **WHEN** 执行 `uv run python scripts/ingest_to_deltalake.py --layer dwd` 跑完
- **THEN** 在 30 秒内访问 `http://localhost:29002/dataset/...` 能在 Lineage 标签页看到上游 `sap_erp.vbak` 边

#### Scenario: 验证脚本存在
- **WHEN** 检查 `scripts/verify_auto_lineage.py`
- **THEN** MUST 存在且能跑（`uv run python scripts/verify_auto_lineage.py`）输出每条 auto 边的 GMS 验证结果

### Requirement: 兜底通道 lineage_recipe.yaml 继续工作

`lineage_recipe.yaml` 业务跨系统 JOIN 边（如 `sap_erp.vbak → lims.samples` 按 KUNNR 关联）MUST 继续走 `scripts/emit_lineage.py` 手工通道，与 auto 通道并存不冲突。

#### Scenario: 手工通道不受影响
- **WHEN** 执行 `uv run python scripts/emit_lineage.py`
- **THEN** MUST 成功写 8 条原有手工边到 GMS，无 OpenLineage 通道干扰

#### Scenario: 双通道边去重
- **WHEN** 同一对 `dataset + upstream` 同时出现在 `lineage_recipe.yaml` 与 auto-emitted 边中
- **THEN** DataHub UI MUST 仅显示 1 条边（OpenSearch 索引按唯一键去重）

### Requirement: notebook module9.ipynb 演示 auto + manual 双通道

`notebook/module9.ipynb` MUST 演示：1 条手工边（来自 `lineage_recipe.yaml`）+ 1 条自动边（来自 ETL 跑完 emit）并排截图，附 Playwright 抓取 DataHub UI 血缘图作为对比证据。

#### Scenario: notebook 存在
- **WHEN** 检查 `notebook/module9.ipynb`
- **THEN** MUST 存在且可执行（cell 顺序：load recipe → emit 1 手工边 → 跑 ETL 触发 auto 边 → query GMS 双通道 → Playwright 截图）

#### Scenario: Playwright 截图存在
- **WHEN** 执行 notebook 最后一个 cell
- **THEN** MUST 生成 `notebook/step_images/module9_lineage_manual.png` 与 `module9_lineage_auto.png` 两个文件
