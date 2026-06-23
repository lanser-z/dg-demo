# 模块六实施步骤：DWA 宽表分析 + DuckDB 即席查询

> 对应 `docs/Background.md` § 6.6。
> 目标：用 DuckDB 对模块五产出的 3 张 DWA 宽表做即席查询，验证数据可用性，让业务人员体会「临时问数字，不用等 IT」的效率提升。

---

## 0. 即席查询总览

| 场景 | 数据源 | 验证什么 | 预期结论 |
|------|--------|---------|---------|
| 销售趋势 | `dwa_sales_daily` | 最近 30 天订单数 / 销售额 / 客户数趋势 | 趋势图可自助生成 |
| 告警传感器排名 | `dwa_tag_alarm` | Top 20 高频告警传感器 | 这 10 个点位占 80% 告警量 |
| 月度煤质 | `dwa_coal_quality` | 各矿井各煤种灰分 / 热值月度均值 | 3 月精煤灰分普遍偏高 |
| 跨系统产销对比 | `dwa_sales_daily` + `dwa_tag_alarm` | ⚠️ 需业务自己写 JOIN | 诚实声明：当前为单系统宽表 |

> 场景 1~3 可现场出数，场景 4 需业务人员自己写 SQL JOIN（Phase 2 跨系统产销宽表交付后自动解决）。

---

## 1. 技术实现

### 1.1 查询引擎：DuckDB

DuckDB 是 in-memory OLAP 引擎，直接扫描 Parquet / Delta Lake 文件做聚合，无需数据导入。

**为什么用 DuckDB**：
- 零部署（`pip install duckdb`）
- 直接读 Parquet / Delta Lake（不需要先建库建表）
- 向量化执行，10GB 级数据秒级出结果

**局限**：
- 数据全部加载到内存（教学数据规模刚好）
- 进程退出后数据消失（适合即席，生产环境换 ClickHouse / Doris）

**局限**：
- 数据全部加载到内存（教学数据规模刚好）
- 进程退出后数据消失（适合即席，生产环境换 ClickHouse / Doris）

### 1.2 DuckDB vs ClickHouse：为什么选 DuckDB

