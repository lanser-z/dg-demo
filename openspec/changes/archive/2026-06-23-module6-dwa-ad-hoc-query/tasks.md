# 模块六：DWA 宽表即席查询验证 — 任务清单

## 1. 文档准备

- [x] 1.1 创建 `docs/Module6.md`，包含 7 节：概述、技术实现、教学 notebook、执行流程、当前状态、故障排查、快速命令汇总
- [x] 1.2 在 `docs/Module6.md` 中补充「技术实现」章节的 DuckDB vs ClickHouse 性能对比说明（基于 ClickBench 数据）
- [x] 1.3 在 `docs/Module6.md` 中补充 4 个分析场景 SQL 模板（销售趋势 / 告警排名 / 月度煤质 / 产销对比含诚实声明）
- [x] 1.4 在 `docs/Module6.md` 中补充故障排查表格（至少 5 个常见问题）

## 2. Notebook 补全

- [x] 2.1 在 `notebook/module5.ipynb` 开头补充步骤 0（痛点故事 markdown cell）
- [x] 2.2 在 `notebook/module5.ipynb` 补充步骤 5（4 场景验证 code cell + 诚实声明 markdown cell）
- [x] 2.3 确认步骤 2~5 的每个 code cell ≤15 行
- [x] 2.4 验证 notebook 从头跑到尾无报错

## 3. 实现验证

- [x] 3.1 确认 `build_dwa_models.py --layer dwa` 已跑通，3 张 DWA 表已写入 Delta Lake
- [x] 3.2 用 DuckDB CLI 执行 4 个场景的 SQL 模板，确认场景 1~3 出数、场景 4 含诚实声明
- [x] 3.3 更新 `docs/Background.md` § 6.6 状态（如需要）

## 4. OpenSpec 归档

- [x] 4.1 将 change archive 提交到 `spec/module6-dwa-ad-hoc-query` 分支
- [x] 4.2 同步 delta specs 到 main `openspec/specs/`
- [ ] 4.3 将 change 归档（`openspec archive`）
