## 1. 前置条件检查

- [x] 1.1 确认 DWD 层数据已落库：`ls data/lakehouse/dwd/sap_erp/dwd_vbak/` 有 Parquet 文件
- [x] 1.2 确认 Historical 数据存在：`ls data/historical/sap_erp/vbak_year=2022.parquet` 文件存在
- [x] 1.3 确认 `build_dwa_models.py` 可导入（`uv run python -c "import sys; sys.path.insert(0, 'scripts'); import build_dwa_models"`）

## 2. Notebook 结构搭建

- [x] 2.1 创建 `notebook/module5.ipynb` 空 notebook（参考 `notebook/module4.ipynb` 的 cell 数量和格式）
- [x] 2.2 添加痛点故事 markdown cell（业务取数等 3~5 天的场景描述）
- [x] 2.3 添加步骤 1 markdown + code cell（调用 `build_dwa_models.py` 构建 3 张 DWA 宽表）
- [x] 2.4 添加步骤 2 markdown + code cell（查询 `dwa_sales_daily`，展示最近 30 天销售趋势）
- [x] 2.5 添加步骤 3 markdown + code cell（查询 `dwa_tag_alarm`，展示 Top 20 告警传感器）
- [x] 2.6 添加步骤 4 markdown + code cell（查询 `dwa_coal_quality`，展示月度煤质）
- [x] 2.7 添加步骤 5 markdown + code cell（4 个分析场景综合验证）
- [x] 2.8 添加诚实声明 markdown cell（明确说明跨系统产销对比需 Phase 2）

## 3. Code Cell 实现

- [x] 3.1 步骤 1 code cell：调用 `uv run python scripts/build_dwa_models.py --layer dwa` 并打印输出
- [x] 3.2 步骤 2 code cell：DuckDB 查询 `dwa_sales_daily`，`≤10` 行，展示 `head(10)`
- [x] 3.3 步骤 3 code cell：DuckDB 查询 `dwa_tag_alarm`，展示 `head(10)` + 告警占比计算
- [x] 3.4 步骤 4 code cell：DuckDB 查询 `dwa_coal_quality`，按矿井×月份聚合结果
- [x] 3.5 步骤 5 code cell：综合查询 4 个场景（场景 4 注明需自己写 JOIN）
- [x] 3.6 确保每个 code cell ≤15 行（不含空行和注释）

## 4. 文档编写

- [x] 4.1 编写 `docs/Module5.md` 章节 0（DWA 宽表总览表格）
- [x] 4.2 编写章节 1（`build_dwa_models.py` 函数说明、存储路径、依赖关系）
- [x] 4.3 编写章节 2（notebook 步骤结构表格）
- [x] 4.4 编写章节 3（完整执行流程命令序列）
- [x] 4.5 编写章节 4（当前状态 + 分析场景可达性表格）
- [x] 4.6 编写章节 5（故障排查表格，≥5 条）
- [x] 4.7 编写章节 6（快速命令汇总）

## 5. 端到端验证

- [x] 5.1 确认 DWA Delta Lake 目录有文件：`ls data/lakehouse/dwa/sap_erp/dwa_sales_daily/`
- [x] 5.2 确认 `dwa_tag_alarm` 和 `dwa_coal_quality` 目录也有文件
- [x] 5.3 启动 Jupyter：`jupyter notebook notebook/module5.ipynb`（验证可打开）
- [x] 5.4 从头跑完所有 cells，确认无报错（3 个查询 cell 均验证通过）
- [x] 5.5 对照 `docs/Module5.md` 验收步骤逐一确认
