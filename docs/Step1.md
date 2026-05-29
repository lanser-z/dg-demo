# 模块一实施步骤：数据资产可视化

---

## 1. Docker 服务

### 1.1 拉取镜像（后台执行，首次运行前）

```bash
# 建议提前拉取，避免启动时超时
docker pull mysql:8.0 &
docker pull elasticsearch:7.17.9 &
docker pull confluentinc/cp-zookeeper:7.4.0 &
docker pull confluentinc/cp-kafka:7.4.0 &
docker pull confluentinc/cp-schema-registry:7.9.2 &
docker pull acryldata/datahub-elasticsearch-setup:v1.3.0.1 &
docker pull acryldata/datahub-mysql-setup:v1.3.0.1 &
docker pull acryldata/datahub-upgrade:v1.3.0.1 &
docker pull acryldata/datahub-gms:v1.3.0.1 &
docker pull acryldata/datahub-frontend-react:v1.3.0.1 &
wait
```

### 1.2 一键启动

```bash
docker compose -f docker-compose.datahub.yml up -d
```

**关键经验（踩坑记录）：**

| 问题 | 原因 | 修复 |
|------|------|------|
| mysql-setup 启动失败（tcp://: 空地址） | 镜像使用 `MYSQL_HOST`/`MYSQL_PORT`，不是 `EBEAN_DATASOURCE_*` | 改用正确的环境变量名 |
| datahub-upgrade dockerize 失败（mysql: missing port） | `EBEAN_DATASOURCE_HOST=mysql` 缺少端口 | 设为 `EBEAN_DATASOURCE_HOST=mysql:3306` |
| upgrade 连 schema-registry 失败（localhost:8081 refused） | JAR 内硬编码 `KAFKA_SCHEMAREGISTRY_URL=http://localhost:8081` | 需设 `KAFKA_SCHEMAREGISTRY_URL=http://schema-registry:8081` |
| Kafka broker 启动失败（Each listener must have different port） | 同时配置了 `KAFKA_LISTENERS` 和 `KAFKA_ADVERTISED_LISTENERS` 但未分离 | 使用 `PLAINTEXT://kafka:9092` 单 listener 分离 |
| entity-registry.yml 找不到 | Java 用相对路径 `../../metadata-models/src/main/resources/entity-registry.yml` | 启动命令加 `mkdir -p ... && cp ...` |
| 容器内 `/metadata-models` mkdir 权限不足 | 非 root 用户无法创建目录 | 加 `user: root` |
| GMS API 401 未授权 | 默认启用认证 | 加 `METADATA_SERVICE_AUTH_ENABLED: false` |
| ingest_metadata 端点 404 | 用的是旧的 Rest.li `/datasets?action=ingest` | 改用 OpenAPI `/openapi/v3/entity/dataset?async=false` |
| ingest_metadata 500/400 | aspect 格式错误 | OpenAPI 格式：`aspectName: {value: {actual_data}}` |
| GraphQL searchAcrossEntities 查不到数据 | v1.3.0 不支持 `entities`/`type` 参数，ES 索引异步更新 | 直接用 URN 查询，或等 ES 索引完成 |

**启动顺序（compose 自动处理）：**
```
mysql (healthy) → mysql-setup (Flyway migrations)
               → elasticsearch-setup
               → datahub-upgrade (SystemUpdate，初始化 ES indices + MySQL schema)
               → datahub-gms (启动 GMS)
               → datahub-frontend
```

**手动验证：**
```bash
# 基础服务
curl -s http://localhost:23308  # Elasticsearch
curl -s http://localhost:23309/health  # DataHub GMS
curl -s http://localhost:23310  # DataHub Frontend

# MySQL schema 验证
docker exec datahub-mysql mysql -u datahub -pdatahub -e "SHOW TABLES;" datahub
# 期望看到：metadata_aspect_v2 等表
```

---

## 2. Python 依赖安装

```bash
uv sync
```

**核心依赖（pyproject.toml 中已有）：**
- `pandas>=2.0` — 数据处理
- `pyarrow>=14.0` — Parquet 读写
- `requests>=2.31` — HTTP 客户端（DataHub API 调用）

**无需安装：**
- `acryl-datahub` 是 CLI 工具（`uv tool install`），不是项目依赖

---

## 3. 待开发功能

### 3.1 资产目录查询（部分完成）

**文件：** `src/dg_platform/datahub_client.py`

