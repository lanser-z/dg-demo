# 模块八实施步骤：DataHub 生产接入

> 对应 `docs/Background.md` § 6.8。
> 目标：从 Phase 1 的「手工直写 OpenSearch」升级为「Kafka 事件流 → GMS → OpenSearch 自动同步」，实现 DataHub 元数据的自动化接入。

---

## 0. DataHub 接入模式总览

### 0.1 Phase 1 vs Phase 2

| 维度 | Phase 1（当前） | Phase 2（升级后） |
|------|---------------|-----------------|
| 接入方式 | `scripts/direct_es_bulk.py` 直接 bulk 写入 OpenSearch | GMS REST API + Kafka 事件流（DataHub actions 服务消费） |
| 新表注册 | 手动跑 `emit_browsepaths.py` | Parquet 文件落地 → Kafka 事件 → DataHub 自动发现 |
| 元数据更新 | 手动跑 `emit_browsepaths.py` | Kafka CDC 事件驱动，无需人工干预 |
| 资产一致性 | ES 和 MySQL 可能短暂不一致 | 最终一致（GMS 为唯一写入路径） |
| 延迟 | 依赖人工触发 | 分钟级自动同步 |

### 0.2 为什么需要 Phase 2 升级

Phase 1 手工模式的痛点：

1. **新表需要人工注册**：每次新增 Parquet 文件，需要手动跑 `emit_browsepaths.py`
2. **元数据更新滞后**：源数据更新后，DataHub UI 不自动刷新
3. **ES 和 GMS 不一致**：`direct_es_bulk.py` 绕过 GMS，OpenSearch 和 MySQL 数据可能短暂不一致
4. **无法规模化**：5 个系统 × N 张表，手工模式无法支撑长期运营

---

## 1. DataHub 架构解析

### 1.1 DataHub 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                     DataHub 架构                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐ │
│  │  GMS      │◄───│  MySQL   │    │  OpenSearch      │ │
│  │ (Java)    │    │ (存储元数据)│    │  (搜索+UI渲染)    │ │
│  └────┬─────┘    └──────────┘    └────────▲─────────┘ │
│       │                                      │         │
│       │  REST API 写入                        │ 读取     │
│       │  + Kafka 事件消费                    └─────────┘ │
│       │                                        │         │
│  ┌────▼────────────────────────────────────────────┐   │
│  │              datahub-actions 服务               │   │
│  │   (Kafka Consumer → GMS REST → OpenSearch)    │   │
│  └────────────────────────────────────────────────┘   │
│       ▲                                               │
│       │ Kafka Topic                                 │
│  ┌────┴─────┐                                        │
│  │  Kafka    │  ← 变更事件（dataset created/updated）│
│  └───────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

### 1.2 数据写入路径对比

**Phase 1（手工模式）**：
```
scripts/direct_es_bulk.py
       │
       │ 直接 Bulk API
       ▼
  OpenSearch
  (绕过 GMS)
```

**Phase 2（Kafka 事件流）**：
```
源数据变更
       │
       ▼
  Kafka Topic (datahub-event)
       │
       ▼
  datahub-actions 服务
       │
       ├──► GMS REST API → MySQL（元数据存储）
       │
       └──► OpenSearch 索引 → UI 渲染
```

### 1.3 Kafka 事件格式

DataHub 产出的 Kafka 事件示例：

```json
{
  "eventType": "ENTITY_CHANGE",
  "entityType": "dataset",
  "entityUrn": "urn:li:dataset:(urn:li:dataPlatform:delta-lake,data/lakehouse/dwd/sap_erp/kna1,PROD)",
  "changeType": "CREATE",
  "aspectName": "browsePaths",
  "auditHeader": {
    "time": 1719120000000
  }
}
```

---

## 2. 技术实现

### 2.1 datahub-actions 服务配置

`datahub-actions` 是 DataHub 的事件消费服务，配置文件示例：

```yaml
# datahub-actions.yml
version: 1
source:
  type: kafka
  config:
    bootstrapServers: "localhost:9092"
    topic: "MetadataChangeLog_v4"
    groupId: "datahub-actions-gms"
    # 从 latest 开始消费（生产环境建议 earliest）
    autoOffsetReset: "latest"

pipeline:
  - name: datahub-gms-sync
    filter:
      event:
        types:
          - "ENTITY_CHANGE"
          - "METADATA_CHANGE_LOG"
    action:
      type: "rest"
      config:
        apiBaseUrl: "http://localhost:8080"
        # 同步到 GMS MySQL
```

### 2.2 Metadata Ingestion 连接器

DataHub 支持通过 ingestion connector 主动拉取元数据：

```yaml
# datahub ingestion recipe
source:
  type: delta-lake
  config:
    basePath: "/home/szs/Playground/dg-demo/data/lakehouse"
    platform: "delta-lake"
    fileExtensions:
      - ".parquet"

sink:
  type: "datahub-rest"
  config:
    server: "http://localhost:8080"
```

### 2.3 REST API 直连模式

