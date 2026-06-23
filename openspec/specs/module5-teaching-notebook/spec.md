# module5-teaching-notebook Spec

> 对应教学能力：模块五教学 notebook

---

## Purpose

TBD

---

## ADDED Requirements

### Requirement: Notebook 结构
module5-teaching-notebook SHALL contain the following sections in order:

1. 痛点故事（markdown）：业务取数等待 3~5 天的痛点
2. 步骤 1（code）：构建 3 张 DWA 宽表
3. 步骤 2（code）：即席查询——日销售趋势
4. 步骤 3（code）：即席查询——传感器告警 Top
5. 步骤 4（code）：即席查询——月度煤质
6. 步骤 5（code）：4 个分析场景验证
7. 诚实声明（markdown）：当前为单系统宽表，跨系统需 Phase 2

### Requirement: Code Cell 行数限制
Each code cell SHALL contain at most 15 lines of code that call functions from `build_dwa_models.py` or perform DuckDB queries. Large SQL blocks SHALL NOT be inlined in notebook cells.

### Requirement: 函数调用规范
The notebook SHALL call `build_dwa_models.py` functions for DWA construction, not inline the aggregation logic. Code cells SHALL only contain function calls and result display (head/print).

### Requirement: 4 个分析场景
The notebook SHALL demonstrate the following 4 analysis scenarios:

| 场景 | 数据源 | 预期结论 |
|------|--------|---------|
| 销售趋势 | `dwa_sales_daily` | 最近 30 天订单数/销售额趋势 |
| 告警传感器排名 | `dwa_tag_alarm` | Top 20 高频告警传感器 |
| 月度煤质 | `dwa_coal_quality` | 各矿井各煤种灰分月度均值 |
| 产销对比 | `dwa_sales_daily` + `dwa_tag_alarm` | ⚠️ 需业务自己写 JOIN（诚实声明） |

### Requirement: 诚实声明内容
The notebook SHALL explicitly state in markdown cells that:
- 当前 3 张 DWA 宽表均为**单系统**汇总
- 跨系统产销对比需要业务人员自己写 JOIN
- 该功能在 Phase 2 跨系统产销宽表交付后自动解决

### Requirement: 执行方式
The notebook SHALL use `%pip install duckdb` if needed, and use DuckDB Python API (`duckdb.connect()`) for in-notebook queries.

---

## Scenarios

#### Scenario: Notebook 成功运行所有步骤
- **WHEN** user executes all cells in `notebook/module5.ipynb` from top to bottom
- **THEN** each code cell completes without error
- **AND** each step outputs visible results (head/print)

#### Scenario: Code cell 行数合规
- **WHEN** code cells are inspected
- **THEN** no single code cell exceeds 15 lines
- **AND** aggregation logic is NOT inlined (functions from `build_dwa_models.py` are called instead)

#### Scenario: 诚实声明可见
- **WHEN** user scrolls to the end of the notebook
- **THEN** a markdown cell clearly states the limitation of single-system DWA tables
- **AND** mentions that cross-system analysis requires Phase 2

#### Scenario: 4 个场景均能出数
- **WHEN** step 5 (4 scenarios) is executed
- **THEN** scenario 1~3 return query results
- **AND** scenario 4 returns results requiring user-written JOIN (诚实声明 fulfilled)