已实现：
- `DataHubClient.is_alive()` — 健康检查 ✓
- `DataHubClient.ingest_metadata(assets)` — OpenAPI v3 格式上报元数据 ✓
- `DataHubClient.get_lineage(guid)` — 血缘查询（未测试）
- `DataHubClient.list_datasets()` — GraphQL 查询（需适配 v1.3.0）

**环境变量：**
```bash
export DATAHUB_GMS_URL=http://localhost:23309   # 必须设置
```

**验证 ingest：**
```python
import os, pandas as pd
os.environ['DATAHUB_GMS_URL'] = 'http://localhost:23309'
from dg_platform.datahub_client import get_client
client = get_client()
print('GMS alive:', client.is_alive())  # True

assets = pd.DataFrame([{
    'table_name': 'sap_erp.vbak',
    'chinese_name': 'SAP-ERP 销售订单主表',
    'system': 'SAP-ERP',
    'owner': '张三',
    'row_count': 10000,
    'size_mb': 50.5,
    'security_level': '重要',
}])
result = client.ingest_metadata(assets)
print(result)  # {'ingested': 1, 'failed': 0, ...}
```

### 3.2 资产可视化模块

**文件：** `src/dg_platform/asset_visualizer.py`（待实现）

需实现：
- `get_system_status()` → List[SystemStatus] — 5个系统接入状态
- `get_asset_catalog()` → DataFrame — 资产目录（表名/中文名/负责人/行数/大小/分区字段）
- `get_quality_score_card()` → DataFrame — 每系统质量评分
- `get_security_classification()` → DataFrame — 安全分级

### 3.3 数据探查服务

**文件：** `src/dg_platform/data_profiler.py`（待实现）

需实现：
- `profile_parquet(path)` → TableProfile — 单表探查
- `discover_partitions(base_path)` → List[Partition] — 分区发现
- `count_rows(tables)` → Dict[str, int] — 行数统计

---

## 4. 测试计划

**文件：** `tests/test_asset_visualization.py`

| 测试 | 预期 |
|------|------|
| `test_system_connection_status` | 枚举 5 个系统（SAP-ERP/PI-System/SCADA/LIMS/OA），每系统含 name/status/record_count |
| `test_asset_catalog_returns_tables` | 返回字段：table_name, chinese_name, owner, row_count, size_mb, partition_field |
| `test_asset_catalog_covers_all_systems` | SAP-ERP 6张表、PI-System tags、LIMS samples、OA contract+doc_flow、SCADA equipment_status |
| `test_quality_score_card` | 每系统有 4 项评分（完整性/一致性/时效性/准确性），范围 0-100 |
| `test_security_classification` | 每系统/表有分级：核心/重要/一般 |

**文件：** `tests/test_data_profiling.py`

| 测试 | 预期 |
|------|------|
| `test_parquet_file_readable` | pandas 可读取 data/historical 下的 Parquet 文件 |
| `test_table_row_count` | 每表行数 > 0 |
| `test_partition_discovery` | 可发现分区字段和分区值 |

---

## 5. 端到端验证

```bash
# 运行测试
uv run pytest tests/ -v

# DataHub 前端验证
open http://localhost:23310
# 登录后应看到资产目录页面

# Python 端到端
uv run python -c "
from dg_platform.datahub_client import get_client
client = get_client()
print('GMS alive:', client.is_alive())
catalog = client.list_datasets()
print('Datasets in DataHub:', len(catalog))
"
```

---

## 6. 当前状态

**基础设施层（100%）**
- [x] docker-compose.datahub.yml 完整可运行（Kafka/KAFKA_SCHEMAREGISTRY_URL/user root/认证关闭）
- [x] datahub-upgrade 全部 27/27 步骤完成
- [x] datahub-gms + datahub-frontend 健康运行
- [x] Python `ingest_metadata` 端到端成功（OpenAPI v3 格式）

**应用层（100%）**
- [x] `asset_visualizer.py` 实现（4 个核心函数）
- [x] `data_profiler.py` 实现（3 个核心函数）
- [x] 测试 41/41 全部通过
- [x] 端到端验证：5 系统、12 张表全部上报 DataHub 成功

**待优化**
- [ ] `list_datasets()` GraphQL 查询需适配 v1.3.0（searchAcrossEntities 参数差异，ES 索引异步问题）
- [ ] SCADA 无历史数据，`status=unknown`（正常行为）
