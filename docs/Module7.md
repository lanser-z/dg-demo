# 模块七实施步骤：主数据编码标准化

> 对应 `docs/Background.md` § 6.7。
> 目标：建立矿井 / 客户 / 物料维表，统一编码体系，为跨系统分析（模块十二产销宽表）扫除 JOIN 障碍。Phase 1 各系统字面统一但字段名不同，Phase 2 建立标准维表彻底解决。

---

## 0. 主数据标准化总览

### 0.1 痛点：跨系统 JOIN 的编码障碍

当前 Phase 1 状态：各系统矿井编码字面上都是 `M001`~`M005`，但 JOIN 时需要大量映射：

```sql
-- 没有维表时：跨系统产销分析需要 3 个 WHERE 子句
SELECT s.sale_date, p.mine, s.total_amount
FROM dwa_sales_daily s
-- LEFT JOIN dwd_pi_tags p ON ???  -- 字段名不同，JOIN 条件不直观
WHERE s.mine = 'M001'   -- SAP 字段叫 MINE
  AND p.mine_code = 'M001'  -- PI 字段叫 MINE_CODE
  AND l.mine_code = 'M001'  -- LIMS 字段叫 MINE_CODE
```

**问题根因**：各系统对「同一矿井」的字段名不统一（`mine` vs `mine_code` vs `mine`）。

### 0.2 Phase 1 vs Phase 2

| 维度 | Phase 1（当前） | Phase 2（目标） |
|------|----------------|----------------|
| 矿井编码 | 字面一致（M001），字段名不同（`mine`/`mine_code`） | 统一维表 `dim_mine(mine_code, mine_name, mine_type)` |
| 客户编码 | KUNNR 字面一致，无校验 | 统一维表 `dim_customer(kunnr, customer_name, region, credit_level)` |
| 物料编码 | MARA 物料编码未关联 LIMS/OA | 统一维表 `dim_material(matnr, mat_desc, mat_type)` |
| JOIN 方式 | 大量 `WHERE a.mine = b.mine` 映射子查询 | 维表 JOIN，条件清晰、复用性强 |

### 0.3 维表设计原则

- **轻量**：不建独立 MDM 系统，维表直接放在 `data/lakehouse/dwd/_dimensions/`
- **标准编码**：使用源系统已统一的字面值（如 `M001`）作为主键，不重新编码
- **可追溯**：维表记录源字段到标准字段的映射关系
- **Phase 2 专用**：不影响 Phase 1 的 3 张 DWA 宽表

---

## 1. 维表设计

### 1.1 矿井维表 `dim_mine`

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| mine_code | VARCHAR | 标准矿井编码（如 M001） | 源系统统一 |
| mine_name | VARCHAR | 矿井中文名称 | KNA1 或手动维护 |
| mine_type | VARCHAR | 矿井类型（露天/井工） | KNA1 或手动维护 |
| sap_mine_field | VARCHAR | SAP 源字段名（如 `WERKS`） | 映射用 |
| pi_mine_field | VARCHAR | PI 源字段名（如 `TAG` 中的 mine 段） | 映射用 |
| lims_mine_field | VARCHAR | LIMS 源字段名（如 `MINE_CODE`） | 映射用 |

### 1.2 客户维表 `dim_customer`

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| kunnr | VARCHAR | 标准客户编码（6 位） | KNA1 |
| customer_name | VARCHAR | 客户中文名称 | KNA1-NAME1 |
| region | VARCHAR | 所属区域 | KNA1-REGION |
| credit_level | VARCHAR | 信用等级 | KNA1 映射 |

### 1.3 物料维表 `dim_material`

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| matnr | VARCHAR | 标准物料编码（9 位） | MARA |
| mat_desc | VARCHAR | 物料描述 | MARA-MAKTX |
| mat_type | VARCHAR | 物料类型（原煤/精煤/中煤/矸石/洗煤） | MARA 映射 |

### 1.4 存储路径

```
data/lakehouse/dwd/
  _dimensions/
    dim_mine/           ← Delta Lake
    dim_customer/        ← Delta Lake
    dim_material/        ← Delta Lake
```

