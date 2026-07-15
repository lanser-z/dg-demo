# 模块十一实施步骤：主题域 DWD 重组

> **归属**：Background §6.11 / Phase 2
> **演示时长**：10 分钟
> **新增依赖**：无（复用 `deltalake`、`acryl-datahub`、`duckdb`、`playwright`）
> **新增产物**：`scripts/restructure_dwd.py`、`scripts/register_subject_dwd.py`、`notebook/module11.ipynb`、`docs/Module11.md`、`data/lakehouse/dwd/{sales,production,coal_quality,finance}/`

---

## 1. 模块概述

### 1.1 教学目标

把 DWD 层从「按源系统分区」（`dwd/sap_erp/`、`dwd/pi_system/`、`dwd/lims/`、`dwd/oa/`）升级为「按业务主题分区」（`dwd/sales/`、`dwd/production/`、`dwd/coal_quality/`、`dwd/finance/`），让同主题跨系统数据自然落在同目录下，**dual-write 模式保留旧 system-分区**。

### 1.2 与 module1 / module4 的关系

| 维度 | module1 / module4 (Phase 1) | module11 (Phase 2 / 6.11) |
|------|-----------------------------|---------------------------|
| DWD 组织 | `dwd/sap_erp/dwd_vbak`（按系统分） | `dwd/sales/dwd_vbak`（按主题分） |
| 维度表 | `dwd/_dimensions/` 不动 | `dwd/_dimensions/` 仍不动（共享维度全局可用） |
| DWA 上游 | 读 system-分区 | **仍读 system-分区**（6.12 才切） |
| DataHub 平台 | `sap_erp` / `pi_system` / `lims` / `oa` | 新增 `dwd` 自定义 platform，6 张新表按 `dwd.{subject}.{table}` 命名 |
| 存储成本 | 1× | 2×（dual-write 阶段）；6.12 切流后回 1× |

### 1.3 关键约束

- **表名保持不变**（`dwd_vbak` 等保留原名），**只换目录**。`dwa_*.py` 等下游脚本不需要改。
- **维度表不参与重组**：`dim_mine` / `dim_customer` / `dim_material` 保留在 `dwd/_dimensions/`，因为它们是跨主题共享的。
- **dual-write 模式**：旧 system-分区完全不动（演示阶段零风险，学员可对比新旧布局）。

---

## 2. 主题目录结构

### 2.1 新布局（4 主题 / 6 表）

```
data/lakehouse/dwd/
├── sales/                          ← 主题：销售
│   ├── dwd_vbak/                   ← SAP 销售订单抬头
│   ├── dwd_vbap/                   ← SAP 销售订单行项目
│   └── dwd_kna1/                   ← SAP 客户主数据
├── production/                     ← 主题：生产
│   └── dwd_tags/                   ← PI System 时序标签
├── coal_quality/                   ← 主题：煤质
│   └── dwd_samples/                ← LIMS 样品化验
├── finance/                        ← 主题：财务
│   └── dwd_doc_flow/               ← OA 文档流
└── _dimensions/                    ← 全局共享维度（不动）
    ├── dim_mine/                   ← 矿井维表
    ├── dim_customer/               ← 客户维表
    └── dim_material/               ← 物料维表
```

### 2.2 旧布局（保留，dual-write 阶段）

```
data/lakehouse/dwd/
├── sap_erp/                        ← 系统：SAP
│   ├── dwd_vbak/                   (保留)
│   ├── dwd_vbap/                   (保留)
│   └── dwd_kna1/                   (保留)
├── pi_system/                      ← 系统：PI
│   └── dwd_tags/                   (保留)
├── lims/                           ← 系统：LIMS
│   └── dwd_samples/                (保留)
├── oa/                             ← 系统：OA
│   └── dwd_doc_flow/               (保留)
└── _dimensions/                    (保留)
```

### 2.3 表-主题映射（canonical）

| 旧 system-分区 | 新 subject-分区 | 源系统 |
|----------------|-----------------|--------|
| `dwd/sap_erp/dwd_vbak`     | `dwd/sales/dwd_vbak`     | SAP-ERP |
| `dwd/sap_erp/dwd_vbap`     | `dwd/sales/dwd_vbap`     | SAP-ERP |
| `dwd/sap_erp/dwd_kna1`     | `dwd/sales/dwd_kna1`     | SAP-ERP |
| `dwd/pi_system/dwd_tags`   | `dwd/production/dwd_tags`   | PI-System |
| `dwd/lims/dwd_samples`     | `dwd/coal_quality/dwd_samples` | LIMS |
| `dwd/oa/dwd_doc_flow`      | `dwd/finance/dwd_doc_flow`    | OA |

### 2.4 为什么维度表保留在 `_dimensions/`

维度表（`dim_mine` / `dim_customer` / `dim_material`）是**跨域共享**的：

- `dim_mine` 被 `production`（`dwd_tags` 用 `MINE_CODE`）、`coal_quality`（`dwd_samples` 用 `MINE_CODE`）、`sales`（`dwd_vbak` 间接通过 KNA1 + 矿井代码）**共同引用**
- 把 `dim_mine` 放进 `dwd/sales/` 会导致跨域引用；放 `_dimensions/` 一处管理更清晰

