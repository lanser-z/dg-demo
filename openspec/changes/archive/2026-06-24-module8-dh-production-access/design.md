## Context

### 背景

当前 Demo 环境采用 Phase 1 手工模式：
- `scripts/direct_es_bulk.py` 直接 Bulk API 写入 OpenSearch，绕过 GMS
- `scripts/emit_browsepaths.py` 人工注册 browse paths
- 问题：新 Parquet 文件需人工触发，元数据滞后，GMS/ES 短暂不一致

Phase 2 目标：Kafka 事件流驱动，GMS 为唯一写入路径，OpenSearch 自动同步。

### 约束

- Demo 环境无真实 Kafka 集群，Phase 2 方案为架构演示（notebook 中展示配置和预期行为）
- 不得修改 `docs/*.md`
- 使用 `uv` 管理 Python 依赖
- datahub-actions 当前消费 topic 为 `MetadataChangeLog_Versioned_v1`（非废弃的 `MetadataChangeLog_v4`）

## Goals / Non-Goals

**Goals:**
- 提供 datahub-actions Kafka Consumer 完整配置示例（`MetadataChangeLog_Versioned_v1`）
- 提供 Delta-Lake ingestion recipe（`delta-lake` source → `datahub-rest` sink）
- 提供 GMS REST API 直连模式 Python 示例（开发/测试 fallback）
- 引用官方 `datahub docker quickstart` 提供本地演示环境
- 编写 `notebook/module8.ipynb` 教学 notebook

**Non-Goals:**
- 不在 Demo 环境实际运行 Kafka 集群（无 docker-compose 环境）
- 不修改现有 Phase 1 脚本（`direct_es_bulk.py`、`emit_browsepaths.py`）
- 不修改 `docs/Module8.md`（CLAUDE.md 约束）

## Decisions

### Decision 1: datahub-actions Kafka Topic 使用 `MetadataChangeLog_Versioned_v1`

**选项 A（采用）**: `MetadataChangeLog_Versioned_v1`
- datahub-actions 当前版本消费此 topic
- 支持 entity 级别的变更事件（`ENTITY_CHANGE`）

**选项 B（放弃）**: `MetadataChangeLog_v4`
- 已被官方标记为 deprecated
- DeepWiki 确认已废弃

### Decision 2: datahub-actions pipeline action 使用 `metadata_change_sync` 而非 `rest`

**选项 A（采用）**: `metadata_change_sync` action
- 官方内置 action，监听 `MetadataChangeLog` 事件并作为 `MetadataChangeProposal` 发送到目标 GMS
- 使用 `DatahubRestEmitter` 发送变更
- 支持 `aspects_to_exclude`、`urn_regex` 等精细过滤

**选项 B（放弃）**: `rest` action
- 历史上存在过，但当前版本官方内置 action 为 `metadata_change_sync`
- DeepWiki 确认 `metadata_change_sync` 是当前推荐方式

### Decision 3: Delta-Lake ingestion 使用 `datahub-rest` sink 而非 `datahub-kafka`

**选项 A（采用）**: `datahub-rest` sink
- 写入 GMS REST API，不依赖 Kafka
- 适合开发/测试环境

**选项 B（放弃）**: `datahub-kafka` sink
- 需要 Kafka 集群，Demo 环境不可用

### Decision 4: 本地演示使用 `datahub docker quickstart` CLI

**选项 A（采用）**: `datahub docker quickstart`
- 官方推荐方式，自动下载 `docker-compose.quickstart-profile.yml`
- 一行命令启动完整栈（GMS + MySQL + Kafka + OpenSearch + datahub-actions）

**选项 B（放弃）**: 手工编写 `datahub-quickstart.yml`
- 维护成本高，版本更新后可能不同步
- 官方已有成熟方案

## Architecture Diagram

### Phase 1 vs Phase 2 数据流对比

