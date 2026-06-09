# 计划：在 datahub-quickstart.yml 中补全 Neo4j，保留 OpenSearch 做搜索后端

## 目标

在现有的 `datahub-quickstart.yml` 中，Neo4j 服务已定义但从未成功运行过。
确保 datahub-gms 使用 **OpenSearch** 做搜索索引（`ELASTICSEARCH_IMPLEMENTATION: opensearch`），
同时使用 **Neo4j** 做图谱服务（`GRAPH_SERVICE_IMPL: neo4j`），两者共存。

## 当前上下文

- `datahub-quickstart.yml` 中已有 `neo4j:4.4.9-community` 服务定义（端口 27474/27687）
- `neo4jdata` / `neo4jlogs` volume 已定义
- 但 GMS 服务的环境变量中 `GRAPH_SERVICE_IMPL` 仍为 `neo4j`，且 `NEO4J_*` 变量已正确配置
- 之前快速启动失败原因是 **8080 端口被占用**（GMS 无法绑定）
- 所有 datahub 容器当前已停止

## 方案：端口映射 + 官方 compose 合并

### 方案 A（推荐）：`datahub docker quickstart` + 本地 compose 追加

1. 让 `datahub docker quickstart` 拉起官方基础服务（gms/frontend/actions/kafka/opensearch/mysql/system-update）
2. 再用本地 `docker compose up -f datahub-quickstart.yml neo4j` 单独追加 neo4j 容器
3. GMS 已在官方 compose 中配置好 Neo4j 相关环境变量（`NEO4J_HOST/NEO4J_URI/NEO4J_USERNAME`），只需确保 `GRAPH_SERVICE_IMPL: neo4j`

**问题**：官方 quickstart 的 GMS 容器是否已包含 Neo4j 图谱服务支持（而不只是 Elasticsearch）？

### 方案 B：修改官方 compose 模板（覆盖环境变量）

`datahub docker quickstart` 支持通过环境变量覆盖配置，但不支持自定义 compose 文件。

1. 先运行 `datahub docker quickstart --version v1.6.0`（官方基础服务）
2. GMS 默认用 Elasticsearch 做图谱，需要验证官方 GMS 镜是否同时支持 Neo4j 图谱实现
3. 若不支持，需在官方 compose 之上追加 Neo4j 服务 + 重配 GMS

### 方案 C（最稳妥）：完全使用 datahub-quickstart.yml 启动

- 停止所有官方容器：`cd ~/.datahub/quickstart && docker compose -p datahub down`
- 直接 `docker compose -f datahub-quickstart.yml -p datahub up -d` 启动完整环境
- 确认 `system-update` 初始化不会因 8080 端口冲突失败
- 解决 `ELASTICSEARCH_IMPLEMENTATION: opensearch` 与官方 GMS 镜像的兼容性

## 待验证的关键问题

1. 官方 GMS 镜像（`acryldata/datahub-gms:v1.6.0`）是否同时支持 `GRAPH_SERVICE_IMPL: neo4j`？
2. Neo4j 图谱服务是否需要额外的数据初始化（与 Elasticsearch 不同的 schema）？
3. `datahub docker quickstart` 是否会自动配置 Neo4j 的认证凭据供 GMS 使用？

## 建议实施步骤

### Step 1：清理残留，确认端口空闲

```bash
# 确认 8080/28080/29200/27474/27687 端口未被占用
ss -tlnp | grep -E '8080|28080|29200|27474|27687'
```

### Step 2：确认官方 GMS 镜像对 Neo4j 的支持

阅读官方 v1.6.0 GMS Dockerfile 或 entrypoint，验证 `GRAPH_SERVICE_IMPL=neo4j` 是否被支持。

### Step 3A（如官方支持）：使用 datahub docker quickstart

```bash
# 先单独启动 neo4j（不通过官方 quickstart）
docker compose -f datahub-quickstart.yml up -d neo4j
# 再启动官方 quickstart
datahub docker quickstart --version v1.6.0
```

### Step 3B（如官方不支持）：完全用本地 compose

直接用 `datahub-quickstart.yml` 启动所有服务，手动处理 system-update。

## 风险

- 官方 GMS 镜像可能只内置 Elasticsearch 图谱支持，需要额外配置才能切换到 Neo4j
- Neo4j 和 OpenSearch 同时运行内存消耗较大
- system-update 初始化 GMS 索引时若 Neo4j 未就绪可能导致失败
