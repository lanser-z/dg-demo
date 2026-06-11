## 1. 准备

- [x] 1.1 备份当前 `notebook/step1.ipynb` 到 `notebook/step1.ipynb.bak.YYYYMMDD`（已在 `.gitignore` 的 `*.bak` 规则下，不入库）
- [x] 1.2 创建 `src/dg_education/` 包目录与 `__init__.py`（新模块；与现有 `src/dg_simulator/` 平级）
- [x] 1.3 创建 `src/dg_education/tests/` 与 `tests/__init__.py`（基础单元测试）
- [x] 1.4 创建 `scripts/snapshot_datahub_ui.py`（Playwright 截图脚本骨架；先空跑通）
- [x] 1.5 验证 `screenshots/` 目录在 `.gitignore` 中（已有规则，新增截图不入库）

## 2. 核心代码下沉到 src/dg_education/

> 原则：notebook 是教学/演示，不是 IDE；大段代码必须移出 notebook，notebook 只 `import` + 调函数 + 写文字 + 渲染图。

- [x] 2.1 新建 `src/dg_education/quality.py`：迁移 step1.ipynb 中 5 个质量检测函数
  - `check_sap_quality(vbak, vbap, kna1) -> dict`（VBAK null/dup + VBAP 关联失效 + KNA1 重复）
  - `check_pi_quality(df_pi) -> dict`（点位缺失 + WAGAS 危险 + 异常突升）
  - `check_lims_quality(df_lims) -> dict`（关键指标空值 + 灰分超合理区间 + 重复）
  - `check_oa_quality(df_oa) -> dict`（重复 + 关键字段空值）
  - `calc_quality_score(quality_dict) -> dict`（基于 null/dup/outlier/link 比例反推四维 + 综合分）
  - 函数顶部加 docstring（输入/输出/单位/引用 Background.md）
- [x] 2.2 新建 `src/dg_education/catalog.py`：迁移资产目录构建逻辑
  - `build_asset_catalog(data_root: Path) -> pd.DataFrame`（列：系统、表/数据集、记录数、存储大小(MB)、说明、Owner）
  - `SYSTEM_INFO` 常量字典（5 系统 / 12 表的中文名 / Owner / 安全级别）
- [x] 2.3 新建 `src/dg_education/visualization.py`：迁移 4 段 matplotlib 代码为 4 个函数
  - `plot_storage_distribution(df, save_to=None)`（饼图 + 柱状图，2 subplot）
  - `plot_quality_scorecard(scores, save_to=None)`（四维分组柱状图 + 综合得分横向柱状图）
  - `plot_security_levels(save_to=None)`（按安全分级的彩色柱状图）
  - `plot_business_impact(alerts, save_to=None)`（**新增**，把每条 `[业务影响]` 翻译为柱状图，行数 × 注入率 × 单位成本 → 元成本）
- [x] 2.4 新建 `src/dg_education/business_impact.py`：业务影响换算
  - `COST_TABLE` 常量（每条告警的单位成本，从 `docs/Background.md` 业务场景取，标注"教学参考值"）
  - `estimate_annual_cost(alert_name, total_rows, injection_rate) -> dict`（返回 `{events_per_year, unit, total_yuan, narrative}`）
  - `format_business_impact_line(alert_name, total_rows, injection_rate) -> str`（生成 1 行 markdown 文本，给 notebook 直接打印）
- [x] 2.5 写 `src/dg_education/__init__.py`：导出 `check_*_quality` / `build_asset_catalog` / `plot_*` / `estimate_annual_cost` / `format_business_impact_line` 等 public API
- [x] 2.6 写基础单元测试 `src/dg_education/tests/test_quality.py` 与 `test_business_impact.py`：用 `data/historical/sap_erp/vbak_year=2023.parquet`（已生成的小样本）跑一遍函数，断言返回 dict 含预期 key、score 在 [0, 100]、cost 数字 > 0
- [x] 2.7 在 `pyproject.toml` 的 `[tool.uv]` 包发现部分注册 `src/dg_education`（与 `src/dg_simulator` 一致）

## 3. DataHub UI 截图脚本

> Playwright 是主流文档截图方案（Microsoft 团队 2024-2026 实践），用现有依赖即可。

