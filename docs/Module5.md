# 模块五实施步骤：ELT 数据加工与 DWA 主题宽表

> 对应 `docs/Background.md` § 6.5。
> 目标：从 DWD 清洗层构建 3 张 DWA 汇总宽表（日销售 / 传感器告警 / 月度煤质），用 DuckDB 即席查询验证数据可用性，支撑业务报表和临时分析。

---

## 0. DWA 宽表总览

| DWA 表名 | 主题 | 数据源 | 主要字段 | 业务场景 |
|---------|------|--------|---------|---------|
| `dwa_sales_daily` | 销售 | `sap_erp.vbak` | sale_date, order_count, customer_count, total_amount | 日销售趋势 / 订单量监控 |
| `dwa_tag_alarm` | 生产安全 | `pi_system.tags` | tag, mine, alarm_count, high_value_count, avg_value | 传感器告警 Top20 / 维护优先级 |
| `dwa_coal_quality` | 煤质 | `lims.samples` | mine_code, month, coal_type, avg_ash, avg_qgr | 月度煤质报告 / 产销定价参考 |

> 3 张表均为**单系统**汇总（Phase 1 范围）。跨系统产销宽表 `dwa_sales_production`（PI + LIMS + SAP + KNA1）属 Phase 2 / 模块十二，待主数据标准化后实现。

---

## 1. 代码实现

### 1.1 `scripts/build_dwa_models.py`

| 函数 | 说明 | 输出 |
|------|------|------|
| `build_dwa_sales_daily(conn)` | 日销售聚合：按 ERDAT 分组统计订单数/客户数/金额 | `dwa/sap_erp/dwa_sales_daily` |
| `build_dwa_tag_alarm(conn)` | 传感器告警聚合：按 tag 分组统计高频告警点位 | `dwa/pi_system/dwa_tag_alarm` |
| `build_dwa_coal_quality(conn)` | 煤质月汇总：按矿井×月份聚合灰分/挥发分/硫分/发热量 | `dwa/lims/dwa_coal_quality` |
| `build_dwd_with_derived(conn)` | DWD 扩展：增加订单规模分类等衍生字段 | `dwd_ext/`（非正式 DWD） |
| `write_delta(table_key, df)` | 将 DataFrame 写入 Delta Lake（mode=overwrite） | — |
| `_delta_stats(table_key)` | 返回 Delta 表文件数和总大小（MB） | — |
| `get_duckdb()` | 创建 DuckDB 连接，注册所有 ODS/DWD Delta Lake 表为视图 | — |

**关键设计**：
- DuckDB 读取 Parquet 直连聚合，不重复沉源数据
- DWA 结果写回 Delta Lake（`data/lakehouse/dwa/{system}/{table}/`）
- 所有聚合带 `LIMIT`，控制计算量（教学数据规模）

### 1.2 存储路径

```
data/lakehouse/
  dwa/
    sap_erp/dwa_sales_daily/     ← Delta Lake
    pi_system/dwa_tag_alarm/     ← Delta Lake
    lims/dwa_coal_quality/       ← Delta Lake
```

### 1.3 依赖关系

```
DWD 清洗层（data/lakehouse/dwd/）
       │
       │  build_dwa_models.py
       ▼
DWA 汇总层（data/lakehouse/dwa/）
       │
       │  DuckDB 即席查询
       ▼
业务分析（notebook module5.ipynb）
```

> 前置条件：DWD 层数据已落库（`scripts/ingest_to_deltalake.py --layer dwd` 已跑）。模块四清洗是本模块的前置。

---

## 2. 教学 notebook

`notebook/module5.ipynb` 按以下结构组织：

| 步骤 | 内容 | 调用的函数 / 命令 |
|------|------|-----------------|
| 痛点故事 | 「业务要一个数，等 IT 排期 3 天」的尬 | — |
| 步骤1 | 构建 3 张 DWA 宽表 | `build_dwa_models.py --layer dwa` |
| 步骤2 | DuckDB 即席查询：日销售趋势 | `dwa_sales_daily` SQL |
| 步骤3 | DuckDB 即席查询：传感器告警 Top | `dwa_tag_alarm` SQL |
| 步骤4 | DuckDB 即席查询：月度煤质 | `dwa_coal_quality` SQL |
| 步骤5 | 4 个分析场景验证 | 综合查询 |
| 诚实声明 | 当前为单系统宽表，跨系统需 Phase 2 | — |

