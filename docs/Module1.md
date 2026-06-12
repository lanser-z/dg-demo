# 模块一实施步骤：数据资产可视化

---

## 1. Docker 服务

### 1.1 拉取镜像（首次运行前）

```bash
# 提前拉取，避免启动时超时
docker pull acryldata/datahub-gms:${DATAHUB_VERSION:-v1.6.0} &
docker pull acryldata/datahub-frontend-react:${DATAHUB_VERSION:-v1.6.0} &
docker pull acryldata/datahub-actions:${DATAHUB_VERSION:-v1.6.0} &
docker pull acryldata/datahub-upgrade:${DATAHUB_VERSION:-v1.6.0} &
docker pull opensearchproject/opensearch:2.19.3 &
docker pull mysql:8.2 &
docker pull confluentinc/cp-kafka:8.0.0 &
wait
```

> **架构变更**（`bb03262` 提交起）：去掉了 Neo4j（`27474` / `27687` 端口停用）。
> 血缘录入现在只用 GMS REST API，不再做 Neo4j fallback。

### 1.2 一键启动

```bash
cd /home/szs/Playground/dg-demo
docker compose -f datahub-quickstart.yml up -d
```

**关键经验（踩坑记录）：**

| 问题 | 原因 | 修复 |
|------|------|------|
| Delta Lake 写入 MinIO S3 超时 | MinIO 无认证时 S3 scheme 被拒绝 | 改用本地文件系统存储（`data/lakehouse/`，不依赖对象存储） |
| Great Expectations v1.x API 变更 | PandasDataset/expectation_type 参数名变化 | 使用轻量 GE 风格规则（pandas 执行）—— 见 `src/dg_education/quality.py` |
| ~~Neo4j healthcheck 永远 unhealthy~~ | （已删除 Neo4j 容器，此问题不再适用） | 改用 GMS REST API 写血缘（`scripts/emit_lineage.py` 不再尝试 Neo4j fallback） |
| ~~GMS /aspects 返回 400~~ | （实测 GMS 上游 lineage 可正常写入） | `emit_lineage.py` 当前只走 GMS REST |

**各服务端口：**

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 Web UI | 29002 | 浏览器访问 |
| GMS API | 28080 | 后端接口 |
| OpenSearch | 29200 | 搜索索引 |
| MySQL | 23306 | 元数据存储 |
| Kafka | 29092 | 消息队列 |

**启动顺序（compose 自动处理）：**

```
kafka-broker (healthy) ─┬─→ mysql (healthy)
                         └─→ opensearch (healthy)
                                │
                         system-update-quickstart (一次性 setup 任务)
                                │
                         datahub-gms-quickstart
                                │
                         frontend-quickstart
                                │
                         datahub-actions-quickstart
```

**手动验证：**

```bash
# 检查所有服务状态
docker ps --format "table {{.Names}}\t{{.Status}}" | grep datahub

# 基础服务验证
curl -s http://localhost:29200/_cluster/health?pretty  # OpenSearch
curl -s http://localhost:28080/health                  # DataHub GMS
curl -s http://localhost:29002                          # DataHub Frontend

# MySQL schema 验证
docker exec datahub-mysql mysql -u root -pdatahub -e "SHOW TABLES;" datahub
```

---

## 2. Python 依赖安装

```bash
uv sync
```

**核心依赖（pyproject.toml 中已有）：**
- `pandas>=2.0` — 数据处理
- `pyarrow>=14.0` — Parquet 读写
- `requests>=2.31` — HTTP 客户端
- `great-expectations>=0.18` — 数据质量规则引擎
- `deltalake>=0.12` — Delta Lake 读写

---

## 3. 数据资产上报

### 3.1 直接写入 OpenSearch（推荐演示用）

