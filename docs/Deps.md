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

```bash
# docker-compose.yml（Kafka + Zookeeper 单节点）
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    hostname: zookeeper
    container_name: zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    hostname: kafka
    container_name: kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
```

```bash
# 启动
docker-compose up -d

# 验证
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

**依赖的 Kafka Connect 镜像（Debezium CDC）：**

```bash
docker pull quay.io/debezium/connect:2.3
```

---

### 1.3 时序存储（TimescaleDB）

已在 PI-System 使用，本方案复用 TimescaleDB 作为 PI 历史数据的归档存储和 OLAP 查询加速。

```bash
# 启动 TimescaleDB（生产用云厂商托管或独服）
docker run -d \
  --name timescaledb \
  -p 5432:5432 \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin123 \
  -e POSTGRES_DB=pi_archive \
  -v timescaledb-data:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg15
```

```bash
# 验证
docker exec -it timescaledb psql -U admin -d pi_archive -c "SELECT version();"
```

---

## 2. 元数据与资产目录

### 2.1 DataHub（元数据管理平台）

核心元数据管理平台，选型理由见 Design.md 3.2 节。

**前置依赖：MySQL + Elasticsearch**

```yaml
# docker-compose.yml（DataHub 前置服务）
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    hostname: mysql
    container_name: datahub-mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: datahub_root
      MYSQL_DATABASE: datahub
      MYSQL_USER: datahub
      MYSQL_PASSWORD: datahub
    volumes:
      - mysql-data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_bin

  elasticsearch:
    image: elasticsearch:7.17.9
    hostname: elasticsearch
    container_name: elasticsearch
    ports:
      - "9200:9200"
    environment:
      discovery.type: single-node
      ES_JAVA_OPTS: "-Xms1g -Xmx1g"
      xpack.security.enabled: "false"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    mem_limit: 2g
```

```bash
# 启动前置服务
docker-compose -f docker-compose前置.yml up -d
```

**DataHub 本体（Datahub-Containerized）**：

> 注意：DataHub 官方推荐使用 `datahub docker quickstart` 命令，但该命令依赖 Datahub CLI。也可直接使用 acryldata 提供的镜像自建。

```bash
# 方式一：官方 quickstart（推荐用于演示）
# 安装 DataHub CLI
curl -fsSL https://Raw.githubusercontent.com/datahub-project/datahub/master/quickstart.sh | bash

# 方式二：手动 Docker Compose（生产推荐）
# 获取官方 docker-compose 文件
wget https://raw.githubusercontent.com/datahub-project/datahub/master/docker-composeonitoring/docker-compose.yml

# 修改 MySQL 和 Elasticsearch 指向外部服务（上述 yaml 启动的）
# 然后
docker-compose up -d
```

**验证：**
```bash
# DataHub 前端
open http://localhost:9002

# DataHub GMS（Metadata Service）
curl -s http://localhost:8080/health
```

---

## 3. 数据质量

### 3.1 Great Expectations（Python 库）

质量检测引擎，通过 pip 安装。

```bash
uv add great-expectations
```

```toml
# pyproject.toml
[project]
dependencies = [
    "pandas>=2.0",
    "pyarrow>=14.0",
    "numpy>=1.26",
    "great-expectations>=0.18",
]
```

```python
# 快速验证安装
import great_expectations as ge
print(ge.__version__)  # 0.18.x
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
# Delta Lake Spark connector（通过 pyspark 自动携带）
uv add pyspark>=3.4
```

```python
# 验证 Delta Lake 功能
from pyspark.sql import SparkSession
spark = SparkSession.builder \
    .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
    .getOrCreate()

spark.read.format("delta").load("s3://bucket/path")
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
# Apache Toree（Jupyter 内核，支持 Spark）
# 或直接用 PySpark
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

```bash
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
      - |
        FLINK_PROPERTIES=
        jobmanager.rpc.address: jobmanager
        state.backend: rocksdb

  taskmanager:
    image: flink:1.17.1
    hostname: taskmanager
    container_name: flink-taskmanager
    depends_on:
      - jobmanager
    command: taskmanager
    scale: 2
    environment:
      - |
        FLINK_PROPERTIES=
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
docker-compose up -d

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
# Docker Compose
version: '3.8'
services:
  superset:
    image: apache/superset:latest
    container_name: superset
    ports:
      - "8088:8088"
    environment:
      SUPERSET_SECRET_KEY: superset_secret_key_change_me
    volumes:
      - superset-data:/var/lib/superset
    mem_limit: 4g
```

