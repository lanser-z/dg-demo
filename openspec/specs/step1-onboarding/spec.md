# step1-onboarding Specification

## Purpose
TBD - created by archiving change improve-step1-notebook-onboarding. Update Purpose after archive.
## Requirements

### Requirement: module1.ipynb 必须以「痛点故事」cell 开头

`notebook/module1.ipynb` 的第一个 cell MUST 是一个 markdown cell，包含一段两幕对照的"痛点故事"，用于向小白回答"为什么需要数据资产可视化"。

幕一 MUST 描述**没有可视化**时一个具体角色的痛点场景（如新员工找数据时遇到的具体困难：问 3 个同事得到 3 个不同答案、下载错表、用错字段被领导批评等）。
幕二 MUST 描述**有可视化**时同一角色的顺利场景（在 notebook 中 1 分钟内定位到正确表，并附带看到 Owner / 质量分等关键信息）。

两幕对照 MUST 在同一 cell 内呈现，让读者一眼能感知差异。剧本长度 MUST 控制在 200 中文字符以内（避免拖沓）。

#### Scenario: 痛点故事 cell 存在并位于第一位
- **WHEN** 在 jupyter 中打开 `notebook/module1.ipynb` 并查看第 1 个 cell
- **THEN** 该 cell MUST 是 markdown 类型，且 MUST 包含 "幕一" 与 "幕二" 两个标签

#### Scenario: 故事中包含具体角色与冲突
- **WHEN** 阅读该 cell 的内容
- **THEN** 幕一 MUST 至少包含 1 个具体痛点（如"下载错表"或"被领导批评"），幕二 MUST 至少包含 1 个具体正向收益（如"1 分钟定位"或"看到 Owner"）

#### Scenario: 故事长度可控
- **WHEN** 统计该 cell 的中文字符数
- **THEN** 总字符数 MUST < 200

### Requirement: module1.ipynb 不得包含 OpenSearch 或 GMS GraphQL 开发者脚本

`notebook/module1.ipynb` MUST NOT 包含任何直接调用 OpenSearch REST API（如 `POST /_delete_by_query`、`POST /_bulk`）或 GMS GraphQL（如 `POST /api/graphql` 的 `browse` / `searchAcrossEntities` 查询）的代码 cell。

教学 notebook 的代码 MUST 局限于读取 `data/historical/` 下的 Parquet 文件并用 pandas/matplotlib 做离线分析。所有 OpenSearch / GraphQL 操作 MUST 在独立的 `notebook/datahub_setup.ipynb` 中。

#### Scenario: 全文搜索不应命中 ES/GraphQL 端点
- **WHEN** 在 `notebook/module1.ipynb` 全文搜索 `29200` 或 `/api/graphql` 或 `_delete_by_query` 或 `_bulk`
- **THEN** MUST 0 命中

#### Scenario: 不应包含 dev 上报相关 subprocess 调用
- **WHEN** 在 `notebook/module1.ipynb` 全文搜索 `subprocess.run` 或 `direct_es_bulk.py`
- **THEN** MUST 0 命中

#### Scenario: 末尾必须含 1 行引用 datahub_setup.ipynb
- **WHEN** 打开 `notebook/module1.ipynb` 查看最后一个 cell 或最末几 cell 之一
- **THEN** MUST 包含 1 行 markdown 引用 `notebook/datahub_setup.ipynb`（如「开发者手册：见 `datahub_setup.ipynb`」），让 dev 知道去哪里重跑上报

### Requirement: 质量告警章节每条告警必须配 `[业务影响]` 翻译

`notebook/module1.ipynb` 第 5 节（详细质量告警）每条主要告警（如 SAP `dup_vbak`、PI `wagas_danger_pct`、LIMS `ad_outlier_pct`、OA `dup_pct` 等）MUST 在检测结果后追加 1 行 `[业务影响]` 文本注释。

`[业务影响]` 注释 MUST 包含 3 个要素：
1. **年发生量**：由对应表的实际行数（`len(df)`）与注入率（脚本生成的 0.5% / 0.498% 等）相乘得出
2. **单位成本**：来自 `docs/Background.md` 的业务场景（工时费率 / 煤价 / 事故代价等）
3. **影响金额或代价**：年发生量 × 单位成本