Phase 1 / 6.7 已确立维度表独立于业务域；6.11 维持这一约束。

---

## 3. dual-write 模式

### 3.1 入口

```bash
uv run python scripts/restructure_dwd.py             # 默认 dual 模式
uv run python scripts/restructure_dwd.py --dry-run   # 仅打印计划
uv run python scripts/restructure_dwd.py --mode=replace  # 删旧 system-分区（6.12 才用）
```

### 3.2 内部流程

1. 读 `dwd/{system}/{table}/` 的 Delta Lake 表（`deltalake.DeltaTable`）
2. 写 `dwd/{subject}/{table}/` 的 Delta Lake 表（`deltalake.write_deltalake(mode="overwrite")`）
3. 旧 system-分区**完全不动**（无 `rm`、无 rename）
4. 表名不变（`dwd_vbak` 仍是 `dwd_vbak`）

### 3.3 存储成本

- dual-write 阶段：约 2× 存储（~1 GB DWD × 2 = ~2 GB）
- 演示阶段可接受；生产切流后（6.12 范围）用 `--mode=replace` 删旧目录回到 1×

### 3.4 验证：行数严格一致

跑过脚本后用 DuckDB 验证：

```python
import duckdb
con = duckdb.connect()
old = con.sql("SELECT count(*) FROM delta_scan('data/lakehouse/dwd/sap_erp/dwd_vbak')").fetchone()[0]
new = con.sql("SELECT count(*) FROM delta_scan('data/lakehouse/dwd/sales/dwd_vbak')").fetchone()[0]
assert old == new  # 2,999,312 == 2,999,312
```

6 张表均验证通过（详见 `notebook/module11.ipynb` cell 2）。

---

## 4. 与 6.12 的关系

### 4.1 6.11 范围内（本次变更）

- ✅ 4 个主题目录重组（sales / production / coal_quality / finance）
- ✅ dual-write 保留旧 system-分区
- ✅ DataHub 注册 `dwd` 自定义 platform + 6 张新表的 `datasetKey` + `datasetProperties` aspect
- ✅ `_dimensions/` 保留不动
- ✅ DWA 宽表仍读 system-分区（**不**切流）

### 4.2 6.12 范围（后续变更）

- DWA 宽表上游切换到新主题-分区（如 `dwa_sales_daily` 从 `dwd/sap_erp/dwd_vbak` 切到 `dwd/sales/dwd_vbak`）
- 跨主题 JOIN（产销 4 表 JOIN：sales × production × coal_quality × finance）
- OLAP 物化视图（ClickHouse / Doris）
- 切流稳定后用 `restructure_dwd.py --mode=replace` 删旧 system-分区，存储从 2× 回到 1×

### 4.3 6.11 不做跨主题 JOIN

跨主题 JOIN（特别是 sales × coal_quality 跨系统业务关联键）属于 6.12 范围。6.11 只做"目录重组 + DataHub 主题视图"演示，不引入新 JOIN 逻辑。

---

## 5. DataHub 集成

### 5.1 Platform 注册

```python
from datahub.metadata.schema_classes import DataPlatformInfoClass, PlatformTypeClass
from datahub.utilities.urns.data_platform_urn import DataPlatformUrn

platform_urn = DataPlatformUrn(platform_name="dwd")
aspect = DataPlatformInfoClass(
    name="dwd",
    type=PlatformTypeClass.OTHERS,
    datasetNameDelimiter=".",
    displayName="DWD",
    logoUrl="...",
)
emitter.emit(MetadataChangeProposalWrapper(entityUrn=str(platform_urn), aspect=aspect))
```

注册后通过 `curl http://localhost:28080/aspects/urn:li:dataPlatform:dwd?aspect=dataPlatformInfo&version=0` 验证。

### 5.2 Dataset 注册（6 张表）

每张新主题表的 URN 格式：

```
urn:li:dataset:(urn:li:dataPlatform:dwd,dwd.{subject}.{table},PROD)
```

例：`urn:li:dataset:(urn:li:dataPlatform:dwd,dwd.sales.dwd_vbak,PROD)`

注册 `DatasetKeyClass`（DataHub GMS 必备）+ `DatasetPropertiesClass`（带 `customProperties` 标 layer/subject/table/lake_path）。

### 5.3 DataHub UI 树形浏览

注册后 DataHub UI `Browse` 页面显示：

```
📁 dwd
  📁 sales
    📄 dwd.sales.dwd_vbak
    📄 dwd.sales.dwd_vbap
    📄 dwd.sales.dwd_kna1
  📁 production
    📄 dwd.production.dwd_tags
  📁 coal_quality
    📄 dwd.coal_quality.dwd_samples
  📁 finance
    📄 dwd.finance.dwd_doc_flow
```

> 截图见 `notebook/step_images/module11_subject_dwd.png`。

### 5.4 与 lineage 边共存

旧 system-分区表的 lineage（6.9 阶段 emit 的 dataJobInputOutput 边）保留不变；新主题表通过新 URN 独立索引。DataHub graph 服务按 `(dataset, upstream)` 唯一键合并，UI 不重复显示。

