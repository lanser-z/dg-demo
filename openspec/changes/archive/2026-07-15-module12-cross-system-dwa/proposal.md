## Why

当前 3 张 DWA 宽表（dwa_sales_daily / dwa_tag_alarm / dwa_coal_quality）都基于单系统 DWD，无法回答"某矿井某日销售订单对应的生产量、煤质、客户"这种跨主题问题。6.12 目标是把 6.11 主题域重组的回报兑现：建 1 张 4 表 JOIN 跨系统宽表 `dwa_sales_production`，用 DuckDB（已在依赖中）替代 ClickHouse/Doris，避免 5+ 分钟 Docker 启动。

## What Changes

- **新增 `scripts/build_dwa_sales_production.py`**：DuckDB 4 表 LEFT JOIN 跨主题，写入 `data/lakehouse/dwa/dwa_sales_production/` Delta Lake
- **新增宽表**：`dwa_sales_production` 字段含 VBELN/ERDAT/KUNNR/NAME1（sales）+ mine/face/avg_production（production）+ AD/QGR_AD（coal_quality）
- **保留 3 张旧 DWA 宽表**：sales_daily / tag_alarm / coal_quality 仍可用，6.12 是 additive
- **保留** 旧 3 个 DWA 宽表的 `dwd/{system}/` 上游（6.11 设计已声明），但 `dwa_sales_production` 走新 subject-分区
- **新增** `notebook/module12.ipynb` 3 cells 演示
- **新增** `docs/Module12.md` + Background.md §6.12 状态更新
- **DWA 上游切换**：`build_dwa_models.py` 中 3 个旧 DWA 函数的 SQL 引用从 `dwd/{system}/*` 切换到 `dwd/{sales,production,coal_quality}/*`（按 6.11 delta 承诺，6.12 实施）

## Capabilities

### New Capabilities
- `cross-system-dwa`: 跨系统 4 表 JOIN 宽表（dwa_sales_production）+ DuckDB 物化视图模拟

### Modified Capabilities
- `dwa-coal-quality`: 上游路径从 `dwd/lims/dwd_samples/` 切换到 `dwd/coal_quality/dwd_samples/`（6.11 delta 承诺 6.12 实施）
- `dwa-sales-daily`: 上游路径从 `dwd/sap_erp/dwd_vbak/` 切换到 `dwd/sales/dwd_vbak/`
- `dwa-tag-alarm`: 上游路径从 `dwd/pi_system/dwd_tags/` 切换到 `dwd/production/dwd_tags/`
- `data-lineage-ingestion`: 增加"4 表 JOIN 跨主题宽表 lineage 边"需求

## Impact

- **代码**：
  - 新增 `scripts/build_dwa_sales_production.py`（~100 行）
  - 改 `scripts/build_dwa_models.py`：3 个 DWA 函数的 SQL 引用切换到 subject-分区
- **数据**：新增 `data/lakehouse/dwa/dwa_sales_production/`（Delta Lake 格式，被 .gitignore 排除）
- **依赖**：无新增（duckdb 已在 pyproject.toml）
- **文档**：
  - `docs/Module12.md` 新增
  - `docs/Background.md §6.12` 状态更新
  - `README.md` 路径 B notebook 列表：加 `module12.ipynb`（**影响学习路径 B**）
- **回滚**（≤ 30 分钟）：
  1. `rm -rf data/lakehouse/dwa/dwa_sales_production/`
  2. `rm scripts/build_dwa_sales_production.py notebook/module12.ipynb`
  3. `git checkout HEAD~1 -- scripts/build_dwa_models.py`（恢复 3 个旧 DWA 上游路径）
  4. 旧 DWA 宽表完全不动