注释 MUST 显式标注"行数取自 `data/historical/` 实际数据"和"单位成本参考 `docs/Background.md`"，确保小白可追溯。

#### Scenario: 每条 TOP 告警都有 [业务影响] 注释
- **WHEN** 打开 module1.ipynb 第 5 节，逐条查看 SAP-ERP / PI-System / LIMS / OA 四个子节的告警
- **THEN** 每条 TOP 告警后 MUST 至少有 1 行以 `[业务影响]` 开头的文本

#### Scenario: 注释使用行数 × 注入率 × 单位成本公式
- **WHEN** 检查任意 1 条 `[业务影响]` 注释的内容
- **THEN** MUST 显式出现"行数"与"注入率"与"单位成本"中至少 2 个的算式关系

#### Scenario: 注释标注数据来源
- **WHEN** 检查任意 1 条 `[业务影响]` 注释
- **THEN** MUST 含 1 处对 `data/historical/` 或 `docs/Background.md` 的引用

### Requirement: module1.ipynb 必须包含「DataHub 是什么、怎么用」节

`notebook/module1.ipynb` MUST 在第 6 节（模块总结）前新增 1 节「DataHub 是什么、怎么用、与本 notebook 的关系」。

该节 MUST 至少包含 4 个要素：
1. **DataHub 定义**：1 段话（≤ 100 中文字）说明 DataHub 是公司级元数据中心、用于元数据治理
2. **3 个最常用操作**：列点说明"搜资产 / 看 Owner / 看 Schema"是 DataHub UI 的高频操作
3. **与本 notebook 的边界**：明确本 notebook 是离线分析、DataHub UI 是线上协作平台，二者互补不冲突
4. **UI 截图引用**：1~3 张 `screenshots/datahub_*.png` 的 markdown 引用（截图脚本生成的 PNG 文件）

#### Scenario: 存在 DataHub 介绍节
- **WHEN** 在 module1.ipynb 全文搜索 `## DataHub` 或 `DataHub 是什么`
- **THEN** MUST 命中至少 1 处

#### Scenario: 介绍节包含 3 个核心操作
- **WHEN** 阅读该节内容
- **THEN** MUST 出现"搜资产"与"看 Owner"与"看 Schema"（或同义表达如"搜索资产"/"查看负责人"/"查看字段"）

#### Scenario: 介绍节有边界说明
- **WHEN** 阅读该节内容
- **THEN** MUST 含 1 句明示"本 notebook（离线分析）与 DataHub UI（线上协作）的边界"

#### Scenario: 介绍节有截图引用
- **WHEN** 阅读该节 markdown
- **THEN** MUST 含 1~3 处 `![datahub_*](screenshots/datahub_*.png)` 格式的相对路径引用

### Requirement: datahub_setup.ipynb 必须包含完整 dev 上报流程

`notebook/datahub_setup.ipynb` MUST 是一个独立的开发者用 notebook，包含 module1.ipynb 改造前第 7.1~7.7 全部内容：服务状态确认、清除 OpenSearch、调用 `scripts/direct_es_bulk.py`、验证 ES count、验证 GraphQL browse、验证 GraphQL search。

该 notebook MUST 在第 1 个 cell 包含 1 段开发者说明（不是教学材料，仅供 dev/运维 跑通数据上报流程）。

#### Scenario: datahub_setup.ipynb 存在且 cell 数 ≥ 8
- **WHEN** 执行 `jupyter nbconvert --to script notebook/datahub_setup.ipynb --stdout | grep -c "^# In\[`
- **THEN** MUST ≥ 8 个 cell（1 个 markdown 说明 + 7 个原 module1.ipynb 第 7.1~7.7 cell）

#### Scenario: 包含 dev 上报流程关键步骤
- **WHEN** 在 `notebook/datahub_setup.ipynb` 全文搜索以下关键词
- **THEN** 每个 MUST 至少命中 1 次：
  - `direct_es_bulk.py`（调用上报脚本）
  - `_delete_by_query`（清空 OpenSearch）
  - `searchAcrossEntities`（验证搜索）
  - `browse`（验证 Browse 树）

#### Scenario: 顶部含开发者说明
- **WHEN** 阅读 `notebook/datahub_setup.ipynb` 第 1 个 cell
- **THEN** MUST 是 markdown 类型且含 1 句"本 notebook 面向 dev/运维"或同义说明
