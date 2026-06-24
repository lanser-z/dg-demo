## 1. 环境准备

- [x] 1.1 确认 `datahub docker quickstart` CLI 已安装（`pip install acryl-datahub`）✓ datahub v1.6.0
- [x] 1.2 确认 `uv` 可用（`uv --version`）✓ uv 0.10.12
- [x] 1.3 确认 Docker 和 Docker Compose v2 已安装 ✓ Docker 29.1.3, Compose 2.40.3

## 2. datahub-actions Kafka 配置

- [x] 2.1 创建 `datahub-actions.yml` 配置文件
- [x] 2.2 配置 Kafka source：bootstrap servers 和 topic `MetadataChangeLog_Versioned_v1`
- [x] 2.3 配置 pipeline filter（使用 `filters` 列表语法，event_type filter）
- [x] 2.4 配置 `metadata_change_sync` action：目标 GMS server URL、`urn_regex`、`aspects_to_exclude`

## 3. Delta-Lake Ingestion Recipe

- [x] 3.1 创建 `delta-lake-ingestion.yaml` 配置文件
- [x] 3.2 配置 `delta-lake` source：`base_path` 填入实际 lakehouse 路径（如 `data/lakehouse`）
- [x] 3.3 配置 `datahub-rest` sink：GMS server URL（`http://localhost:8080`）
- [x] 3.4 配置 `platform_instance` 和 `env`（如 `platform_instance: "dg-demo-lakehouse"`, `env: "PROD"`）

## 4. GMS REST API 示例代码

- [x] 4.1 编写 Python requests 示例：POST dataset entity with browsePaths to `/entities`
- [x] 4.2 验证 GMS health endpoint：`curl http://localhost:28080/health` ✓ 200 OK，OpenAPI GET 正常

## 5. Module8 Notebook

- [x] 5.1 编写痛点故事 markdown cell（Phase 1 四个问题）
- [x] 5.2 添加架构图：PlantUML 展示 Phase 1 vs Phase 2 数据流对比
- [x] 5.3 编写 direct_es_bulk.py 演示 code cell（`--dry-run` 模式）
- [x] 5.4 展示 datahub-actions 配置 code cell（使用正确 topic `MetadataChangeLog_Versioned_v1`）
- [x] 5.5 展示 REST API Python 示例 code cell
- [x] 5.6 添加 Demo 环境限制说明 markdown cell（诚实声明无真实 Kafka）

## 6. 文档与验证

- [x] 6.1 确认 `datahub docker quickstart` 能成功启动完整栈（GMS + MySQL + Kafka + OpenSearch + datahub-actions）— 服务已运行（端口 28080/29092/29200）
- [x] 6.2 确认 Delta-Lake ingestion recipe YAML 语法正确（`uv run datahub ingest -c delta-lake-ingestion.yaml --dry-run`）✓ 成功，发现 21 个 dataset
- [x] 6.3 确认 Jupyter notebook 能正常打开并渲染所有 cells ✓ JSON 有效