```bash
# 初始化（首次启动）
docker exec -it superset superset db upgrade
docker exec -it superset superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@example.com \
    --password admin123
docker exec -it superset superset init

# 验证
open http://localhost:8088   # admin / admin123
```

**接入 Doris（推荐）：**
```python
# Superset → Sources → Databases → Add Database
Database Name: doris_dwm
SQLAlchemy URI: mysql+pymysql://root:@doris-fe:9030/dwm
```

---

## 9. 完整 Docker Compose（一体化演示环境）

以下文件一次性启动所有基础服务（Kafka / Zookeeper / MySQL / Elasticsearch / DataHub / MinIO / Doris / Flink / DolphinScheduler / Grafana / Superset）：

```yaml
# docker-compose.all-in-one.yml
version: '3.8'

services:
  # ── 1. MinIO（对象存储）───────────────────────────────
  minio:
    image: minio/minio:latest
    container_name: minio
    ports:
      - "9000:9000"   # API
      - "9001:9001"   # Console
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: admin123
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── 2. Zookeeper + Kafka───────────────────────────────
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    container_name: zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    container_name: kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"

  # ── 3. MySQL（DataHub 元数据库 + OLTP）───────────────
  mysql:
    image: mysql:8.0
    container_name: datahub-mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: datahub_root
      MYSQL_DATABASE: datahub
      MYSQL_USER: datahub
      MYSQL_PASSWORD: datahub
    volumes:
      - mysql-data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_bin

  # ── 4. Elasticsearch（DataHub 搜索）──────────────────
  elasticsearch:
    image: elasticsearch:7.17.9
    container_name: elasticsearch
    ports:
      - "9200:9200"
    environment:
      discovery.type: single-node
      ES_JAVA_OPTS: "-Xms1g -Xmx1g"
      xpack.security.enabled: "false"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    mem_limit: 2g

  # ── 5. DataHub（元数据管理）────────────────────────────
  datahub:
    image: acryldata/datahub-frontend-react:v1.3.0.1
    container_name: datahub
    depends_on:
      mysql:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
    ports:
      - "9002:9002"
    environment:
      DATABASE_HOST: mysql
      DATABASE_PORT: 3306
      DATABASE_NAME: datahub
      DATABASE_USERNAME: datahub
      DATABABASE_PASSWORD: datahub
      DATAHUB_GMS_HOST: datahub-gms
      ELASTICSEARCH_HOST: elasticsearch
      ELASTICSEARCH_INDEX_FLAVOR: elasticsearch
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9002"]
      interval: 30s
      timeout: 10s
      retries: 5

  datahub-gms:
    image: acryldata/datahub-gms:latest
    container_name: datahub-gms
    depends_on:
      mysql:
        condition: service_healthy
    ports:
      - "8080:8080"
    environment:
      DATABASES_HOST: mysql
      DATABASES_PORT: 3306
      KAFKA_BOOTSTRAPSERVER: kafka:29092
      ELASTICSEARCH_HOST: elasticsearch
      ENTITY_SERVICE_AUTH_ENABLED: "false"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ── 6. Apache Doris（OLAP）───────────────────────────
  doris-fe:
    image: apache/doris-fe:2.0.0
    container_name: doris-fe
    ports:
      - "8030:8030"
      - "9030:9030"
    environment:
      FE_SERVERS: fe1:127.0.0.1:9010

  doris-be:
    image: apache/doris-be:2.0.0
    container_name: doris-be
    depends_on:
      - doris-fe
    ports:
      - "8040:8040"
    environment:
      BE_ADDR: doris-be:9050
      FE_ADDR: doris-fe:9010
    volumes:
      - doris-be-data:/opt/apache-doris/be/storage

  # ── 7. Apache Flink（流处理）─────────────────────────
  flink-jobmanager:
    image: flink:1.17.1
    container_name: flink-jobmanager
    ports:
      - "8081:8081"
    command: jobmanager
    environment:
      - |
        FLINK_PROPERTIES=
        jobmanager.rpc.address: flink-jobmanager

  flink-taskmanager:
    image: flink:1.17.1
    container_name: flink-taskmanager
    depends_on:
      - flink-jobmanager
    command: taskmanager
    scale: 1
    environment:
      - |
        FLINK_PROPERTIES=
        jobmanager.rpc.address: flink-jobmanager
        taskmanager.numberOfTaskSlots: 4

  # ── 8. DolphinScheduler（调度）────────────────────────
  dolphinscheduler:
    image: apache/dolphinscheduler-standalone-server:latest
    container_name: dolphinscheduler
    ports:
      - "12345:12345"
      - "25333:25333"
    mem_limit: 2g

  # ── 9. Grafana（监控）─────────────────────────────────
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin123
    volumes:
      - grafana-data:/var/lib/grafana

  # ── 10. Superset（BI）────────────────────────────────
  superset:
    image: apache/superset:latest
    container_name: superset
    ports:
      - "8088:8088"
    environment:
      SUPERSET_SECRET_KEY: superset_demo_key_2024
    volumes:
      - superset-data:/var/lib/superset
    mem_limit: 4g

volumes:
  minio-data:
  mysql-data:
  es-data:
  doris-be-data:
  grafana-data:
  superset-data:
```