- [x] 3.1 `scripts/snapshot_datahub_ui.py` 实现：
  - 启动 chromium headless（1440×900），登录 datahub/datahub
  - 截图 1：首页（DataHub v2 主题 + 5 系统入口可见）→ `screenshots/datahub_home.png`
  - 截图 2：搜索「lims」的结果页 → `screenshots/datahub_search.png`
  - 截图 3：lims/samples 详情页 → `screenshots/datahub_detail.png`
  - 截图失败/容器未启动时降级：在 console 打 WARNING 并写 1 个 `screenshots/UNAVAILABLE.txt` 占位（notebook 检测到该文件则走纯文字 walkthrough）
- [x] 3.2 跑一次：DataHub 7 容器 healthy 状态下生成 3 张 PNG（用 `verify_datahub_ui.py` 已验证的登录逻辑 + 详情页 URL 模板）
- [x] 3.3 验证 PNG 文件 < 1MB 且分辨率 ≥ 1280×720

## 4. notebook 改造

### 4.1 抽出第 7 节到 datahub_setup.ipynb

- [x] 4.1.1 新建 `notebook/datahub_setup.ipynb`：把 step1.ipynb 的 cell id `step1-20` 到 `step1-28` 整段（7.1~7.7）原样迁入
  - 第 1 个 cell 改为 markdown："本 notebook 面向 dev/运维，演示 DataHub 上报流程重跑；教学请看 `step1.ipynb`"
- [x] 4.1.2 `step1.ipynb` 删除 cell id `step1-20` 到 `step1-28`，替换为 1 个 markdown cell：「📘 开发者手册：见 `notebook/datahub_setup.ipynb`」

### 4.2 step1.ipynb 教学结构改造

- [x] 4.2.1 在 step1.ipynb 第 1 个 cell 前插入「痛点故事」markdown cell（≤ 200 中文字符）
  - 幕一无可视化：小王问 3 个同事得到 3 个不同表名 → 下载错表 → 用错字段被领导批评
  - 幕二有可视化：小王搜「煤质」→ 1 分钟定位到 lims/samples → 看到 Owner=煤质中心 + 质量分 88 + 0.5% 重复 → 决定二次确认
  - 文末小字提示：「如不喜欢此剧本可删除本 cell，不影响后续学习」
- [x] 4.2.2 在 step1.ipynb 顶部加 1 个 setup cell：
  - `import sys; sys.path.insert(0, '../src')`（让 notebook 能 `from dg_education import ...`）
  - `import pandas as pd, numpy as np, matplotlib.pyplot as plt`
  - `%matplotlib inline`
  - 字体配置（保留原 Noto Sans CJK JP）
- [x] 4.2.3 替换 step1.ipynb 第 1 节「5 系统接入表」：从 inline 表格改为 `from dg_education.catalog import SYSTEM_INFO; pd.DataFrame(SYSTEM_INFO).T`
- [x] 4.2.4 替换 step1.ipynb 第 2 节「资产目录」：从 inline `get_file_stats` 改为 `from dg_education.catalog import build_asset_catalog; df = build_asset_catalog(DATA_ROOT); display(df)`
- [x] 4.2.5 替换 step1.ipynb 第 2.1 节「存储分布可视化」：从 inline matplotlib 代码改为 `from dg_education.visualization import plot_storage_distribution; plot_storage_distribution(df)`
- [x] 4.2.6 替换 step1.ipynb 第 3 节「质量概览」：
  - 加载样本数据保留（`pd.read_parquet` 几行）
  - 检测改为 `from dg_education.quality import check_sap_quality, ...; sap_q = check_sap_quality(vbak, vbap, kna1)`
  - 评分卡改为 `from dg_education.quality import calc_quality_score; scores = calc_quality_score({...}); display(scores)`
  - 可视化改为 `plot_quality_scorecard(scores)`
- [x] 4.2.7 替换 step1.ipynb 第 4 节「安全分级」：从 inline DataFrame 改为 `from dg_education.catalog import SYSTEM_INFO; df_sec = pd.DataFrame([SYSTEM_INFO[s] for s in SYSTEM_INFO]); df_sec['级别'] = ...; display(df_sec)`
  - 可视化改为 `plot_security_levels()`