```bash
# 清除已有数据
uv run python -c "
import requests
ES_URL = 'http://localhost:29200'
r = requests.post(
    f'{ES_URL}/datasetindex_v2/_delete_by_query',
    json={'query': {'match_all': {}}},
    headers={'Content-Type': 'application/json'},
    timeout=30
)
print('Deleted:', r.json().get('deleted', 0))
"

# 重新上报
uv run python scripts/direct_es_bulk.py
```

`scripts/direct_es_bulk.py` 特点：
- 直接 bulk 写入 OpenSearch，不经过 GMS/MySQL
- 自动从 Parquet 文件读取行数/存储大小
- 支持全部 12 张表（含 scada/equipment_status）

### 3.2 通过 GMS REST API 写入 Aspect

```bash
uv run python scripts/emit_browsepaths.py
```

`scripts/emit_browsepaths.py` 特点：
- 通过 GMS `/aspects` REST 接口写入 browsePathsV2 + datasetProperties + ownership
- 写入 MySQL 元数据存储，触发索引同步
- 支持全部 12 张表的 Aspect 注册

### 3.3 验证 Browse 导航

```bash
uv run python scripts/check_browse.py
```

---

## 4. 数据资产录入现状

### 4.1 已录入的资产（12 张表）

| 平台 | 表名 | 说明 | Owner |
|------|------|------|--------|
| sap_erp | vbak | 销售订单抬头 | 销售部 |
| sap_erp | vbap | 销售订单行项目 | 销售部 |
| sap_erp | kna1 | 客户主数据 | 销售部 |
| sap_erp | likp | 交货单抬头 | 销售部 |
| sap_erp | lips | 交货单行项目 | 销售部 |
| sap_erp | mara | 物料主数据 | 销售部 |
| pi_system | tags | PI 时序标签数据 | 安全部 |
| lims | samples | 煤质化验样品 | 煤质中心 |
| oa | doc_flow | 文档流转记录 | 综合管理部 |
| oa | contract | 合同记录 | 综合管理部 |
| oa | meeting | 会议记录 | 综合管理部 |
| scada | equipment_status | 设备状态 | 安全部 |

### 4.2 验证资产是否在 DataHub 中

```bash
# 直接查 OpenSearch
curl -s "http://localhost:29200/datasetindex_v2/_search?size=20&_source=name,urn,platform" | \
  python3 -c "
import sys,json
d=json.load(sys.stdin)
for h in d.get('hits',{}).get('hits',[]):
    s=h['_source']
    print(s.get('platform',''), '/', s.get('name',''))
"
```

---

## 5. 当前状态

**基础设施层（100%）**
- [x] datahub-quickstart.yml 完整可运行（v1.6.0）
- [x] OpenSearch 2.19.3 作为搜索后端
- [x] MySQL 8.2 + Kafka 8.0.0 健康运行
- [x] Delta Lake 本地文件系统存储（无外部依赖）
- [x] 所有脚本端口已统一（28080/29200/23306）
- [x] 已移除 Neo4j 依赖（架构变更 bb03262）

**数据资产层（100%）**
- [x] 12 张数据表已录入 OpenSearch 索引
- [x] Browse 路径已写入
- [x] 所有脚本端口已统一为新端口
- [x] direct_es_bulk.py 重写（直接从 Parquet 读取统计）
- [x] emit_browsepaths.py 重写（纯 REST API）
- [x] check_browse.py 更新（验证 ES browsePath）

**数据入湖层（100%）**
- [x] Delta Lake 本地存储 data/lakehouse/
- [x] ODS 层：6 张 Parquet 入湖（sap_erp/pi_system/lims/oa）
- [x] DWD 层：6 张清洗表（去空值/去重复/规范化）
- [x] DWA 层：3 张汇总宽表（销售/告警/煤质）

**数据质量层（100%）**
- [x] Great Expectations 风格规则引擎（pandas 执行）
- [x] 4 大系统全覆盖（sap_erp / pi_system / lims / oa）
- [x] 评分等级 A/B/C/D 自动判定
- [x] JSON 格式质量报告输出

