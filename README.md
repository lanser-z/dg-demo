# A 公司煤炭数据治理 Demo

模拟 5 个异构系统（SAP-ERP / PI-System / LIMS / OA / SCADA）的数据治理全流程演示环境。

业务背景见 [docs/Background.md](docs/Background.md)，技术选型见 [docs/Design.md](docs/Design.md)，安装与服务清单见 [docs/Deps.md](docs/Deps.md)。

---

## 环境前置

- Python ≥ 3.10 + [uv](https://docs.astral.sh/uv/)（包管理）
- Docker + Docker Compose（仅路径 B 需要）
- 内存 ≥ 16 GB
- 磁盘 ≥ 5 GB（历史数据 + Delta Lake 占 ~3 GB）

```bash
cd /home/szs/Playground/dg-demo
uv sync
```

如果 `uv sync` 之后包缺失，参考 [pyproject.toml](pyproject.toml) 顶部注释。

启动 DataHub：

```bash
./startup.sh
```

约 2~3 分钟，验证：

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep datahub
open http://localhost:29002   # DataHub UI
```

---

## 两条学习路径

| 维度 | 路径 A：Pandas 快速通道 | 路径 B：完整演示 |
|---|---|---|
| 上手时间 | 5 分钟 | 30~40 分钟 |
| 依赖服务 | 仅 Python | DataHub 全家桶（7 个容器） |
| 覆盖模块 | step0 + module1~4 | step0 + datahub_setup + module1~8 |
| 适合 | 先看数据长什么样 / 试清洗规则 | 完整跑通 5 系统数据治理 |
| 数据源 | `data/historical/*.parquet` | + DataHub UI + Delta Lake |

### 路径 A：Pandas 快速通道（5~10 分钟）

不依赖任何 Docker 服务，直接用 pandas 读历史 Parquet 跑教学 notebook。

```bash
cd /home/szs/Playground/dg-demo
uv run jupyter lab notebook/
```

按顺序打开：

| 顺序 | Notebook | 内容 |
|---|---|---|
| 1 | `step0.ipynb` | 5 分钟串讲 + 数据集总览 |
| 2 | `module1.ipynb` | 资产可视化 + DWD 入湖 |
| 3 | `module2.ipynb` | Great Expectations 质量检测 |
| 4 | `module4.ipynb` | ODS→DWD 清洗演示 |

完成路径 A 后想看血缘 / DWA 宽表，进入路径 B。

### 路径 B：完整演示通道（30~40 分钟）

依赖 DataHub 全家桶（Kafka + MySQL + OpenSearch + GMS + Frontend + Actions）。`./startup.sh` 启动后 7 个服务全部 healthy 即可。

```bash
cd /home/szs/Playground/dg-demo
./startup.sh                        # 启动 DataHub
uv run jupyter lab notebook/        # 启动 Jupyter
```

浏览器先开 http://localhost:29002 验证 UI 可达，搜索 `sap_erp` 应能看到 6 张表。

按顺序打开：

| 顺序 | Notebook | 配套服务 | 内容 |
|---|---|---|---|
| 0 | `datahub_setup.ipynb` | DataHub | 验证 GMS + OpenSearch 连通性 |
| 1 | `step0.ipynb` | — | 5 分钟串讲 |
| 2 | `module1.ipynb` | DataHub + Lakehouse | 资产可视化 + DWD 入湖 |
| 3 | `module2.ipynb` | DataHub (GE) | 质量检测 + 评分卡 |
| 4 | `module3.ipynb` | DataHub (Lineage) | 5 条手工血缘 |
| 5 | `module4.ipynb` | Lakehouse | 清洗演示（去空/去重/规范化） |
| 6 | `module5.ipynb` | Lakehouse | DWA 宽表 + DuckDB |
| 7 | `module6.ipynb` | DuckDB | 4 个即席查询场景 |
| 8 | `module7.ipynb` | Lakehouse | 矿井/客户/物料维表 |
| 9 | `module8.ipynb` | DataHub (GMS REST + Kafka) | 生产级元数据接入 |
| 10 | `module9.ipynb` | DataHub (OpenLineage) | 自动血缘采集（auto + manual 双通道对比） |
| 11 | `module10.ipynb` | APScheduler + SQLite | 定时质量监控（Checkpoint + 阈值告警 + 趋势图） |
| 12 | `module11.ipynb` | DataHub (dwd platform) | 主题域 DWD 重组（dual-write + `dwd` 自定义 platform + 6 张新表 datasetKey） |
| 13 | `module12.ipynb` | DuckDB OLAP | 跨系统 DWA（4 表 JOIN 宽表 + 4 个分析场景 SQL） |

---

## 验证清单

启动后跑一遍：

```bash
# 1. Python 环境
uv run python -c "
import duckdb, yaml, pandas, pyarrow, deltalake
from datahub.emitter.rest_emitter import DatahubRestEmitter
print('✅ 核心依赖 OK')
"

# 2. DataHub 服务
curl -s http://localhost:28080/health       # GMS
curl -s "http://localhost:29200/_cat/indices?v" | head -5   # OpenSearch
open http://localhost:29002                  # Frontend

# 3. 教学数据
ls data/historical/                          # 5 系统 Parquet
ls data/lakehouse/{ods,dwd,dwa}/             # 三层湖仓
```

预期看到：

- 5 个容器 healthy（gms / frontend / opensearch / mysql / kafka）
- 12 个 dataset 索引在 OpenSearch 中
- DataHub UI 搜索 `sap_erp` 返回 6 张表

---

## 常见问题

**Q: `uv sync` 卸载了一堆包怎么办？**

A: 参考 [pyproject.toml](pyproject.toml) 当前声明。`uv sync` 只会保留显式声明的依赖。

**Q: startup.sh 启动了但端口 29002 访问不了？**

A: 检查 GMS 是否 healthy：`docker ps | grep datahub-gms`。如果 unhealthy 看 `docker logs datahub-datahub-gms-quickstart-1 --tail 50`。

**Q: 路径 A 和路径 B 都需要重启环境吗？**

A: 不需要。两个路径共享 `data/historical/` 和 `data/lakehouse/`，只是 DataHub 服务按需启停。

**Q: DataHub 启动很慢？**

A: 首次启动 system-update 一次性任务需 2~3 分钟初始化索引。后续启动 < 30 秒。

**Q: Neo4j 怎么没起来？**

A: 当前 `datahub-quickstart.yml` 用 OpenSearch 兼任图谱后端（`GRAPH_SERVICE_IMPL: elasticsearch`），不需要 Neo4j。

---

## 进一步学习

- 模块详细讲解：[docs/Module1.md](docs/Module1.md) ~ [docs/Module11.md](docs/Module11.md)
- 5 分钟演示剧本：[docs/Demo.md](docs/Demo.md)
- 已完成与待办变更：[openspec/specs](openspec/specs/)
