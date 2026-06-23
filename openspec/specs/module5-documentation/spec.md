# module5-documentation Spec

> 对应文档能力：模块五实施文档

---

## Purpose

TBD

---

## ADDED Requirements

### Requirement: 文档位置与命名
module5-documentation SHALL be saved as `docs/Module5.md` and follow the same naming convention as `docs/Module1.md` through `docs/Module4.md`.

### Requirement: 必需的章节
The document SHALL contain the following sections:

1. **概述**（0. DWA 宽表总览）：3 张表的用途、数据源、主要字段、业务场景表格
2. **代码实现**（1.）：`build_dwa_models.py` 函数说明、存储路径、依赖关系
3. **教学 notebook**（2.）：步骤结构、每个步骤调用的函数/命令
4. **执行流程**（3.）：完整命令序列（从 DWD 入湖到 notebook 打开）
5. **当前状态**（4.）：各部分完成情况、分析场景可达性表格
6. **故障排查**（5.）：常见问题、原因、处理方法表格
7. **快速命令汇总**（6.）：常用命令速查

### Requirement: 分析场景可达性表格
The "当前状态" section SHALL include a table showing:

| 场景 | 数据源 | 当前可达 |
|------|--------|---------|
| 销售趋势 | `dwa_sales_daily` | ✅ 可查 |
| 告警传感器排名 | `dwa_tag_alarm` | ✅ 可查 |
| 月度煤质报告 | `dwa_coal_quality` | ✅ 可查 |
| 跨系统产销对比 | 需 PI + SAP + LIMS JOIN | ⚠️ 需自己写 JOIN |

### Requirement: 故障排查表格
The document SHALL include troubleshooting entries for at least:
- `build_dwa_models.py` 报 `ModuleNotFoundError: No module named 'duckdb'`
- DWA 表行数为 0（Parquet 文件路径/LIMIT 问题）
- DuckDB 查不到 Delta Lake 表
- Delta Lake 写入报 `FileExistsError`
- 煤质字段（如 全硫St）为空（列名大小写/空格问题）

### Requirement: 快速命令
The "快速命令汇总" section SHALL include:
- 构建 3 张 DWA 宽表的完整命令
- 验证 DWA 写入的命令
- DuckDB 即席查询示例
- Jupyter notebook 启动命令

### Requirement: 文档风格一致性
The document SHALL use the same formatting conventions (tables, headers, code blocks) as `docs/Module1.md` through `docs/Module4.md`.

---

## Scenarios

#### Scenario: 文档位置正确
- **WHEN** file `docs/Module5.md` is accessed
- **THEN** it exists at the same level as `docs/Module1.md` through `docs/Module4.md`

#### Scenario: 必需章节齐全
- **WHEN** `docs/Module5.md` is reviewed
- **THEN** all 7 required sections (0~6) are present with non-empty content

#### Scenario: 分析场景可达性表格准确
- **WHEN** table in section 4 is checked
- **THEN** first 3 scenarios show ✅ (可查)
- **AND** 4th scenario shows ⚠️ (需自己写 JOIN)
- **AND** explanation matches Phase 2 scope

#### Scenario: 故障排查覆盖常见问题
- **WHEN** troubleshooting section is reviewed
- **THEN** at least 5 common error scenarios are listed with cause and resolution
