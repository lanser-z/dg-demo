## Why

Phase 1 手工直写 OpenSearch 模式无法支撑长期运营：新增 Parquet 文件需人工触发注册，元数据更新滞后，ES 与 GMS 数据短暂不一致，5 系统 × N 张表的规模下人工模式不可扩展。Phase 2 需要 Kafka 事件流驱动的自动化同步能力，作为模块九（自动血缘采集）和模块十（定时质量监控）的基础设施。

## What Changes

- 新增 `datahub-actions` Kafka Consumer 配置，消费 `MetadataChangeLog_Versioned_v1` Topic，将变更事件同步至 GMS MySQL 和 OpenSearch
- 新增 Delta-Lake ingestion recipe：`delta-lake` source → `datahub-rest` sink，实现 Parquet 文件落地后自动被发现和注册
- 新增 GMS REST API 直连模式示例，作为开发/测试环境或无 Kafka 集群场景的备选路径
- 引用官方 `datahub docker quickstart` CLI（compose 文件：`docker/quickstart/docker-compose.quickstart-profile.yml`），提供本地演示环境
- 新增 `notebook/module8.ipynb` 教学 notebook，展示 Phase 2 架构和痛点故事
- **BREAKING**：Phase 2 稳定后，现有 `scripts/direct_es_bulk.py` 手工模式应标记为 deprecated（不影响当前 Module7 环境）

## Capabilities

### New Capabilities

- `datahub-actions-kafka-sync`: datahub-actions Kafka Consumer 配置，消费 `MetadataChangeLog_Versioned_v1`，将变更事件同步至 GMS MySQL 和 OpenSearch，实现分钟级自动同步
- `delta-lake-auto-discovery`: Delta-Lake ingestion recipe 配置，`delta-lake` source + `datahub-rest` sink，新增 Parquet 文件无需人工注册
- `gms-rest-api-mode`: GMS REST API 直连写入示例，适用于开发/测试环境或无 Kafka 集群场景
- `module8-teaching-notebook`: Phase 2 架构演示 notebook，包含痛点故事、架构解析、Kafka 事件流配置和 REST API 示例

### Modified Capabilities

（无）

## Impact

| 影响范围 | 说明 |
|---------|------|
| 代码 | 新增 `datahub-actions.yml`、`delta-lake-ingestion.yaml` 配置文件；`notebook/module8.ipynb` 教学 notebook |
| 依赖 | datahub-actions 服务（`acryl-datahub/actions`）；Kafka 集群（`MetadataChangeLog_Versioned_v1` Topic）；Delta-Lake Python 库 |
| 文档 | `docs/Module8.md` 中 Phase 2 待办项将变为已完成；架构图需更新 topic 名称（`MetadataChangeLog_v4` → `MetadataChangeLog_Versioned_v1`） |
| 现有系统 | `scripts/direct_es_bulk.py` Phase 2 稳定后应 deprecated；`scripts/emit_browsepaths.py` 可保留作为 fallback |
| 回滚计划 | 若 datahub-actions 配置失败，可回退至 Phase 1 手工模式；Delta-Lake ingestion 失败时保留人工注册脚本 |
