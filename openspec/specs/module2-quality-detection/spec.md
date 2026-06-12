## ADDED Requirements

### Requirement: module2.ipynb 必须以「痛点故事」cell 开头

`notebook/module2.ipynb` 的第一个 cell MUST 是一个 markdown cell，包含一段两幕对照的"痛点故事"，用于向小白回答"为什么需要根因定位"。

幕一 MUST 描述**只能看到评分**时的痛点场景（如：知道 SAP 评分 C 等级，但不知道具体是哪些订单/哪些列出问题，找开发排查要 2 天）。
幕二 MUST 描述**有根因定位**时的顺利场景（在 notebook 中 5 分钟内定位到 SAP VBAP 孤儿行的具体订单号、PI 异常突升的传感器编号）。

两幕对照 MUST 在同一 cell 内呈现。剧本长度 MUST 控制在 200 中文字符以内。

#### Scenario: 痛点故事 cell 存在并位于第一位
- **WHEN** 在 jupyter 中打开 `notebook/module2.ipynb` 并查看第 1 个 cell
- **THEN** 该 cell MUST 是 markdown 类型，且 MUST 包含 "幕一" 与 "幕二" 两个标签

#### Scenario: 故事中包含具体角色与冲突
- **WHEN** 阅读该 cell 的内容
- **THEN** 幕一 MUST 至少包含 1 个具体痛点（如"找 2 天"或"不知道哪些订单"），幕二 MUST 至少包含 1 个具体正向收益（如"5 分钟定位"或"具体订单号"）

#### Scenario: 故事长度可控
- **WHEN** 统计该 cell 的中文字符数
- **THEN** 总字符数 MUST < 200

### Requirement: module2.ipynb 不得包含 OpenSearch 或 GMS GraphQL 开发者脚本

`notebook/module2.ipynb` MUST NOT 包含任何直接调用 OpenSearch REST API、GMS GraphQL、subprocess.run 调用 `scripts/direct_es_bulk.py` 的代码 cell。

教学 notebook 的代码 MUST 局限于读取 `data/historical/` 下的 Parquet 文件、用 pandas/matplotlib 做离线分析、以及通过 `dg_education.ge_scan` 子进程调用 `scripts/run_great_expectations.py` 生成 GE 报告。

#### Scenario: 全文搜索不应命中 ES/GraphQL 端点
- **WHEN** 在 `notebook/module2.ipynb` 全文搜索 `29200` 或 `/api/graphql` 或 `_delete_by_query` 或 `_bulk`
- **THEN** MUST 0 命中

#### Scenario: 不得包含上报相关的 subprocess 调用
- **WHEN** 在 `notebook/module2.ipynb` 全文搜索 `direct_es_bulk.py` 或 `emit_browsepaths.py` 或 `emit_lineage.py`
- **THEN** MUST 0 命中

#### Scenario: 仅允许调用 run_great_expectations.py 一个脚本
- **WHEN** 在 `notebook/module2.ipynb` 全文搜索 `subprocess`
- **THEN** 所有命中 MUST 仅指向 `run_great_expectations.py`，MUST NOT 包含其他 scripts/ 下的脚本

### Requirement: module2.ipynb 末尾必须引用 module1.ipynb

`notebook/module2.ipynb` 的最后 1-3 个 cell 之一 MUST 包含 1 行 markdown 引用 `notebook/module1.ipynb`，让小白知道模块二与模块一的关系（模块一是看资产，模块二是找问题）。

#### Scenario: 末尾包含 module1 引用
- **WHEN** 打开 `notebook/module2.ipynb` 查看最后一个 cell 或最末几 cell 之一
- **THEN** MUST 包含 1 行 markdown 引用 `notebook/module1.ipynb`

### Requirement: module2.ipynb 根因分析每条告警必须配「业务影响」白话翻译

`notebook/module2.ipynb` 第 2 节（4 类根因定位）每条主要告警（如 SAP `invalid_link_pct`、PI `missing_pct`、PI `wagas_anomaly_pct`、LIMS `ad_outlier_pct`）MUST 在根因分析结果后追加 1 段「业务影响」文字注释。

「业务影响」注释 MUST 包含 3 个要素：
1. 影响的行数 / 标签数 / 样品数（具体数字）
2. 1 句白话解释（业务上意味着什么）
3. 责任部门归属（参考 `src/dg_education/catalog.py` 的 SYSTEM_INFO）

#### Scenario: SAP 孤儿行根因后必含业务影响
- **WHEN** 运行 `analyze_vbap_invalid_links` 后
- **THEN** MUST 在同一 cell 或紧随 cell 展示 1 段文字，包含：影响行数、物料前缀分布 Top 3、责任部门=销售部

#### Scenario: PI 缺失根因后必含业务影响
- **WHEN** 运行 `analyze_pi_missing_tags` 后
- **THEN** MUST 在同一 cell 或紧随 cell 展示 1 段文字，包含：影响标签数 Top 5、责任部门=安全部

#### Scenario: PI 异常突升根因后必含业务影响
- **WHEN** 运行 `analyze_pi_anomalies` 后
- **THEN** MUST 展示 1 段文字，说明"传感器异常 vs 真实异常"的判断方法、责任部门=安全部

#### Scenario: LIMS 灰分异常根因后必含业务影响
- **WHEN** 运行 `analyze_lims_ad_outliers` 后
- **THEN** MUST 展示 1 段文字，包含：影响样品数、煤种分布 Top 3、责任部门=煤质中心

### Requirement: module2.ipynb 必须使用 2022 年全量数据

`notebook/module2.ipynb` 的数据加载 MUST 读取 2022 年全量 Parquet，不使用 2023 年样本数据。

具体路径：
- `data/historical/sap_erp/vbak_year=2022.parquet`
- `data/historical/sap_erp/vbap_year=2022.parquet`
- `data/historical/sap_erp/kna1.parquet`
- `data/historical/pi_system/tags_year=2022_month=01.parquet`（根因分析时只加载 1 月）
- `data/historical/lims/samples_year=2022.parquet`
- `data/historical/oa/doc_flow_year=2022.parquet`

#### Scenario: 数据路径均为 2022
- **WHEN** 在 `notebook/module2.ipynb` 全文搜索 `year=2023`
- **THEN** MUST 0 命中

#### Scenario: PI 根因分析只加载 1 月数据
- **WHEN** 在 `notebook/module2.ipynb` 全文搜索 `tags_year=2022_month`
- **THEN** MUST 仅出现 `month=01` 的引用（不得出现 month=02-12）
