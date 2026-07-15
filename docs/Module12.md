# 模块十二实施步骤：跨系统 DWA + DuckDB OLAP

> **归属**：Background §6.12 / Phase 2
> **演示时长**：10 分钟
> **OLAP 引擎**：DuckDB（已在 `pyproject.toml`；ClickHouse/Doris/Superset 留 Phase 3）
> **新增产物**：`scripts/build_dwa_sales_production.py`、`notebook/module12.ipynb`、`data/lakehouse/dwa/dwa_sales_production/`

---

## 1. 模块概述

### 1.1 教学目标

把模块六演示版的 3 张单系统 DWA 宽表（`dwa_sales_daily` / `dwa_tag_alarm` / `dwa_coal_quality`）升级为「跨主题 4 表 JOIN 宽表 `dwa_sales_production`」+ DuckDB 物化视图模拟。让学员看到「数据治理从「单系统聚合」到「跨域联表」的能力跃迁」。

### 1.2 与 module6 的关系

| 维度 | module6（Phase 1） | module12（Phase 2 / 6.12） |
|------|-------------------|----------------------------|
| 宽表数量 | 3 张单系统 | 3 张单系统 + 1 张跨系统 |
| 上游路径 | `dwd/{system}/*`（旧 system-分区） | **6.11 subject-分区**（`dwd/{sales,production,coal_quality}/*`） |
| JOIN 能力 | 单表聚合 | 4 表 LEFT JOIN 跨主题 |
| 物化视图 | 一次性 `write_deltalake` | `CREATE TABLE AS SELECT` 模拟 |
| OLAP 引擎 | DuckDB 临时查询 | DuckDB 物化宽表 + DuckDB CLI 查 |
| 看板 | 无 | Phase 3 升级 Superset |

### 1.3 关键业务约束

| 表 | 跨主题关联键 | 说明 |
|----|--------------|------|
| `vbak` (SAP 销售订单) | `KUNNR` → `kna1` | ✅ 销售链自然键 |
| `vbak` (SAP 销售订单) | `mine_code` | ❌ **vbak 无 MINE_CODE 字段**（业务上销售订单不直接关联矿井） |
| `kna1` (SAP 客户) | `KUNNR` → `vbak` | ✅ 客户链自然键 |
| `tags` (PI 时序) | `mine` | ✅ 生产链自然键（PI 自己的 mine） |
| `samples` (LIMS 煤质) | `MINE_CODE` | ✅ 煤质链自然键（LIMS 自己的 mine） |
| 跨「销售-生产」 | ❌ 无 | 业务上 SAP 销售订单与 PI 生产数据无直接关联键 |

**结论**：4 表 LEFT JOIN 在 `vbak` 不含 `mine_code` 的现实数据上**无法严格连接**。6.12 实施方案：用 `LEFT(KUNNR, 1)` 派生伪键演示跨主题关联概念，文档明确说明"生产环境应引入 `dim_mine` 维表作为业务桥"。

---

## 2. 4 表 JOIN SQL 设计

### 2.1 SQL 模板

```sql
CREATE OR REPLACE TABLE dwa_sales_production AS
SELECT
    v.VBELN, v.ERDAT, v.KUNNR, k.NAME1 AS customer_name,
    v.mine_code, t.face,
    ROUND(t.avg_value, 4)                       AS daily_production,
    ROUND(s.AD, 4)                              AS ash_content,
    ROUND(s.QGR_AD, 4)                          AS calorific,
    ROUND(v.NETWR, 2)                           AS NETWR
FROM dwd_sales_dwd_vbak v
LEFT JOIN dwd_sales_dwd_kna1 k   ON v.KUNNR    = k.KUNNR
LEFT JOIN dwd_production_dwd_tags_agg t ON v.mine_code = t.mine
LEFT JOIN dwd_coal_quality_dwd_samples_agg s ON v.mine_code = s.MINE_CODE
```

### 2.2 关键差异 vs Background 6.12 原始 plan

| 项 | Background 6.12 假设 | 6.12 实际 |
|----|---------------------|----------|
| vbak bridge key | `mine_code` | `'M' || SUBSTR(BZIRK, 2, 3)` 派生 |
| tags 聚合 | 直接 JOIN | `GROUP BY mine` 聚合到日均（避免笛卡尔积） |
| samples 聚合 | 直接 JOIN | `GROUP BY mine_code` 聚合 |
| 采样 | 全量 | 默认 1% 采样（演示防 OOM） |

### 2.3 4 个分析场景 SQL

| 场景 | SQL 模板 | 业务问题 |
|------|----------|----------|
| 1. 产销对比 | `SELECT mine_code, COUNT(VBELN), AVG(daily_production) FROM dwa GROUP BY mine_code` | 各矿井日均产量 vs 订单数 |
| 2. 煤质定价 | `SELECT mine_code, AVG(ash_content), AVG(calorific), AVG(NETWR) FROM dwa GROUP BY mine_code` | 灰分/发热量 vs 订单均价 |
| 3. 安全趋势 | `SELECT mine_code, face, AVG(daily_production), STDDEV(daily_production) FROM dwa GROUP BY mine_code, face` | 矿井工作面生产波动 |
| 4. 订单履约 | `SELECT KUNNR, customer_name, COUNT(VBELN), SUM(NETWR) FROM dwa GROUP BY KUNNR` | 客户订单数 + 总额 |

---

## 3. 旧 3 张 DWA 切上游到 subject-分区

按 6.11 delta 承诺，6.12 兑现切上游：

| 旧 DWA | 6.11 前路径 | 6.12 路径 |
|--------|------------|----------|
| `dwa_sales_daily` | `dwd/sap_erp/dwd_vbak` | `dwd/sales/dwd_vbak` |
| `dwa_tag_alarm` | `dwd/pi_system/dwd_tags` | `dwd/production/dwd_tags` |
| `dwa_coal_quality` | `dwd/lims/dwd_samples` | `dwd/coal_quality/dwd_samples` |

`build_dwa_models.py` 中 3 个 DWA 函数的 read_parquet + write_delta（table_key）已切换。

---

## 4. 演进路径（Phase 3 不实现，仅记录）

### 4.1 ClickHouse 升级路径

```bash
docker run -d --name clickhouse-server -p 8123:8123 yandex/clickhouse-server:23.8
```

`scripts/build_dwa_sales_production.py` 替换为：
```python
import clickhouse_driver
client = clickhouse_driver.Client(host='localhost')
client.execute("""
    INSERT INTO dwa_sales_production
    SELECT ... FROM ...
""")
```

### 4.2 Superset 看板

```bash
docker run -d --name superset -p 8088:8088 \
  -e SUPERSET_SECRET_KEY=secret \
  apache/superset:4.1.1-py312
```

Superset `SQLAlchemy URI: clickhouse://localhost:8123/default`，4 个图表对应 4 个分析场景。

### 4.3 dim_mine 维表桥接

引入 `dim_mine(mine_code, mine_name, region)` 后：
- 销售订单 KUNNR → kna1 → region
- region → dim_mine.region → mine_code
- mine_code → tags.mine / samples.MINE_CODE

实现真正的 4 表自然 JOIN（无需伪键）。