| 维度 | DuckDB | ClickHouse |
|------|--------|------------|
| 部署模式 | 嵌入式（in-process），无需服务进程 | 分布式服务器，需要独立部署 |
| 适用规模 | 单节点 <100GB（本项目 ~1GB） | TB~PB 级分布式集群 |
| 性能 | [ClickBench 2025年10月排名第一](https://motherduck.com/learn/fastest-olap-databases-compared)（单节点） | 多节点并行，适合大规模数据 |
| 运维成本 | 零运维（`pip install duckdb`） | 需要管理集群、副本、扩容 |
| 数据湖直读 | ✅ Parquet / Delta Lake / Iceberg | ✅ Parquet / etc. |

**本项目选 DuckDB 的理由**：
- 教学数据约 1GB，完全在 DuckDB 舒适区
- Jupyter Notebook 内直接 `import duckdb` 使用，零额外依赖
- 单节点性能最优，无需运维分布式集群

> **Phase 2 升级路径**：当数据规模增长到 100GB+ 或需要多用户并发查询时，升级为 ClickHouse / Doris，SQL 语法兼容，无需重写查询。

### 1.3 查询路径

```
Delta Lake（data/lakehouse/dwa/）
       │
       │  DuckDB 直读 Parquet
       ▼
  in-memory 聚合
       │
       ▼
  即席查询结果（DataFrame / CSV）
```

### 1.4 依赖关系

```
模块五 build_dwa_models.py
       │ 已产出 3 张 DWA 表
       ▼
data/lakehouse/dwa/
       │
       │  本模块 DuckDB 即席查询
       ▼
  业务结论（销售趋势 / 告警排名 / 煤质月度）
```

> 前置条件：模块五 `build_dwa_models.py --layer dwa` 已跑通，3 张 DWA 表已写入 Delta Lake。

---

## 2. 教学 notebook

`notebook/module5.ipynb` 步骤 2~5 已覆盖本模块所有即席查询：

| 步骤 | 内容 | 调用的函数 / 命令 |
|------|------|-----------------|
| 步骤2 | 即席查询：日销售趋势 | DuckDB SQL → `dwa_sales_daily` |
| 步骤3 | 即席查询：传感器告警 Top | DuckDB SQL → `dwa_tag_alarm` |
| 步骤4 | 即席查询：月度煤质 | DuckDB SQL → `dwa_coal_quality` |
| 步骤5 | 4 个分析场景验证 | 综合查询 + 诚实声明 |

**设计原则**：
- 不在 notebook 里写大段聚合逻辑（已在 `build_dwa_models.py`）
- 每个 code cell ≤15 行（调 DuckDB SQL + 展示结果）
- 步骤5 包含诚实声明：产销对比需业务自己写 JOIN

---

## 3. 执行流程

```bash
# step 1: 确保模块五已跑完（DWA 表已生成）
uv run python scripts/build_dwa_models.py --layer dwa

# step 2: 打开教学 notebook
jupyter notebook notebook/module5.ipynb

# step 3: 依次跑步骤 2~5 的 code cell

# step 4:（可选）用 duckdb CLI 直接查
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily' LIMIT 5;"
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/pi_system/dwa_tag_alarm' ORDER BY high_value_count DESC LIMIT 10;"
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/lims/dwa_coal_quality' ORDER BY month DESC, MINE_CODE LIMIT 10;"
```

---

## 4. 当前状态

**即席查询功能（100%）**
- [x] `notebook/module5.ipynb` 步骤 2~5：3 张 DWA 表即席查询
- [x] DuckDB Python API（`duckdb.connect().execute().df()`）
- [x] DuckDB CLI 命令行查询
- [x] 4 个场景验证（含诚实声明）

**4 个分析场景可达性**

| 场景 | 数据源 | 当前可达 | 说明 |
|------|--------|---------|------|
| 销售趋势 | `dwa_sales_daily` | ✅ 可查 | 最近 30 天订单数 / 销售额 / 客户数 |
| 告警传感器排名 | `dwa_tag_alarm` | ✅ 可查 | Top 20 高频告警，定位维护重点 |
| 月度煤质 | `dwa_coal_quality` | ✅ 可查 | 各矿井各煤种灰分 / 热值月度均值 |
| 跨系统产销对比 | dwa + dwd JOIN | ⚠️ 需自己写 JOIN | 矿井日产量 vs 日发货量，当前无跨系统表 |

**演示边界（必须明确说）**
- 这是**数据可用性验证**，不是生产级 OLAP
- 临时查询 5 分钟能出，生产报表需等 Phase 2（ClickHouse + Superset）
- 场景 4 产销对比：当前无 PI 生产量与 SAP 销售量的跨系统关联

**待办（Phase 2）**
- [ ] ClickHouse / Doris 替代 DuckDB（物化视图自动刷新）
- [ ] Apache Superset 看板替代 CLI 即席查询
- [ ] 跨系统产销宽表 `dwa_sales_production`（PI + LIMS + SAP + KNA1）
- [ ] 钻取（年→月→日→单笔）和切片（单矿井）功能

---

## 5. 故障排查

### 5.1 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| DuckDB 查出来为空 | DWA 表未生成（模块五没跑） | 先跑 `uv run python scripts/build_dwa_models.py --layer dwa` |
| `duckdb` 命令不存在 | 未安装 duckdb CLI | `uv pip install duckdb`；或用 Python API 替代 |
| Delta Lake 路径读不到 | 目录不存在或权限问题 | `ls data/lakehouse/dwa/` 确认路径 |
| 告警排名全是 0 | `high_value_count` 阈值判断问题（数据无 >8000 的值） | 查 `dwa_tag_alarm` 全量数据确认 |
| 月度煤质字段为空 | Parquet schema 列名大小写 / 空格 | `df.columns.tolist()` 确认实际列名 |
| Jupyter 卡住不返回 | DuckDB 加载大 Parquet 耗尽内存 | 减少 LIMIT 或给容器加内存 |

### 5.2 报错自查清单

复制 SQL 模板后报错的排查顺序：

1. **表不存在**：确认路径正确，`ls data/lakehouse/dwa/sap_erp/dwa_sales_daily/` 有 Parquet 文件
2. **列不存在**：用 `SELECT * FROM 'path/' LIMIT 1` 查 schema，确认列名大小写
3. **语法错误**：确认 SQL 中路径用**单引号**包裹（如 `'data/lakehouse/...'`）
4. **内存不足**：减少 LIMIT，或确认机器内存 ≥8GB

---

## 6. 快速命令汇总

### 6.1 场景 1 SQL 模板：销售趋势

```sql
-- 日销售汇总：最近 30 天趋势
SELECT
    sale_date,
    order_count,
    customer_count,
    total_amount,
    avg_order_amount
FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily/'
ORDER BY sale_date DESC
LIMIT 30;
```

### 6.2 场景 2 SQL 模板：告警传感器排名

```sql
-- Top 20 高频告警传感器
SELECT
    mine,
    face,
    tag,
    high_value_count,
    missing_count,
    avg_value,
    stddev_value
FROM 'data/lakehouse/dwa/pi_system/dwa_tag_alarm/'
ORDER BY high_value_count DESC
LIMIT 20;
```

### 6.3 场景 3 SQL 模板：月度煤质

```sql
-- 月度煤质报告（按矿井×月份聚合）
SELECT
    MINE_CODE,
    month,
    SAMPLE_TYPE,
    sample_count,
    avg_ash_content,
    avg_volatile_content,
    avg_sulfur_content,
    avg_gross_calorific
FROM 'data/lakehouse/dwa/lims/dwa_coal_quality/'
ORDER BY month DESC, MINE_CODE
LIMIT 50;
```

### 6.4 场景 4 SQL 模板：产销对比（⚠️ 需业务自己写 JOIN）

```sql
-- ⚠️ 警告：当前 3 张 DWA 均为单系统汇总，
-- 跨系统产销对比需要 JOIN PI 生产数据。
-- Phase 2 的 dwa_sales_production 交付后自动解决。
SELECT
    s.sale_date,
    s.total_amount,
    s.order_count
    -- p.mine,
    -- p.production_volume
FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily/' s
-- LEFT JOIN 'data/lakehouse/dwa/pi_system/dwa_production/' p
--   ON s.sale_date = p.production_date
LIMIT 30;
```

### 6.5 快速命令

```bash
# 构建 DWA 表（如未完成）
uv run python scripts/build_dwa_models.py --layer dwa

# DuckDB 即席查询（CLI）
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily' ORDER BY sale_date DESC LIMIT 10;"
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/pi_system/dwa_tag_alarm' ORDER BY high_value_count DESC LIMIT 10;"
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/lims/dwa_coal_quality' ORDER BY month DESC LIMIT 10;"

# DuckDB 即席查询（Python）
python3 - <<'EOF'
import duckdb
conn = duckdb.connect()
df = conn.execute("SELECT * FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily' LIMIT 5").df()
print(df)
EOF

# 教学入口
jupyter notebook notebook/module5.ipynb
```