**血缘关系层（100%）**
- [x] lineage_recipe.yaml 血缘关系配置
- [x] emit_lineage.py 通过 GMS REST API 写血缘（`/aspects` upstreamLineage）
- [x] 4 条血缘边（sap_erp→lims / dwd清洗血缘 / pi_system→dwd）
- [x] 已移除 Neo4j fallback（架构变更 bb03262）

**分层建模层（100%）**
- [x] DuckDB OLAP 引擎计算 DWA 汇总
- [x] dwa_sales_daily — 每日销售汇总宽表
- [x] dwa_tag_alarm — 传感器告警汇总
- [x] dwa_coal_quality — 煤质月汇总

---

## 6. 教学演示流程

### 6.1 演示一：数据资产可视化（10分钟）

**教学目标**：展示接入 DataHub 后数据的全局可见性

```
Step 1: 启动服务
  docker compose -f datahub-quickstart.yml up -d
  → 确认 5 个服务全部 healthy

Step 2: 上报数据资产
  uv run python scripts/direct_es_bulk.py
  → 12 张表写入 OpenSearch

Step 3: 验证数据资产
  uv run python scripts/check_browse.py
  → 全部 ✅ browsePath 正确

Step 4: 打开 DataHub Frontend
  http://localhost:29002
  → 搜索 "lims" 或 "sap" 查看数据集卡片
```

**Before**：各系统数据分散，没有统一视图
**After**：DataHub 统一资产目录，5 个系统一览无余

---

### 6.2 演示二：数据质量检测（10分钟）

**教学目标**：用 Great Expectations 规则引擎发现数据质量问题

教学入口：`notebook/module1.ipynb` → 「步骤 2：质量评分卡 + 业务影响翻译」（含 4 系统覆盖率 + A/B/C/D 评分 + 业务影响白话翻译）。

如需 dev 单独跑：
```bash
uv run python scripts/run_great_expectations.py
```

**预期输出示例**：
```
📦 SAP_ERP
  ▶ vbak ... [D] 66.7% (4/6)
     🔴 FAIL: expect_column_values_to_not_be_null(KUNNR) → 12,688 异常 (2.54%)
     🔴 FAIL: expect_column_values_to_be_unique(VBELN) → 434 异常 (0.09%)

📦 PI_SYSTEM
  ▶ tags ... [D] 40.0% (2/5)
     🔴 FAIL: expect_column_values_to_be_between(status) → 2,518 异常 (0.50%)

📊 全局质量评分汇总
  sap_erp            73.3      C      73.3%        4
  pi_system          40.0      D      40.0%        3
  lims               71.4      C      71.4%        2
  oa                 75.0      C      75.0%        1
  平均                 64.9
```

**Before**：不知道数据质量如何
**After**：量化评分 + 失败规则详情，质量问题一目了然

**教学要点**：
- GE 规则定义语法（expect_column_values_to_not_be_null 等）
- 完整性 / 唯一性 / 准确性 / 一致性 四个维度
- 评分等级含义（A≥95 / B≥85 / C≥70 / D<70）

---

### 6.3 演示三：数据入湖 Delta Lake（10分钟）

**教学目标**：展示从原始 Parquet 到 Delta Lake 的完整入湖流程

```bash
# ODS 层入湖
uv run python scripts/ingest_to_deltalake.py --layer ods

# DWD 层清洗
uv run python scripts/ingest_to_deltalake.py --layer dwd

# DWA 层汇总
uv run python scripts/build_dwa_models.py --layer dwa
```

**ODS 层输出示例**：
```
▶ sap_erp/kna1
  行数: 15,000
  ✅ Delta Lake: 4 files, 1.8 MB

▶ pi_system/tags
  行数: 4,464,000
  ✅ Delta Lake: 2 files, 41.5 MB
```

**DWD 层输出示例**：
```
▶ sap_erp/dwd_vbak
  3,014,284 → 2,999,312 行 (剔除 14,972 行, 0.5%)
  ✅ Delta Lake: 4 files, 219.8 MB
```

