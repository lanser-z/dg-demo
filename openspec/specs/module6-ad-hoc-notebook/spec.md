# module6-ad-hoc-notebook Spec

> 对应教学能力：模块六教学 notebook，即席查询验证 3 张 DWA 宽表

---

## Purpose

TBD

---
## Requirements
### Requirement: Notebook 结构
module6-ad-hoc-notebook SHALL contain the following sections in order:

1. 痛点故事（markdown）：「等 IT 排期 3 天才能拿到数据」的尬
2. 步骤 2（code）：即席查询——日销售趋势（`dwa_sales_daily`）
3. 步骤 3（code）：即席查询——传感器告警 Top（`dwa_tag_alarm`）
4. 步骤 4（code）：即席查询——月度煤质（`dwa_coal_quality`）
5. 步骤 5（code）：4 个分析场景验证 + 诚实声明
6. 诚实声明（markdown）：当前为单系统宽表，跨系统产销对比需 Phase 2

#### Scenario: Notebook 结构正确
- **WHEN** user opens `notebook/module5.ipynb`
- **THEN** the notebook contains sections 1 through 6 listed above in order

### Requirement: Code Cell 行数限制
Each code cell SHALL contain at most 15 lines of code that perform DuckDB queries or display results.

#### Scenario: Code cell 行数合规
- **WHEN** code cells are inspected
- **THEN** no single code cell exceeds 15 lines

### Requirement: 复用 build_dwa_models.py
The notebook SHALL call `duckdb.connect()` directly for ad-hoc queries. Aggregation logic is NOT inlined in notebook cells.

#### Scenario: DuckDB 连接复用
- **WHEN** notebook executes ad-hoc query cells
- **THEN** `conn = duckdb.connect()` is called in setup cell
- **AND** subsequent cells reuse the `conn` object

### Requirement: 4 个分析场景验证
The notebook SHALL demonstrate the following 4 analysis scenarios:

| 场景 | 数据源 | 预期结论 |
|------|--------|---------|
| 销售趋势 | `dwa_sales_daily` | 最近 30 天订单数/销售额趋势 |
| 告警传感器排名 | `dwa_tag_alarm` | Top 20 高频告警传感器 |
| 月度煤质 | `dwa_coal_quality` | 各矿井各煤种灰分月度均值 |
| 产销对比 | `dwa_sales_daily` + `dwa_tag_alarm` | ⚠️ 需业务自己写 JOIN（诚实声明） |

#### Scenario: 4 个场景均能出数
- **WHEN** step 5 (4 scenarios) is executed
- **THEN** scenario 1~3 return query results
- **AND** scenario 4 prints honest declaration

### Requirement: 诚实声明内容
The notebook SHALL explicitly state in markdown cells that:
- 当前 3 张 DWA 宽表均为**单系统**汇总
- 跨系统产销对比需要业务人员自己写 JOIN
- 该功能在 Phase 2 跨系统产销宽表交付后自动解决

#### Scenario: 诚实声明可见
- **WHEN** user scrolls to the end of the notebook
- **THEN** a markdown cell clearly states the limitation of single-system DWA tables
- **AND** mentions that cross-system analysis requires Phase 2

### Requirement: 执行方式
The notebook SHALL use `duckdb.connect()` from DuckDB Python API for in-notebook queries.

#### Scenario: 执行方式正确
- **WHEN** notebook is executed from top to bottom
- **THEN** all code cells use `duckdb.connect()` for queries
- **AND** no external OLAP server is required