```bash
# 一键启动（需要 16GB+ 内存）
docker-compose -f docker-compose.all-in-one.yml up -d

# 检查所有服务健康状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**服务端口速查：**

| 服务 | 端口 | 说明 |
|------|------|------|
| MinIO API | 9000 | S3 兼容 |
| MinIO Console | 9001 | Web 控制台 |
| Kafka | 9092 | 消息队列 |
| Zookeeper | 2181 | Kafka 依赖 |
| MySQL | 3306 | 元数据库 |
| Elasticsearch | 9200 | 搜索索引 |
| DataHub | 9002 | Web UI |
| DataHub GMS | 8080 | Metadata API |
| Doris FE | 9030 | MySQL 协议 |
| Doris BE | 8040 | 计算节点 |
| Flink UI | 8081 | 流处理管理 |
| DolphinScheduler | 12345 | 调度平台 |
| Grafana | 3000 | 监控看板 |
| Superset | 8088 | BI 分析 |

---

## 10. Python 依赖清单

所有 Python 库通过 `uv add` 安装，统一记录在 `pyproject.toml`：

```toml
[project]
requires-python = ">=3.10"
dependencies = [
    # ── 数据处理 ──────────────────────────
    "pandas>=2.0",
    "pyarrow>=14.0",
    "numpy>=1.26",

    # ── 数据湖 ────────────────────────────
    "pyspark>=3.4",
    "deltalake>=0.12",

    # ── 数据质量 ──────────────────────────
    "great-expectations>=0.18",

    # ── 时序数据 ──────────────────────────
    "psycopg2-binary>=2.9",       # TimescaleDB/PostgreSQL
    "sqlalchemy>=2.0",

    # ── 消息队列 ──────────────────────────
    "kafka-python>=2.0",

    # ── 对象存储 ──────────────────────────
    "boto3>=1.28",

    # ── OLAP ─────────────────────────────
    "pymysql>=1.1",

    # ── 数据质量告警 ──────────────────────
    "requests>=2.31",
]

[dependency-groups]
dev = [
    "pytest>=7.0",
    "jupyter>=1.0",
]
```

```bash
# 安装所有依赖
uv sync

# 验证核心依赖
python -c "
import pandas, numpy, pyarrow
import great_expectations as ge
import pyspark
import boto3
import kafka
print('✓ All core dependencies installed')
"
```

---

## 11. 快速验证清单

```bash
# 1. 基础设施
curl -s http://localhost:9000/minio/health/live          # MinIO
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list  # Kafka
docker exec -it timescaledb psql -U admin -c "SELECT 1"  # TimescaleDB

# 2. 元数据
curl -s http://localhost:9200                             # Elasticsearch
curl -s http://localhost:8080/health                       # DataHub GMS
curl -s http://localhost:9002                              # DataHub UI

# 3. OLAP
mysql -h 127.0.0.1 -P 9030 -uroot -e "SHOW FRONTENDS"    # Doris

# 4. 流处理
curl -s http://localhost:8081/taskmanagers               # Flink

# 5. 调度
curl -s http://localhost:12345/dolphinscheduler           # DolphinScheduler

# 6. 可视化
curl -s http://localhost:3000/api/health                  # Grafana
curl -s http://localhost:8088/health                       # Superset

# 7. Python 依赖
uv run python -c "import pandas, pyspark, great_expectations; print('OK')"
```
