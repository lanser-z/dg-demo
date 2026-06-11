## Why

`notebook/step1.ipynb` 当前是「开发者写给开发者的成果展示」，但项目定位是「给小白软件工程师的数据治理教学环境」。小白看完整本 notebook，能知道"做了什么"，但说不出来"这是什么、为什么做、怎么用"——本变更把 notebook 从"成果展示"重构为"教学产品"。

## What Changes

- **修改** `notebook/step1.ipynb`：
  - 在第 1 节前新增一个 markdown cell 写「痛点故事」剧本（无/有可视化对照）
  - 在第 5 节（详细质量告警）每条告警后追加 `[业务影响]` 一行白话翻译
  - 在第 6 节（模块总结）前新增一节「DataHub 是什么、怎么用、与 notebook 的关系」（含 UI 截图、3 个最常用操作）
  - 移除原第 7.1~7.7（re-upload DataHub 脚本演示），替换为一行引用 `notebook/datahub_setup.ipynb`
- **新增** `notebook/datahub_setup.ipynb`：把原 step1.ipynb 第 7.1~7.7 内容（服务状态确认、清空 OpenSearch、调用 `direct_es_bulk.py`、验证 ES、验证 Browse、验证搜索）迁过来，供 dev/运维重跑数据上报流程

无破坏性变更（BREAKING）。notebook 是教学材料，不影响生产路径；旧 step1.ipynb 的第 7 节内容被搬走，外部脚本/数据不动。

## Capabilities

### New Capabilities

- `step1-onboarding`: 小白友好的 step1.ipynb 教学结构与内容，包含痛点故事、业务影响白话翻译、DataHub UI walkthrough。规范层级描述 step1 notebook 的内容要求与教学节奏。

### Modified Capabilities

（无。`openspec/specs/` 中现有 `datahub-service-startup` 与 `asset-metadata-ingestion` 是基础设施 spec，描述 DataHub 容器与元数据接入；本变更不涉及它们的 REQUIREMENTS 变更。）

## Impact

| 类别 | 受影响项 | 说明 |
|------|----------|------|
| **教学材料** | `notebook/step1.ipynb` | 主体变更：加 3 段（痛点故事 / 业务影响 / DataHub 介绍），删 1 段（第 7.1~7.7） |
| **新增材料** | `notebook/datahub_setup.ipynb` | 从 step1.ipynb 抽出的 dev/运维用 notebook（重跑上报） |
| **外部依赖** | 无 | 不动 `datahub-quickstart.yml` / 容器 / 脚本 / DataHub SDK |
| **数据** | `data/` 完全不动 | 本变更不触发生成或上报 |
| **文档** | `docs/*.md` 不动 | 符合 CLAUDE.md 硬约束；后续如需把"业务影响换算表"沉淀到 Background.md，可单开 change |
| **截图依赖** | `screenshots/` 需新增 1~3 张 DataHub UI 截图 | Idea 4 需要，已 gitignore，不入库 |

## 回滚计划

| 回滚点 | 触发条件 | 操作 | 数据影响 |
|--------|----------|------|----------|
| **R1：notebook 不满意** | 改造后小白反馈"反而看不懂了" / cell 顺序不顺 | `git checkout notebook/step1.ipynb` + 删除新增的 `notebook/datahub_setup.ipynb` | 零（notebook 不生产数据） |
| **R2：部分保留** | 第 7 节迁出引发"新人找不到 dev 教程" | 把 `datahub_setup.ipynb` 内容回填到 `step1.ipynb` 末尾 | 零 |
| **R3：截图失败** | DataHub UI 截图截图时容器挂了 | Idea 4 退化为"纯文字 walkthrough + UI URL"，不阻断整体变更 | 零 |

**回滚 SLA**：所有回滚 1 分钟内完成（git checkout + rm）。`data/` 与 DataHub 容器在变更期间持续运行，不受 notebook 改造影响。

## 不在本变更范围

- 血缘数据上报（`scripts/emit_lineage.py` 走 GMS OpenAPI）—— 后续单独 change
- Great Expectations 质量规则实际运行（`scripts/run_great_expectations.py`）—— 已存在，本变更不触发
- Delta Lake 入湖 / DuckDB DWA 宽表 —— 与本教学改造无关
- step0.ipynb / step2+ notebook 的改造 —— 本期只动 step1
- `docs/Background.md` 中"业务影响换算"沉淀 —— 需用户对真实业务量级 sign-off，单开 change
- Idea 5/6（Schema preview / 教学小结卡）—— 列为 Phase 2 等待观察
