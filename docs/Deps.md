# A公司数据治理平台 — 依赖与服务清单

本文档按技术选型列出所有需要安装的第三方依赖、服务和库，优先使用 Docker 部署。

---

## 1. 基础设施层

### 1.1 对象存储（MinIO）

数据湖的底层存储，兼容 S3 协议。

```bash
# 单节点快速启动
docker run -d \
  --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=admin123" \
  -v minio-data:/data \
  minio/minio server /data --console-address ":9001"
```

```bash
# 验证
curl -s http://localhost:9000/minio/health/live
```

**生产环境推荐：**
- 至少 3 节点纠删码模式（EC），保证数据可靠性
- 外接 Nginx 做负载均衡

---

### 1.2 消息队列（Apache Kafka）

CDC 数据采集和 SCADA 实时流的统一总线。

```yaml
# docker-compose.yml（Kafka KRaft 模式，无需 Zookeeper）
version: '3.8'
services:
  kafka:
    image: confluentinc/cp-kafka:8.0.0
    hostname: broker
    container_name: datahub-kafka
    ports:
      - "29092:29092"  # 外部访问
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: '1'
      KAFKA_PROCESS_ROLES: controller, broker
      KAFKA_LISTENERS: BROKER://broker:29092,EXTERNAL://broker:9092,CONTROLLER://broker:39092
      KAFKA_ADVERTISED_LISTENERS: BROKER://broker:29092,EXTERNAL://localhost:29092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,BROKER:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: '1@broker:39092'
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_HEAP_OPTS: -Xms512m -Xmx512m
      KAFKA_MAX_MESSAGE_BYTES: 5242880
```

```bash
# 启动
docker compose up -d kafka

# 验证
docker exec kafka kafka-topics --bootstrap-server localhost:29092 --list
```

---

## 2. 元数据与资产目录

### 2.1 DataHub（元数据管理平台）

核心元数据管理平台，选型理由见 Design.md 3.2 节。

**当前使用版本：v1.6.0**
**搜索后端：OpenSearch 2.19.3**（不再使用 Elasticsearch）
**图数据库：Neo4j 4.4.9-community**（可与 OpenSearch 共存，GRAPH_SERVICE_IMPL=neo4j）

#### 启动方式

使用项目根目录的 `datahub-quickstart.yml`，一键启动所有 DataHub 相关服务：

```bash
# 启动完整 DataHub（MySQL + Kafka + OpenSearch + Neo4j + GMS + Frontend + Actions）
cd /home/szs/Playground/dg-demo
docker compose -f datahub-quickstart.yml up -d
```

**各服务端口：**

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| 前端 Web UI | datahub-frontend-quickstart | **29002** | 浏览器访问 |
| GMS API | datahub-datahub-gms-quickstart | **28080** | 后端接口 |
| Neo4j 浏览器 | datahub-neo4j | **27474** | 图数据库 UI |
| Neo4j Bolt | datahub-neo4j | **27687** | 程序连接 |
| OpenSearch | datahub-opensearch | **29200** | 搜索索引 |
| MySQL | datahub-mysql | **23306** | 元数据存储 |
| Kafka | datahub-kafka-broker | **29092** | 消息队列 |

**启动顺序（compose 自动处理）：**

```
kafka-broker (healthy) → mysql (healthy) → opensearch (healthy) → neo4j (healthy)
     → system-update-quickstart (一次性 setup 任务)
     → datahub-gms-quickstart (启动 GMS)
     → frontend-quickstart
     → datahub-actions-quickstart
```

**注意事项：**
- Neo4j healthcheck 使用 `bash /dev/tcp/`，无需容器内安装额外工具
- 首次启动 system-update-quickstart 约需 2-3 分钟完成索引初始化
- Neo4j 默认账号：`neo4j` / `datahub`
- DataHub 前端无需登录（quickstart 模式默认关闭认证）

#### 镜像预拉取

