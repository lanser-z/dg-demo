# module6-documentation Spec

> 对应文档能力：模块六实施文档

---

## Purpose

TBD

---

## MODIFIED Requirements

### Requirement: 文档位置与命名
module6-documentation SHALL be saved as `docs/Module6.md` and follow the same naming convention as `docs/Module1.md` through `docs/Module5.md`.

#### Scenario: 文档位置正确
- **WHEN** file `docs/Module6.md` is accessed
- **THEN** it exists at the same level as `docs/Module1.md` through `docs/Module5.md`

### Requirement: 必需的章节
The document SHALL contain the following sections:

1. **概述**（0. 即席查询总览）：4 个场景的用途、数据源，主要字段表格
2. **技术实现**（1.）：DuckDB 查询引擎说明、查询路径、依赖关系
3. **教学 notebook**（2.）：步骤结构、每个步骤调用的函数/命令
4. **执行流程**（3.）：完整命令序列（构建 DWA → 打开 notebook → 跑 cell）
5. **当前状态**（4.）：各部分完成情况，分析场景可达性表格
6. **故障排查**（5.）：常见问题、原因、处理方法表格
7. **快速命令汇总**（6.）：DuckDB CLI 命令速查、4 个场景 SQL 模板

#### Scenario: 必需章节齐全
- **WHEN** `docs/Module6.md` is reviewed
- **THEN** all 7 required sections (0~6) are present with non-empty content

### Requirement: 分析场景可达性表格
The "当前状态" section SHALL include a table showing:

| 场景 | 数据源 | 当前可达 |
|------|--------|---------|
| 销售趋势 | `dwa_sales_daily` | ✅ 可查 |
| 告警传感器排名 | `dwa_tag_alarm` | ✅ 可查 |
| 月度煤质 | `dwa_coal_quality` | ✅ 可查 |
| 跨系统产销对比 | 需 PI + SAP + LIMS JOIN | ⚠️ 需自己写 JOIN |

#### Scenario: 分析场景可达性表格准确
- **WHEN** table in section 4 is checked
- **THEN** first 3 scenarios show ✅ (可查)
- **AND** 4th scenario shows ⚠️ (需自己写 JOIN)

### Requirement: 技术说明：DuckDB vs ClickHouse
The document SHALL include a brief comparison of DuckDB vs ClickHouse for ad-hoc queries, explaining:
- DuckDB is embedded (in-process), no server required
- DuckDB wins on single-node <100GB scale (ClickBench 2025 #1)
- This demo uses DuckDB; ClickHouse/Doris are Phase 2 upgrades

#### Scenario: 技术说明包含 DuckDB vs ClickHouse 对比
- **WHEN** section 1 is reviewed
- **THEN** it explains why DuckDB is chosen for this demo scale
- **AND** mentions ClickHouse/Doris are Phase 2 options

### Requirement: 故障排查表格
The document SHALL include troubleshooting entries for at least:
- DuckDB 查询结果为空（DWA 表未生成）
- `duckdb` 命令不存在
- Delta Lake 路径读不到
- 告警排名全是 0
- 月度煤质字段为空
- Jupyter 卡住不返回（内存不足）

#### Scenario: 故障排查覆盖常见问题
- **WHEN** troubleshooting section is reviewed
- **THEN** at least 5 common error scenarios are listed with cause and resolution

### Requirement: 快速命令
The "快速命令汇总" section SHALL include:
- 构建 DWA 宽表的完整命令
- DuckDB CLI 即席查询示例（4 个场景）
- Jupyter notebook 启动命令

#### Scenario: 快速命令完整
- **WHEN** user refers to section 6 for quick reference
- **THEN** all commands are directly copy-paste executable
