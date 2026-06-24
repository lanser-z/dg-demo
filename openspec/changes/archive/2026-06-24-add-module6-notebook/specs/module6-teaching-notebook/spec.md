# module6-teaching-notebook Spec

> 对应教学能力：模块六独立教学 notebook，承载全套教学内容

---

## Purpose

为业务人员提供模块六的独立教学 notebook，包含痛点故事、技术选型、即席查询验证、故障排查和快速命令。

---

## ADDED Requirements

### Requirement: Notebook 结构
module6-teaching-notebook SHALL contain the following sections in order:

1. 痛点故事（markdown）：「等 IT 排期 3 天才能拿到数据」的尬
2. 技术选型（markdown）：为什么用 DuckDB 而不是 ClickHouse
3. 依赖检查（code）：检查模块五 DWA 表是否已生成
4. 步骤 2（code）：即席查询——日销售趋势（`dwa_sales_daily`）
5. 步骤 3（code）：即席查询——传感器告警 Top（`dwa_tag_alarm`）
6. 步骤 4（code）：即席查询——月度煤质（`dwa_coal_quality`）
7. 步骤 5（code）：4 个分析场景验证 + 诚实声明
8. 故障排查（markdown）：5 个常见问题 + 报错自查清单
9. 快速命令（markdown）：4 个场景 SQL 模板 + CLI 命令速查
10. 诚实声明（markdown）：当前为单系统宽表，跨系统产销对比需 Phase 2

#### Scenario: Notebook 结构完整
- **WHEN** user opens `notebook/module6.ipynb`
- **THEN** the notebook contains sections 1 through 10 listed above in order

### Requirement: 依赖检查
The notebook SHALL check whether the module5 DWA tables exist before running ad-hoc query cells.

#### Scenario: DWA 表已存在
- **WHEN** user runs the dependency check cell with DWA tables present
- **THEN** a success message is printed indicating tables are available

#### Scenario: DWA 表不存在
- **WHEN** user runs the dependency check cell with DWA tables missing
- **THEN** a clear error message is printed with the command to build DWA tables
- **AND** `SystemExit` is raised to prevent running empty queries

### Requirement: Code Cell 行数限制
Each code cell SHALL contain at most 15 lines of code that perform DuckDB queries or display results.

#### Scenario: Code cell 行数合规
- **WHEN** code cells are inspected
- **THEN** no single code cell exceeds 15 lines

### Requirement: 复用 module5.ipynb 的即席查询代码
The notebook SHALL reuse the same DuckDB query code cells from module5.ipynb for steps 2-5.

#### Scenario: 代码复用正确
- **WHEN** step 2-5 cells are inspected
- **THEN** the DuckDB queries match those in `notebook/module5.ipynb` steps 2-5

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
