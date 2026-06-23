# 模块六：DWA 宽表即席查询验证 — 变更提案

## Why

模块五构建了 3 张 DWA 宽表（日销售 / 传感器告警 / 月度煤质），但没有验证业务人员能否直接用这些表做临时分析。业务部门临时问一个数字需要等 IT 排期 3 天，数据治理的价值无法被业务感知。

模块六通过在 `notebook/module5.ipynb` 中补充即席查询验证步骤，让业务人员和数据工程师能够快速验证 DWA 表的数据可用性，体现「临时问数字，不用等 IT」的价值。

## What Changes

1. **新增 `docs/Module6.md`**：模块六实施文档，补充 SQL 模板和快速命令速查，供业务人员参考。
2. **在 `notebook/module5.ipynb` 中补全模块六内容**：补充痛点故事和 4 个分析场景验证 cell（步骤 2~5 的即席查询已有代码，补上下文说明）。
3. **在 `docs/Module6.md` 中补充 SQL 模板**：4 个分析场景的可执行 SQL 示例，降低业务人员自助查询门槛。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `module6-ad-hoc-notebook`：教学 notebook，验证 3 张 DWA 宽表能用 DuckDB 即席查询出数，覆盖销售趋势 / 告警排名 / 月度煤质 / 产销对比 4 个场景。
- `module6-sql-templates`：SQL 模板，在文档中提供 4 个场景的可执行查询示例，供业务人员参考。
- `module6-documentation`：模块六实施文档，包含执行流程、故障排查、快速命令汇总。

## Impact

**受影响的文件**：
- `notebook/module5.ipynb`：补充步骤 0（痛点故事）和步骤 5（4 场景验证 + 诚实声明）
- `docs/Module6.md`：新增实施文档
- `docs/Background.md`：可能需要更新 6.6 节状态（标记模块六已完成）

**回滚计划**：
- 如需回滚，撤销 `notebook/module5.ipynb` 的步骤 0 和步骤 5 修改，删除 `docs/Module6.md`
- 不影响模块五的 DWA 表生成逻辑（`scripts/build_dwa_models.py` 未变更）
