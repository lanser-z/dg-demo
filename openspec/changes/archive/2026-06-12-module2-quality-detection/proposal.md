## Why

模块一（数据资产可视化）已经让小白「看见」资产、看清质量评分卡，
但**发现问题只是开始**。当 SAP VBAP 出现 1% 孤儿行项目、PI 瓦斯超 1% 告警、
LIMS 灰分异常时，业务方会追问：

> "这些问题**影响多少行**？**哪些列/订单/标签**？**怎么定位到责任人**？"

当前模块一的质量检测停留在「整体评分」粒度，**没有自动化根因定位**。运维要排查一个 SAP 告警，
必须手写 pandas 查询；要分析一个 PI 异常突升，必须手算 3x 中位数阈值。**没有一套「从告警到根因」的标准化路径**。

本变更实现模块二「数据质量检测与根因定位」，把模块一的「发现问题」延伸为「定位问题」，
让小白能在 10 分钟内对每类告警走完：扫描 → 评分 → 根因 → 责任部门。

## What Changes

- 新增 `notebook/module2.ipynb`：以「痛点故事」开头（呼应模块一风格），分 3 步走完 GE 扫描 → 4 类根因定位 → 告警聚合
- 新增 `src/dg_education/ge_scan.py`：包装 `scripts/run_great_expectations.py`，提供 `run_ge_scan()` / `parse_ge_report()` 等 Notebook 友好接口
- 扩展 `src/dg_education/quality.py`：新增 4 个根因分析函数（SAP 孤儿行 / PI 缺失 / PI 异常 / LIMS 灰分）
- 扩展 `src/dg_education/visualization.py`：新增 3 个 plot 函数（根因分布 / 告警热力图 / 系统告警汇总）
- 更新 `src/dg_education/__init__.py`：导出新增 API
- 文档：`docs/Module2.md`（已存在）作为实施规范

**BREAKING**：无破坏性变更，纯增量。

## Capabilities

### New Capabilities

- `module2-quality-detection`：模块二教学 notebook + 根因分析能力（GE 扫描、根因定位、告警聚合可视化）
- `quality-root-cause-analysis`：4 类质量问题的根因分析能力（SAP VBAP 关联失效、PI 时序断点、PI 异常突升、LIMS 灰分异常）

### Modified Capabilities

无（模块一是 `step1-onboarding`，其规范不变；模块二是新增独立模块，不修改模块一行为）。

## Impact

**代码影响**：
- 新增文件：`notebook/module2.ipynb`、`src/dg_education/ge_scan.py`
- 修改文件：`src/dg_education/quality.py`（追加根因函数）、`src/dg_education/visualization.py`（追加 plot 函数）、`src/dg_education/__init__.py`（导出新 API）
- 依赖：无新增（`pandas` / `matplotlib` / `great-expectations` 已在 `pyproject.toml`）

**数据影响**：
- 使用 `data/historical/` 现有 2022 年全量 Parquet（不修改、不生成新数据）
- notebook 输出截图保存到 `screenshots/module2_*.png`（如未存在会自动创建）

**下游影响**：
- 后续模块三/模块四/模块五的 notebook 可直接复用 `ge_scan` / `quality` 模块
- 教学流程：模块一（看资产）→ 模块二（找问题）→ 模块三/四/五（解决问题）

**回滚计划**：
- 删除 `notebook/module2.ipynb` 与 `src/dg_education/ge_scan.py`
- 从 `src/dg_education/quality.py` / `visualization.py` / `__init__.py` 移除新增函数与导出
- 模块一与所有现有脚本不受影响（GE 扫描脚本 `scripts/run_great_expectations.py` 是独立 CLI）