不依赖 Kafka 时，可以通过 GMS REST API 写入：

```python
import requests

# 注册 dataset
response = requests.post(
    "http://localhost:8080/entities",
    headers={"Content-Type": "application/json"},
    json={
        "entityType": "DATASET",
        "aspect": {
            "browsePaths": {
                "paths": ["prod/lakehouse/dwd/sap_erp/kna1"]
            }
        }
    }
)
```

---

## 3. 教学 notebook

`notebook/module8.ipynb` 按以下结构组织：

| 步骤 | 内容 | 调用的函数 / 命令 |
|------|------|-----------------|
| 痛点故事 | Phase 1 手工模式的问题：需要人工跑脚本、ES/GMS 不一致 | — |
| 步骤 1 | DataHub 架构解析：GMS / MySQL / OpenSearch / Kafka 的关系 | 架构图 |
| 步骤 2 | Phase 1 手工模式演示：`direct_es_bulk.py` 写入 ES | `direct_es_bulk.py` |
| 步骤 3 | Phase 2 Kafka 事件流模式：`datahub-actions` 配置解析 | 配置展示 |
| 步骤 4 | REST API 直连模式：GMS API 写入示例 | Python requests |
| 诚实声明 | 当前 Demo 环境无真实 Kafka，Phase 2 为架构演示 | — |

**设计原则**：
- 每个 code cell ≤15 行
- 重点在架构理解，不在实际跑通 Kafka（需要 docker-compose 环境）
- 诚实声明 Demo 无法模拟真实的 Kafka 集群

---

## 4. 执行流程

```bash
# step 1: 确保 DataHub 启动
docker-compose -f datahub-quickstart.yml up -d

# step 2: 验证 GMS 可访问
curl http://localhost:8080/health 2>/dev/null | jq .

# step 3: 打开教学 notebook
jupyter notebook notebook/module8.ipynb

# step 4: 手工模式演示（Phase 1）
uv run python scripts/direct_es_bulk.py --dry-run

# step 5: Kafka 事件流模式（Phase 2，架构演示）
# 实际运行需要 docker-compose 环境，notebook 中展示配置和预期行为
```

---

## 5. 当前状态

**Phase 1 手工接入（100%）**
- [x] `scripts/direct_es_bulk.py`：直接 bulk 写入 OpenSearch
- [x] `scripts/emit_browsepaths.py`：批量注册 browse paths
- [x] `notebook/datahub_setup.ipynb`：DataHub 接入演示

**Phase 2 Kafka 事件流接入（架构设计）**
- [ ] `datahub-actions.yml`：Kafka consumer 配置
- [ ] ingestion recipe：`delta-lake` source → `datahub-rest` sink
- [ ] REST API 直连模式：GMS API 写入示例
- [ ] `notebook/module8.ipynb`：Phase 2 架构演示

**Docker Compose 环境**
- [ ] `datahub-quickstart.yml`：完整 DataHub 栈（GMS + MySQL + Kafka + OpenSearch + datahub-actions）
- [ ] Kafka topic 配置：`MetadataChangeLog_v4`
- [ ] 验证：新 Parquet 写入后 30s 内 DataHub UI 自动出现

---

## 6. 与其他模块的依赖

```
模块一（数据资产可视化）
       │ DataHub 资产目录
       ▼
模块八（DataHub 生产接入）
       │
       ├─► 模块九（自动血缘采集）：依赖 datahub-actions 服务
       │
       └─► 模块十（定时质量监控）：依赖 Kafka 事件流

模块八是 Phase 2 的基础设施，
其他 Phase 2 模块依赖它提供的自动化能力。
```

---

## 7. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| `curl localhost:8080/health` 无响应 | DataHub GMS 未启动 | `docker-compose -f datahub-quickstart.yml ps` |
| `direct_es_bulk.py` 报错 403 | OpenSearch 认证问题 | 检查 `OPENSEARCH_PASSWORD` 环境变量 |
| Kafka topic 无消息 | datahub-actions 未启动或 offset 错乱 | 检查 consumer group offset |
| UI 上 dataset 不出现 | ingestion 任务失败 | 查看 DataHub GMS 日志 |
| browsePaths 为空 | `emit_browsepaths.py` 未跑 | 手动触发 `uv run python scripts/emit_browsepaths.py` |

---

## 8. 快速命令汇总

```bash
# DataHub 启动（完整栈）
docker-compose -f datahub-quickstart.yml up -d

# 验证 GMS 健康
curl http://localhost:8080/ping

# 查看 Kafka topics
docker-compose -f datahub-quickstart.yml exec kafka kafka-topics --list

# 查看 datahub-actions 日志
docker-compose -f datahub-quickstart.yml logs -f datahub-actions

# 手工模式：直写 ES（Phase 1）
uv run python scripts/direct_es_bulk.py --dry-run

# 手工模式：注册 browse paths
uv run python scripts/emit_browsepaths.py

# 教学 notebook
jupyter notebook notebook/module8.ipynb
```
