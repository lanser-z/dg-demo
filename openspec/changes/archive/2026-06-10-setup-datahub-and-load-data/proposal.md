## Why

当前 `datahub-quickstart.yml` 与项目 `docs/Step1.md` 记录的踩坑修复方案存在 3 处不一致：GMS 与 system-update 的 `GRAPH_SERVICE_IMPL` 分别指向不同的图后端、frontend-quickstart 不等 GMS 就绪即启动、v2 重构组件（`LINEAGE_GRAPH_V2`、`SHOW_BROWSE_V2` 等）在图服务异常时会渲染失败。直接后果是 DataHub v1.6.0 启动后前端显示不全或出错，无法支撑 5 系统 12 张表的元数据演示。

此变更目标是把项目部署配置对齐到 DataHub 官方推荐的轻量路径（ES 同时承担搜索与图服务），恢复 Browse 导航与资产目录可见性，使演示流程能正常进行。

## What Changes

- **修改** `datahub-quickstart.yml`：
  - GMS 与 system-update 的 `GRAPH_SERVICE_IMPL` 统一为 `elasticsearch`，移除与 Neo4j 相关的环境变量残留
  - 删除 `neo4j` service 及其 `datahub_neo4jdata` / `datahub_neo4jlogs` 卷（释放 569MB 镜像与 1G 内存）
  - `frontend-quickstart` 增加 `depends_on: datahub-gms-quickstart: condition: service_healthy`
  - 关闭 `LINEAGE_GRAPH_V2`、`SHOW_BROWSE_V2`、`SHOW_NAV_BAR_REDESIGN`，保留 `THEME_V2_DEFAULT: 'true'`（前端可继续使用 v2 主题，但避开依赖图服务的组件）
- **新增** 图索引重建步骤：容器启动后通过 GMS OpenAPI 触发 `RestoreIndices` job 重建 ES 中 `datasetindex_v2` / `graph_service_v1_*` 索引
- **新增** 元数据上报步骤：跑 `scripts/direct_es_bulk.py`（直写 OpenSearch 12 张表）+ `scripts/emit_browsepaths.py`（经 GMS 写 browsePath）
- **新增** 验证步骤：跑 `scripts/check_browse.py` + 浏览器打开 http://localhost:29002 确认 12 张表可见

**破坏性变更**：移除 neo4j 容器与 `emit_lineage.py` 当前的 Bolt 直写路径（后续如需血缘直写可重定向到 GMS OpenAPI，不在本变更范围）。

## Capabilities

### New Capabilities

- `datahub-service-startup`：启动 DataHub v1.6.0 + OpenSearch 2.19.3 + MySQL 8.2 + Kafka 8.0.0 全部服务，所有容器 healthcheck 通过、http://localhost:29002 可访问
- `asset-metadata-ingestion`：把 `data/historical/` 下的 12 张表（sap_erp × 6、pi_system × 1、lims × 1、oa × 3、scada × 1）以 `dataset` 实体形式上报到 DataHub，browsePath 指向 `<system>/<table_name>`

### Modified Capabilities

（无。`openspec/specs/` 目录不存在，没有现成能力需要修改。）

## Impact

| 类别 | 受影响项 | 说明 |
|------|----------|------|
| **配置** | `datahub-quickstart.yml` | 3 处修改 + 删除 neo4j service |
| **配置** | `openspec/specs/` | 本次新增 `datahub-service-startup` 与 `asset-metadata-ingestion` 两个规范目录 |
| **脚本（可能）** | `scripts/direct_es_bulk.py`、`scripts/emit_browsepaths.py`、`scripts/check_browse.py` | 端口已对齐 29200/28080/23306（Step1.md 记录已统一），本次不预期改动；若验证发现端口仍不对，按需微调 |
| **脚本（废弃）** | `scripts/emit_lineage.py` | 写入路径从 Neo4j Bolt 改为 GMS OpenAPI **不在本变更范围**；血缘数据本变更内**不上报**（12 张表的 dataset 资产先可见即可） |
| **数据** | `data/historical/`、`data/incremental/`、`data/lakehouse/` | 完全不动 |
| **文档** | `docs/Step1.md`、`docs/Deps.md` | 完全不动（变更落地后如需可单独发 change 更新） |
| **容器卷** | `datahub_neo4jdata`、`datahub_neo4jlogs` | 随 neo4j service 一起删除；其他卷（`datahub_mysqldata`、`datahub_osdata`、`datahub_broker`）保留 |
| **外部依赖** | 无新增、无删除 | 镜像已全部预拉取在本地 |

## 回滚计划

| 回滚点 | 触发条件 | 操作 | 数据影响 |
|--------|----------|------|----------|
| **R1：yml 改回** | 改 yml 后任何步骤出现非预期错误 | `git checkout datahub-quickstart.yml` | 零数据丢失 |
| **R2：容器整体回滚** | 启动后端口冲突 / 服务持续 unhealthy | `docker compose -f datahub-quickstart.yml down -v` | 丢失 `datahub_mysqldata` 中已初始化的 schema 与 `datahub_osdata` 中已上报的 12 张表索引（**不丢** `data/historical/` 原始 Parquet，可重跑 ingest） |
| **R3：仅回滚图服务** | 仅图相关功能异常，其他正常 | 保留 neo4j service、yml 改回旧值 | 同 R2 |
| **R4：完全干净** | 想从零开始 | `docker compose -f datahub-quickstart.yml down -v && docker volume prune` | 同 R2，并删除 dangling 卷 |

**回滚 SLA**：所有回滚可在 5 分钟内完成。`data/` 目录完全隔离于容器卷之外，不受任何 R 操作影响。

## 不在本变更范围

- 血缘数据上报（`emit_lineage.py` 重写 / 通过 GMS OpenAPI 写 lineage）—— 后续单独 change
- Great Expectations 质量规则运行 —— 现有 `run_great_expectations.py` 不依赖本变更
- Delta Lake 入湖、DuckDB DWA 宽表 —— 与 DataHub 元数据服务独立
- 演示文稿 / notebook 编写 —— 由 docs/Demo.md 现有流程覆盖