```plantuml
skinparam backgroundColor #FEFEFE
skinparam componentStyle rectangle

package "Phase 1（当前）" {
  [scripts/\ndirect_es_bulk.py] as phase1_script
  database "OpenSearch" as es
  database "GMS MySQL" as gms_db

  phase1_script --> es : 直接 Bulk API\n（绕过 GMS）
  note bottom of es : ⚠️ ES 与 MySQL\n短暂不一致
}

package "Phase 2（目标）" {
  [源数据变更] as source
  database "Kafka\nMetadataChangeLog_Versioned_v1" as kafka
  [datahub-actions] as actions
  database "GMS MySQL" as gms_db2
  database "OpenSearch" as es2

  source --> kafka : CDC 事件
  kafka --> actions : 消费事件
  actions --> gms_db2 : REST API\n（唯一写入路径）
  gms_db2 --> es2 : 异步同步
}

@enduml
```

### datahub-actions Pipeline 内部结构

```plantuml
skinparam backgroundColor #FEFEFE

database "Kafka\nMetadataChangeLog_Versioned_v1" as kafka
 rectangle "datahub-actions Pipeline" {
  [KafkaSource] as source
  [Filter\n(event_type filter)] as filter
  [metadata_change_sync\nAction] as sync_action
 }

kafka --> source
source --> filter
filter --> sync_action

note bottom of source : at-least-once\n处理语义
note bottom of filter : 过滤 event types：\nMetadataChangeLogEvent_v1
note bottom of sync_action : DatahubRestEmitter\n→ GMS REST API\nGMS 再同步到 OpenSearch
```

> ⚠️ **勘误**：原 design 中将 action 标注为 `rest`，实际应为 `metadata_change_sync`。原 PlantUML 中的 `OpenSearch Index Action` 不存在——OpenSearch 通过 GMS 异步同步。

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|------|------|----------|
| Topic 名称陈旧 | `docs/Module8.md` 中仍写 `MetadataChangeLog_v4` | 架构文档修正需用户授权，notebook 中使用正确名称 |
| Action type 陈旧 | 原 design 写 `rest`，实际应为 `metadata_change_sync` | 已修正，见 Decision 2 |
| Demo 环境无 Kafka | Phase 2 无法实际运行，只能架构展示 | notebook诚实声明，重点在架构理解 |
| Delta-Lake `fileExtensions` 不存在 | 原 recipe 包含 `fileExtensions` 配置项，官方 delta-lake source 无此参数 | Delta-Lake source 无需此参数，默认扫描所有 Parquet 文件 |
| datahub-actions 与 GMS 版本耦合 | actions 版本需与 GMS 版本匹配 | 使用官方 `acryl-datahub/actions` 镜像，与 GMS 同版本 |
| Phase 1/2 并存维护成本 | 两套路径需同时维护文档和脚本 | Phase 2 稳定后 deprecated Phase 1；本变更不修改 Phase 1 脚本 |

## Migration Plan

### 部署步骤

1. **准备环境**
   ```bash
   # 使用官方 CLI 启动完整 DataHub 栈
   datahub docker quickstart
   ```

2. **配置 datahub-actions**
   - 复制 `datahub-actions.yml` 到项目
   - 验证 Kafka topic 可访问：`datahub docker quickstart` 自带 Kafka

3. **配置 Delta-Lake ingestion**
   - 填写 `delta-lake-ingestion.yaml` 中的 `base_path` 为实际 lakehouse 路径
   - 验证 GMS 可达：`curl http://localhost:8080/ping`

4. **运行教学 notebook**
   ```bash
   jupyter notebook notebook/module8.ipynb
   ```

### 回滚策略

- datahub-actions 配置错误：停止 actions 容器，回退至 Phase 1 手工模式
- Delta-Lake ingestion 失败：`scripts/emit_browsepaths.py` 保留作为 fallback
- GMS REST API 失败：检查 GMS 健康状态，重启 `datahub-gms` 容器

## Open Questions

| 问题 | 状态 | 备注 |
|------|------|------|
| `docs/Module8.md` 中 `MetadataChangeLog_v4` 是否需要修正 | 待用户授权 | CLAUDE.md 约束不得主动修改文档 |
| `docs/Module8.md` 中 action type `rest` 是否需要修正为 `metadata_change_sync` | 待用户授权 | CLAUDE.md 约束不得主动修改文档 |
| datahub-actions 是否需要在 `docker-compose.quickstart-profile.yml` 中额外配置 | 待验证 | quickstart 默认已包含 actions 服务 |
| Delta-Lake ingestion 增量扫描策略 | 待设计 | 全量扫描可能慢，可考虑定时任务 |