---

## 6. 文件清单

```
dg-demo/
├── scripts/
│   ├── restructure_dwd.py                  # 新增：dual-write ETL
│   └── register_subject_dwd.py             # 新增：DataHub 平台 + 6 张表注册
├── notebook/
│   ├── module11.ipynb                      # 新增：3 cells 教学
│   └── step_images/
│       └── module11_subject_dwd.png        # 新增：DataHub UI 截图
├── docs/
│   ├── Module11.md                         # 新增：本文件
│   └── Background.md §6.11                 # 状态：已上线
└── data/lakehouse/dwd/
    ├── sales/{dwd_vbak,dwd_vbap,dwd_kna1}/  # 新增（dual-write）
    ├── production/dwd_tags/                # 新增（dual-write）
    ├── coal_quality/dwd_samples/           # 新增（dual-write）
    └── finance/dwd_doc_flow/               # 新增（dual-write）
```

---

## 7. CLI 用法汇总

```bash
# ── 1. dual-write (教学 / 演示) ──
uv run python scripts/restructure_dwd.py
# 6/6 表已写入新主题目录，旧 system-分区保留

# ── dry-run (CI 验证) ──
uv run python scripts/restructure_dwd.py --dry-run
# 仅打印「将写入 X 行到 dwd/sales/dwd_vbak」

# ── 2. DataHub 注册 ──
uv run python scripts/register_subject_dwd.py
# 注册 dwd platform + 6 张新表 + 验证 datasetKey aspect

# ── 3. notebook 教学 ──
cd notebook/
uv run jupyter lab module11.ipynb
# cell 1: 目录结构对比
# cell 2: DuckDB 行数严格一致
# cell 3: Playwright 截图 DataHub UI

# ── 4. 切流 (6.12 才用) ──
uv run python scripts/restructure_dwd.py --mode=replace
# 删旧 system-分区, 新主题目录改名 (DWA 已切流后才能用)
```

---

## 8. 故障排查

| 症状 | 原因 | 修复 |
|------|------|------|
| `deltalake.DeltaTable` 读旧表报 schema error | 旧表无 `_delta_log` 或损坏 | 重新跑 `ingest_to_deltalake.py --layer dwd` |
| `write_deltalake` 报 `Path does not exist` | 目标目录父路径未建 | `deltalake.write_deltalake` 自动创建，无需 os.makedirs |
| DataHub `datasetKey` aspect 查不到 | GMS Kafka 异步落库延迟 | 脚本已 sleep(5)，如仍查不到再 sleep(5) |
| 旧 system-分区被误删 | 误用 `--mode=replace` | dual-write 模式默认安全；replace 仅 6.12 用 |
| `_dimensions/` 消失 | 误把 dim_* 加入 SUBJECT_MAP | 不会：SUBJECT_MAP 硬编码 6 张表，dim_* 不会被处理 |
| `playwright` 报 "asyncio loop" 错误 | Jupyter kernel 在 asyncio 事件循环 | notebook 用 `async_playwright` + `await`（非 sync API） |

---

## 9. 验证清单

```bash
# 1. 依赖（pyproject.toml 已有，无需新增）
uv run python -c "import deltalake, duckdb, datahub, playwright; print('✅ 核心依赖 OK')"

# 2. dual-write 6/6
uv run python scripts/restructure_dwd.py
# 预期：6/6 表写入成功，_dimensions 保留

# 3. DataHub 验证
uv run python scripts/register_subject_dwd.py
# 预期：6/6 datasetKey aspect 验证通过

# 4. GMS 验证
curl -s "http://localhost:28080/aspects/urn%3Ali%3Adataset%3A%28urn%3Ali%3AdataPlatform%3Adwd%2Cdwd.sales.dwd_vbak%2CPROD%29?aspect=datasetKey&version=0" \
  -u datahub:datahub
# 预期：HTTP 200 + 包含 "name": "dwd.sales.dwd_vbak"

# 5. OpenSearch 验证（6 张新主题表索引）
curl -s -X POST "http://localhost:29200/datasetindex_v2/_search" \
  -H "Content-Type: application/json" \
  -d '{"size":20,"query":{"term":{"platform":"urn:li:dataPlatform:dwd"}}}'
# 预期：至少 6 条 dwd.{subject}.{table} 记录

# 6. Notebook 3 cells 全部执行
cd notebook/
uv run jupyter nbconvert --to notebook --execute module11.ipynb --output /tmp/check.ipynb
# 预期：成功，3 cells 输出 6/6 行数一致 + PNG 截图 ~150KB
```

---

## 10. 演进路径（Phase 3 写入但不实现）

1. **OLAP 物化视图**：6.12 跨主题 JOIN 时同步设计
2. **切流自动化**：用 Airflow DAG 编排 DWA 上下游切换，6.12 完成后用 `--mode=replace` 删旧
3. **DataHub 业务标签**：6.12 加 `glossaryTerms` 标注（销售/生产/煤质/财务 term 节点）
4. **多租户 subject 隔离**：跨子公司时按 subject 分 RBAC 权限