**设计原则**：
- 每个 code cell ≤15 行（调函数 + 展示结果），大段逻辑在 `build_dwa_models.py`
- 不内联聚合 SQL，所有查询调用 `build_dwa_models.py` 中已定义的视图或直接读 Delta Lake
- 诚实声明跨系统宽表未实现，避免误导业务方

---

## 3. 执行流程

```bash
# step 1: 确保 DWD 层已落库（如未完成，先跑模块四）
uv run python scripts/ingest_to_deltalake.py --layer dwd

# step 2: 构建 3 张 DWA 宽表
uv run python scripts/build_dwa_models.py --layer dwa

# step 3: 打开教学 notebook
jupyter notebook notebook/module5.ipynb

# step 4: 验证 Delta Lake 写入
ls data/lakehouse/dwa/sap_erp/dwa_sales_daily/
ls data/lakehouse/dwa/pi_system/dwa_tag_alarm/
ls data/lakehouse/dwa/lims/dwa_coal_quality/
```

---

## 4. 当前状态

**DWA 构建（100%）**
- [x] `scripts/build_dwa_models.py`：3 张 DWA 表构建逻辑
- [x] DuckDB 聚合引擎（in-memory OLAP）
- [x] Delta Lake 写入（`write_deltalake`，mode=overwrite）
- [x] 3 张 DWA 表注册到 DataHub（`emit_via_rest_emitter.py` ASSETS 已含 `dwa_sales_daily` / `dwa_tag_alarm` / `dwa_coal_quality`）

**教学 notebook（100%）**
- [x] `notebook/module5.ipynb` 结构：痛点故事 + 3 表构建 + 3 个即席查询 + 4 场景验证
- [x] code cell 不内联大段 SQL
- [x] 诚实声明跨系统宽表待 Phase 2

**分析场景可达性**

| 场景 | 数据源 | 当前可达 |
|------|--------|---------|
| 销售趋势 | `dwa_sales_daily` | ✅ 可查 |
| 告警传感器排名 | `dwa_tag_alarm` | ✅ 可查 |
| 月度煤质报告 | `dwa_coal_quality` | ✅ 可查 |
| 跨系统产销对比 | 需 PI + SAP + LIMS JOIN | ⚠️ 需自己写 JOIN |

**待办（Phase 2）**
- [ ] 跨系统产销宽表 `dwa_sales_production`（PI 生产 + LIMS 煤质 + SAP 订单 + KNA1 客户）
- [ ] 客户主数据补全（KNA1 标准名称 → VBAK）
- [ ] 矿井/客户/物料维表（模块七主数据标准化）
- [ ] ClickHouse / Doris 物化视图替代 DuckDB
- [ ] Apache Superset 看板替代 CLI 即席查询

---

## 5. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| `build_dwa_models.py` 报 `ModuleNotFoundError: No module named 'duckdb'` | 未安装 duckdb | `uv pip install duckdb` |
| DWA 表行数为 0 | Parquet 文件路径 / LIMIT 导致数据为空 | 确认 `data/historical/` 下有对应 parquet；去掉 LIMIT 跑一遍 |
| DuckDB 查不到 Delta Lake 表 | `get_duckdb()` 未注册该路径 | 检查 `os.walk(LAKEHOUSE_ROOT)` 是否扫到了 `dwd` 目录 |
| Delta Lake 写入报 `FileExistsError` | 已存在同名文件且 mode 非 overwrite | `write_deltalake(..., mode="overwrite")` 已在代码中设置 |
| 煤质字段（如 全硫St）为空 | 列名大小写或空格问题 | Parquet schema 用 `df.columns` 确认实际列名 |

---

## 6. 快速命令汇总

```bash
# 构建 3 张 DWA 宽表
uv run python scripts/build_dwa_models.py --layer dwa

# 验证 DWA 写入
ls data/lakehouse/dwa/sap_erp/dwa_sales_daily/
ls data/lakehouse/dwa/pi_system/dwa_tag_alarm/
ls data/lakehouse/dwa/lims/dwa_coal_quality/

# DuckDB 即席查询示例
duckdb -c "SELECT * FROM 'data/lakehouse/dwa/sap_erp/dwa_sales_daily' LIMIT 5;"

# 教学入口
jupyter notebook notebook/module5.ipynb
```