- [x] 4.2.8 替换 step1.ipynb 第 5 节「详细质量告警」：
  - 4 个 `check_*_quality(...)` 调用保留（输出数字）
  - 每条告警后追加 1 行 `print(format_business_impact_line('SAP.dup_vbak', 18_105_000, 0.00498))`，输出形如 `[业务影响] 18.1M × 0.498% ≈ 9 万条/年 × 5 分钟/条 = 7500 工时 ≈ 38 万元成本（行数取自 data/historical/，工时费率参考 Background.md 教学参考值）`
  - **关键**：在第 5 节顶部加 1 段 markdown 解释"以下数字是教学示意，单位成本为行业公开参考值；真实业务影响以 Background.md 为准"
- [x] 4.2.9 在第 6 节前新增「DataHub 是什么、怎么用」节（5 个 cell）：
  - 1 个 markdown 定义 cell（≤ 100 中文字）：DataHub = 公司级元数据中心，统一管理 5 系统的资产目录 / Owner / Schema / 血缘
  - 1 个 markdown 列举 cell：3 个最常用操作 = 搜资产 / 看 Owner / 看 Schema
  - 3 个 markdown 截图 cell（引用 `screenshots/datahub_{home,search,detail}.png`）
  - 1 个 markdown 边界 cell：明示"本 notebook 是离线分析（pandas 读 Parquet 算质量），DataHub UI 是线上协作（多人共享元数据）"
- [x] 4.2.10 重组 3 步学习节奏标题（在各节 markdown 顶部加粗 1 行）：
  - 第 1-2 节标"**步骤一：看见数据**"
  - 第 3-5 节标"**步骤二：判断数据可信**"
  - 第 6 节 + 原第 7 节"模块总结"标"**步骤三：用好数据**"
  - **注**：改叫"3 步学习节奏"而非"3 幕结构"（Tavily 验证：3 幕来自古典叙事学，不是技术培训标准）

### 4.3 收尾

- [x] 4.3.1 step1.ipynb 顶部加 1 个 markdown TOC：「本 notebook 章节与 `docs/Step1.md` 解耦；本 notebook 自带教学节奏，请以本 notebook 为准」
- [x] 4.3.2 jupyter nbconvert --clear-output 清空所有 cell 输出（提交前必做）
- [x] 4.3.3 验证 step1.ipynb cell 总数 ≤ 25（避免膨胀）

## 5. 端到端验证

- [x] 5.1 `jupyter nbconvert --to notebook --execute notebook/step1.ipynb`（自动跑通全本，exit code 0）
- [x] 5.2 `jupyter nbconvert --to notebook --execute notebook/datahub_setup.ipynb`（自动跑通全本，exit code 0）
- [x] 5.3 用 grep 验证 step1.ipynb 不含 OpenSearch / GMS 端点：
  - `grep -E "29200|/_bulk|/_delete_by_query|api/graphql" notebook/step1.ipynb` → 0 命中
  - `grep -E "subprocess.run|direct_es_bulk.py" notebook/step1.ipynb` → 0 命中
- [x] 5.4 用 grep 验证 step1.ipynb 至少 4 处 `[业务影响]` 注释（对应 4 系统的 TOP 告警）
- [x] 5.5 验证 step1.ipynb 至少含 1 张 `screenshots/datahub_*.png` 引用
- [x] 5.6 跑 `pytest src/dg_education/tests/` 全绿
- [x] 5.7 跑 `scripts/snapshot_datahub_ui.py` 重新生成 3 张 PNG，文件大小 100KB-1MB
- [x] 5.8 视觉抽查：随机抽 1 个 cell 的人类可读性，确认小白不会在 5 行 import + 10 行调用外看到 > 30 行的代码块

## 6. 回滚预案（仅在异常时执行；本变更全程未触发则全部 [x]）

- [x] 6.1 不满意改造效果 → `git checkout notebook/step1.ipynb` + 删 `notebook/datahub_setup.ipynb`（零数据丢失）
- [x] 6.2 截图失败 / DataHub 容器挂 → Idea 4（DataHub 介绍节）降级为纯文字 walkthrough，截图 markdown 引用改为「截图暂不可用，访问 http://localhost:29002 实时查看」
- [x] 6.3 业务影响数字争议 → `src/dg_education/business_impact.py` 中 `COST_TABLE` 改为可配置（YAML/TOML），用户改值即可，不动代码
- [x] 6.4 step1.ipynb 改造后跑挂 → 用 `notebook/step1.ipynb.bak.YYYYMMDD` 还原，定位失败 cell