```bash
# 提前拉取，避免首次启动超时（后台执行）
docker pull acryldata/datahub-gms:v1.6.0 &
docker pull acryldata/datahub-frontend-react:v1.6.0 &
docker pull acryldata/datahub-actions:v1.6.0 &
docker pull acryldata/datahub-upgrade:v1.6.0 &
docker pull opensearchproject/opensearch:2.19.3 &
docker pull neo4j:4.4.9-community &
docker pull mysql:8.2 &
wait
```

#### 环境验证

```bash
# 检查所有服务状态
docker ps --format "table {{.Names}}\t{{.Status}}" | grep datahub

# DataHub 前端
open http://localhost:29002

# GMS 健康检查
curl -s http://localhost:28080/health

# OpenSearch 索引验证
curl -s "http://localhost:29200/_cat/indices?v"

# Neo4j 验证
curl -s http://localhost:27474

# MySQL schema 验证
docker exec datahub-mysql mysql -u root -pdatahub -e "SHOW TABLES;" datahub
```

#### 从旧版本升级

如果之前使用 v1.3.0.1，数据无法自动迁移，需要重新启动一次 setup：

```bash
# 删除旧容器和卷，重新启动
docker compose -f datahub-quickstart.yml down -v
docker compose -f datahub-quickstart.yml up -d
```

---

## 3. 数据质量

### 3.1 Great Expectations（Python 库）

质量检测引擎，通过 uv 安装。

```bash
uv add great-expectations
```

```python
# 快速验证安装
import great_expectations as ge
print(ge.__version__)
```

### 3.2 自研告警服务（需自行开发）

不依赖第三方，使用 Python + 企业微信/钉钉/邮件 SDK 即可：

```bash
# 告警通知依赖（按需选择）
uv add wechatwork-sdk    # 企业微信机器人
uv add aliyun-sdk-python # 钉钉（阿里云 SDK）
uv add yagmail           # 邮件通知
```

---

## 4. 数据湖与批处理

### 4.1 Delta Lake

通过 PySpark 使用，不需要单独安装。

```bash
uv add pyspark>=3.4
```

```python
# 验证 Delta Lake 功能
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
    .getOrCreate()
```

### 4.2 MinIO S3 兼容存储（见 1.1）

Delta Lake 数据最终写入 MinIO。

```python
# Spark 读写 MinIO 配置示例
spark = SparkSession.builder \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "admin123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .getOrCreate()
```

### 4.3 Apache Spark

**演示/开发环境：Local 模式（Docker）**

```bash
uv add pyspark

# 提交 Spark 作业
spark-submit \
    --master "spark://localhost:7077" \
    --deploy-mode cluster \
    app.py
```

**生产环境：集群模式（Kubernetes 或 YARN）**

```bash
# Kubernetes 部署 Spark（推荐生产使用）
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install spark bitnami/spark \
    --set master.webPort=8080 \
    --set worker.webPort=8081 \
    --set worker.replicas=3
```

---

## 5. 流处理

### 5.1 Apache Flink

SCADA 实时流预处理和实时质量检测。

```yaml
# Docker Compose 单节点 Flink
version: '3.8'
services:
  jobmanager:
    image: flink:1.17.1
    hostname: jobmanager
    container_name: flink-jobmanager
    ports:
      - "8081:8081"
    command: jobmanager
    environment:
      FLINK_PROPERTIES: |
        jobmanager.rpc.address: jobmanager
        state.backend: rocksdb

  taskmanager:
    image: flink:1.17.1
    hostname: taskmanager
    container_name: flink-taskmanager
    depends_on:
      - jobmanager
    command: taskmanager
    environment:
      FLINK_PROPERTIES: |
        jobmanager.rpc.address: jobmanager
        taskmanager.numberOfTaskSlots: 4
```

```bash
# 验证 Flink UI
open http://localhost:8081
```

---

## 6. OLAP 层