**DWA 层输出示例**：
```
▶ dwa_sales_daily
  汇总天数: 30 天
  示例:
    sale_date  order_count  customer_count  total_amount
    2022-01-01            1               1     407663.73

▶ dwa_tag_alarm
  告警传感器数: 20
  TOP: M003_FACE_E_TEMP, M005_FACE_E_WAGAS...

▶ dwa_coal_quality
  汇总记录数: 50
  示例: 鄂尔多斯一号煤矿 / 2022-01 / 精煤 / avg_ash=28.69
```

**Before**：Parquet 散落在 data/historical/，无版本控制
**After**：Delta Lake 本地存储（data/lakehouse/），事务支持 + Schema 演进

**教学要点**：
- ODS（原始层）→ DWD（清洗层）→ DWA（汇总层）的分层理念
- Delta Lake ACID 事务 + Parquet 分区
- 数据清洗规则（去空值、去重复、范围校验）

---

### 6.4 演示四：数据血缘（10分钟）

**教学目标**：展示跨系统数据血缘关系和追溯能力

```bash
# 写入血缘到 GMS（upstreamLineage aspect）
uv run python scripts/emit_lineage.py
```

**预期输出**：
```
Processing: lims.samples
  [GMS] sap_erp.vbak --> lims.samples
  [GMS] sap_erp.vbap --> lims.samples

Processing: dwd.tags
  [GMS] pi_system.tags --> dwd.tags

Processing: dwd.vbak
  [GMS] sap_erp.vbak --> dwd.vbak

Processing: dwd.samples
  [GMS] lims.samples --> dwd.samples

LINEAGE GRAPH
  sap_erp.vbak --> lims.samples
  sap_erp.vbap --> lims.samples
  lims.samples --> dwd.samples
  sap_erp.vbak --> dwd.vbak
  pi_system.tags --> dwd.tags
```

**血缘关系图**：
```
  ┌─────────────┐       ┌─────────────┐
  │  sap_erp    │       │ pi_system   │
  │  vbak/vbap  │──────▶│   tags      │
  └──────┬──────┘       └──────┬──────┘
         │                      │
         │ KUNNR 关联           │ 清洗血缘
         ▼                     ▼
  ┌─────────────┐       ┌─────────────┐
  │   lims      │       │  dwd.tags   │
  │  samples    │──────▶│             │
  └──────┬──────┘       └─────────────┘
         │ 清洗血缘
         ▼
  ┌─────────────┐
  │ dwd_samples │
  └─────────────┘
```

**Before**：不知道数据从哪来、谁在用
**After**：DataHub GMS 的 `upstreamLineage` aspect 录入完整血缘链路，DataHub UI Lineage 标签页一键追溯

**教学要点**：
- upstreamLineage aspect 通过 GMS REST `/aspects` 写入
- 数据血缘的两个维度：业务血缘（跨系统 JOIN）vs 加工血缘（DWD/DWA 清洗）
- DataHub UI 的 Lineage 视图支持上下游追溯

---

## 7. 快速启动命令汇总

```bash
# 一键启动所有服务
cd /home/szs/Playground/dg-demo
docker compose -f datahub-quickstart.yml up -d

# 上报资产（dev 用，普通用户跳过；notebook 中会讲）
uv run python scripts/direct_es_bulk.py

# 教学入口（小白从这里开始）
jupyter notebook notebook/module1.ipynb

# 开发者上手报流程（小白跳过）
jupyter notebook notebook/datahub_setup.ipynb

# 质量检测（也可在 notebook 步骤 2 中跑）
uv run python scripts/run_great_expectations.py

# 入湖 Delta Lake
uv run python scripts/ingest_to_deltalake.py --layer ods
uv run python scripts/ingest_to_deltalake.py --layer dwd
uv run python scripts/build_dwa_models.py --layer dwa

# 血缘录入（通过 GMS upstreamLineage aspect）
uv run python scripts/emit_lineage.py

# 验证资产
uv run python scripts/check_browse.py
```