---

## 2. 教学 notebook

`notebook/module7.ipynb` 按以下结构组织：

| 步骤 | 内容 | 调用的函数 / 命令 |
|------|------|-----------------|
| 痛点故事 | 跨系统 JOIN 需要 3 个 WHERE 映射的尬 | — |
| 步骤 1 | 构建 3 张维表（矿井/客户/物料） | `build_dimension_tables.py` |
| 步骤 2 | 验证维表内容 | DuckDB 查询 |
| 步骤 3 | 演示 JOIN 改善：产销分析 | 维表 JOIN SQL vs 无维表 SQL |
| 诚实声明 | 当前维表为轻量演示，生产需 MDM 系统 | — |

**设计原则**：
- 维表构建脚本独立，不修改 DWD 清洗逻辑
- 每个 code cell ≤15 行
- 步骤 3 对比展示「有维表」vs「无维表」的 JOIN 差异

---

## 3. 执行流程

```bash
# step 1: 构建矿井/客户/物料维表
uv run python scripts/build_dimension_tables.py

# step 2: 验证维表写入
ls data/lakehouse/dwd/_dimensions/dim_mine/
ls data/lakehouse/dwd/_dimensions/dim_customer/
ls data/lakehouse/dwd/_dimensions/dim_material/

# step 3: 打开教学 notebook
jupyter notebook notebook/module7.ipynb

# step 4: 验证维表内容（DuckDB）
duckdb -c "SELECT * FROM 'data/lakehouse/dwd/_dimensions/dim_mine/' LIMIT 5;"
```

---

## 4. 当前状态

**维表构建（Phase 2）**
- [ ] `scripts/build_dimension_tables.py`：`dim_mine` / `dim_customer` / `dim_material` 构建逻辑
- [ ] DuckDB 维表聚合（in-memory）
- [ ] Delta Lake 写入（`data/lakehouse/dwd/_dimensions/`）

**教学 notebook（Phase 2）**
- [ ] `notebook/module7.ipynb` 结构：痛点故事 + 3 维表构建 + JOIN 对比 + 诚实声明
- [ ] code cell 不内联大段 SQL
- [ ] 诚实声明维表为轻量演示

**分析场景可达性**

| 场景 | 数据源 | 当前可达 | 说明 |
|------|--------|---------|------|
| 单系统分析 | DWA 宽表 | ✅ 可查 | Phase 1 已有 |
| 跨系统产销分析（无维表） | dwd 层手动映射 | ⚠️ 可用但 JOIN 复杂 | 当前 workaround |
| 跨系统产销分析（有维表） | 维表 JOIN | ✅ 清晰简洁 | Phase 2 维表建立后 |

**与模块十二的依赖**

```
模块七（维表建立）
       │
       │  dim_mine / dim_customer / dim_material
       ▼
模块十二（跨系统产销宽表 dwa_sales_production）
       │  PI + LIMS + SAP + KNA1 4 表 JOIN
       ▼
  Superset 看板
```

---

## 5. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| 维表行数为 0 | 源 Parquet 路径不对 | 确认 `data/historical/` 下各系统 parquet 存在 |
| JOIN 结果为空 | 字段名映射不匹配 | 用 `df.columns.tolist()` 确认源字段名 |
| 客户维表 KUNNR 重复 | KNA1 数据本身有重复 | 维表构建时用 `DISTINCT` 去重 |
| 物料维表 MATNR 重复 | MARA 同一物料有多个描述 | 按物料编码去重，取最新描述 |

---

## 6. 快速命令汇总

```bash
# 构建 3 张维表
uv run python scripts/build_dimension_tables.py

# 验证维表
ls data/lakehouse/dwd/_dimensions/dim_mine/
ls data/lakehouse/dwd/_dimensions/dim_customer/
ls data/lakehouse/dwd/_dimensions/dim_material/

# DuckDB 验证维表内容
duckdb -c "SELECT * FROM 'data/lakehouse/dwd/_dimensions/dim_mine/' LIMIT 5;"

# 教学入口
jupyter notebook notebook/module7.ipynb
```