### 6.1 Apache Doris

选型理由见 Design.md 6.1 节。FE + BE 架构，至少 1FE + 1BE。

```bash
# Docker Compose 快速体验（单节点）
version: '3.8'
services:
  doris-fe:
    image: apache/doris-fe:2.0.0
    hostname: doris-fe
    container_name: doris-fe
    ports:
      - "8030:8030"  # FE web
      - "9030:9030"  # MySQL protocol
    environment:
      FE_SERVERS: fe1:127.0.0.1:9010
    mem_limit: 2g

  doris-be:
    image: apache/doris-be:2.0.0
    hostname: doris-be
    container_name: doris-be
    ports:
      - "8040:8040"  # BE web
    depends_on:
      - doris-fe
    environment:
      BE_ADDR: doris-be:9050
      FE_ADDR: doris-fe:9010
    mem_limit: 4g
    volumes:
      - doris-be-data:/opt/apache-doris/be/storage
```

```bash
# 启动
docker compose up -d

# 验证（MySQL 客户端连接）
mysql -h 127.0.0.1 -P 9030 -uroot
```

```sql
-- 创建数据库
CREATE DATABASE dwm;
SHOW FRONTENDS;
SHOW BACKENDS;
```

---

## 7. 调度与编排

### 7.1 Apache DolphinScheduler

可视化任务调度，支持 DAG 编排、ELT 作业调度、质量检测定时任务。

```bash
# Docker Compose 单节点
docker run -d \
  --name dolphinscheduler \
  -p 12345:12345 \
  -p 3306:3306 \
  -p 25333:25333 \
  apache/dolphinscheduler-standalone-server:latest
```

```bash
# 验证
open http://localhost:12345/dolphinscheduler   # 默认账号/密码: admin dolphinscheduler
```

> **备选**：Apache Airflow。如果团队熟悉 Python DAG 编写，Airflow 的灵活性更高：
> ```bash
> uv add apache-airflow
> airflow standalone
> ```

---

## 8. 可视化层

### 8.1 Grafana（指标监控）

时序数据（PI）和 Kafka 监控的最佳搭档。

```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_USER=admin" \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin123" \
  -v grafana-data:/var/lib/grafana \
  grafana/grafana:latest
```

```bash
# 验证
open http://localhost:3000   # admin / admin123
```

**推荐数据源接入：**
- Prometheus（Kafka 监控）
- TimescaleDB（PI 时序数据）
- MySQL（质量检测结果）

### 8.2 Apache Superset（BI 分析）

支持 SQL Lab 即席查询，接入 Doris / MySQL。

```bash
docker run -d \
  --name superset \
  -p 8088:8088 \
  -e "SUPERSET_SECRET_KEY=superset_secret_key_change_me" \
  -v superset-data:/var/lib/superset \
  apache/superset:latest
```

```bash
# 初始化（首次启动）
docker exec -it superset superset db upgrade
docker exec -it superset superset fab create-admin \
    --username admin --firstname Admin --lastname User \
    --email admin@example.com --password admin123
docker exec -it superset superset init

# 验证
open http://localhost:8088   # admin / admin123
```

**接入 Doris（推荐）：**
```
Database Name: doris_dwm
SQLAlchemy URI: mysql+pymysql://root:@doris-fe:9030/dwm
```

---

## 9. 项目启动顺序

```bash
# 1. 启动 DataHub（核心基础设施）
cd /home/szs/Playground/dg-demo
docker compose -f datahub-quickstart.yml up -d

# 等待所有服务 healthy（约 2-3 分钟）
docker ps --format "table {{.Names}}\t{{.Status}}" | grep datahub

# 2. 安装 Python 依赖
uv sync

# 3. 验证 DataHub 前端
open http://localhost:29002

# 4. 验证 OpenSearch 中的数据资产
curl -s "http://localhost:29200/datasetindex_v2/_count"
```
