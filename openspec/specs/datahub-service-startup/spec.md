# datahub-service-startup Specification

## Purpose
TBD - created by archiving change setup-datahub-and-load-data. Update Purpose after archive.
## Requirements
### Requirement: DataHub 容器通过 docker compose 启动并健康
项目根目录的 `datahub-quickstart.yml` MUST 能通过 `docker compose -f datahub-quickstart.yml up -d` 启动；system-update、datahub-gms、frontend、datahub-actions 四个核心容器 MUST 在 5 分钟内依次进入 healthy 状态（system-update 必须先 completed_successfully，然后 datahub-gms 进入 healthy，最后 frontend 和 datahub-actions 进入 healthy）。

#### Scenario: 完整启动成功
- **WHEN** 在 `~/Playground/dg-demo` 目录执行 `docker compose -f datahub-quickstart.yml up -d`
- **THEN** 6 个 DataHub 相关容器（kafka-broker、mysql、opensearch、system-update-quickstart、datahub-gms-quickstart、frontend-quickstart、datahub-actions-quickstart）全部 Up，且 gms 与 frontend 的 healthcheck 通过

#### Scenario: 已有卷可复用
- **WHEN** 之前已经成功启动过、本次 `up` 复用既有命名卷
- **THEN** system-update 仍会重新跑一次初始化（`condition: service_completed_successfully`），但耗时应 < 1 分钟；mysql/opensearch 直接 healthy

### Requirement: 前端 UI 可在 http://localhost:29002 访问
浏览器打开 http://localhost:29002 MUST 能看到 DataHub v2 主题的登录页或首页（quickstart 模式无认证则直接进入首页），UI 框架（顶部导航、左侧 Browse 侧栏占位）渲染正常，无白屏、无"页面崩溃"、无组件加载失败错误。

#### Scenario: 首页加载成功
- **WHEN** 用户浏览器打开 http://localhost:29002
- **THEN** 页面在 5 秒内显示 DataHub v2 主题首页，且浏览器 Network 面板中 `/api/graphql` 请求返回 200

#### Scenario: 旧镜像缓存不导致 stale bundle
- **WHEN** 浏览器强制刷新（Ctrl+Shift+R）
- **THEN** 仍能正常加载（说明 frontend-react 镜像内的 React bundle 完整、无 404 静态资源）

### Requirement: GMS 后端可响应健康检查与 GraphQL 查询
http://localhost:28080/health MUST 返回 200，`/api/graphql` MUST 能响应 `{ __typename }` introspection 查询。

#### Scenario: 健康检查通过
- **WHEN** 执行 `curl -sS http://localhost:28080/health`
- **THEN** 返回 `{"status":"available"}` 或类似 200 响应，退出码 0

#### Scenario: GraphQL introspection 正常
- **WHEN** 执行 `curl -X POST http://localhost:28080/api/graphql -d '{"query":"{__typename}"}'`
- **THEN** 返回 `{"data":{"__typename":"Query"}}` 且 HTTP 状态码 200

### Requirement: 后端依赖服务就绪
OpenSearch (29200)、MySQL (23306)、Kafka (29092) 三个依赖容器 MUST 进入 healthy，且 OpenSearch 中 `datasetindex_v2` 索引已创建、MySQL 中 `datahub` schema 已初始化。

#### Scenario: OpenSearch 索引就绪
- **WHEN** 执行 `curl -s "http://localhost:29200/_cat/indices?v" | grep datasetindex_v2`
- **THEN** 能看到 `datasetindex_v2` 索引（哪怕是空索引）且 `health` 列值为 green 或 yellow

#### Scenario: MySQL schema 就绪
- **WHEN** 执行 `docker exec datahub-mysql-1 mysql -uroot -pdatahub -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='datahub'"`
- **THEN** 返回 ≥ 1（DataHub v1.6.0 将所有 aspect 合并到单一 `metadata_aspect_v2` 表；可执行 `docker exec datahub-mysql-1 mysql -uroot -pdatahub datahub -e "SELECT COUNT(*) FROM metadata_aspect_v2"` 进一步验证 ≥ 84 = 12 数据集 × 7 aspects）

### Requirement: 图后端配置为 Elasticsearch
`datahub-quickstart.yml` 中 GMS 和 system-update 的 `GRAPH_SERVICE_IMPL` MUST 都是 `elasticsearch`，且 `datahub-quickstart.yml` MUST NOT 包含 `neo4j` service。

#### Scenario: yml 配置自检
- **WHEN** 执行 `grep -E "GRAPH_SERVICE_IMPL" datahub-quickstart.yml`
- **THEN** 至少 2 行匹配（gms 和 system-update 各 1 行）且值都是 `elasticsearch`

#### Scenario: 无 neo4j 容器残留
- **WHEN** 执行 `grep -A 1 "^  neo4j:" datahub-quickstart.yml`
- **THEN** 无匹配（neo4j service 已删除）

### Requirement: frontend 等 GMS 健康后才启动
`datahub-quickstart.yml` 中 `frontend-quickstart.depends_on` MUST 包含 `datahub-gms-quickstart` 且 condition 为 `service_healthy`（除 `system-update-quickstart` 外）。

#### Scenario: 启动顺序可观察
- **WHEN** 启动过程中观察 `docker compose -f datahub-quickstart.yml ps` 输出
- **THEN** frontend 容器开始时间 MUST 晚于 datahub-gms 容器健康时间

