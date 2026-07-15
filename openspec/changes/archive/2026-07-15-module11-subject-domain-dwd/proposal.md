## Why

当前 DWD 层按源系统分区（`dwd/sap_erp/`、`dwd/pi_system/`、`dwd/lims/`、`dwd/oa/`），跨系统业务 JOIN（如 SAP 销售订单 ↔ LIMS 煤质）需要跨目录写复杂 WHERE 条件。6.11 目标是把 DWD 层按业务主题重组（`sales/`、`production/`、`coal_quality/`、`finance/`），让跨系统同主题数据自然落在同目录下，演示阶段 dual-write 保留旧布局。

## What Changes

- **新增 `scripts/restructure_dwd.py`**：读 `dwd/{system}/`，写 `dwd/{subject}/`，dual-write 保留旧表
- **新增主题目录**：`dwd/sales/`（vbak/vbap/kna1）、`dwd/production/`（tags）、`dwd/coal_quality/`（samples）、`dwd/finance/`（doc_flow）
- **保留** `dwd/_dimensions/`（dim_mine/customer/material 全局共享，不重分类）
- **DataHub 集成**：注册 `dwd` 自定义 platform，emitter emit 新主题表的 datasetKey + upstreamLineage aspect
- **新增** `notebook/module11.ipynb` 3 cells 演示
- **新增** `docs/Module11.md` + `docs/Background.md §6.11` 状态

## Capabilities

### New Capabilities
- `subject-domain-dwd`: 主题域 DWD 目录重组（sales/production/coal_quality/finance）

### Modified Capabilities
- `data-lineage-ingestion`: 增加"主题域重组后 dual-write 模式"需求
- `dwa-coal-quality` / `dwa-sales-daily` / `dwa-tag-alarm`: 标记 DWA 上游路径从 system-分区改为 subject-分区（演示阶段 DWA 仍读旧路径，6.12 改）

## Impact

- **代码**：新增 `scripts/restructure_dwd.py`（~80 行）
- **数据**：
  - `data/lakehouse/dwd/sales/` 新增（vbak/vbap/kna1 三个表）
  - `data/lakehouse/dwd/production/` 新增（tags）
  - `data/lakehouse/dwd/coal_quality/` 新增（samples）
  - `data/lakehouse/dwd/finance/` 新增（doc_flow）
  - 旧 `dwd/{system}/` 保留
- **DataHub**：注册新 `dwd` platform；emit 6 张新表的 datasetKey + upstreamLineage aspect
- **文档**：`docs/Module11.md` 新增；`docs/Background.md §6.11` 状态更新；`README.md` path B 路径加 `module11.ipynb`（**影响学习路径 B**）
- **回滚**（≤ 30 分钟）：
  1. `rm -rf data/lakehouse/dwd/{sales,production,coal_quality,finance}`
  2. `rm scripts/restructure_dwd.py notebook/module11.ipynb`
  3. DataHub 用 datahub CLI `datahub delete` 6 张新表
  4. 旧布局完全不动
