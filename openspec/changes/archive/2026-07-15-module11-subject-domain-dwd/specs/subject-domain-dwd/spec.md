# subject-domain-dwd Specification

## Purpose

把 `data/lakehouse/dwd/` 从"按源系统分区"（`sap_erp/`/`pi_system/`/`lims/`/`oa/`）重组为"按业务主题分区"（`sales/`/`production/`/`coal_quality/`/`finance/`），dual-write 保留旧布局。覆盖 ETL 脚本、DataHub 集成、教学 notebook。

## ADDED Requirements

### Requirement: scripts/restructure_dwd.py 实现 dual-write ETL

`scripts/restructure_dwd.py` MUST 读取 `data/lakehouse/dwd/{sap_erp,pi_system,lims,oa}/{table}/` 下的 Delta Lake 表，写入 `data/lakehouse/dwd/{sales,production,coal_quality,finance}/{table}/`，保留旧 system-分区不变。表名不变（`dwd_vbak` 等保留原名）。

#### Scenario: sales 主题跨 3 表写入
- **WHEN** 执行 `uv run python scripts/restructure_dwd.py`（默认行为）
- **THEN** 读 `dwd/sap_erp/dwd_vbak/`、`dwd/sap_erp/dwd_vbap/`、`dwd/sap_erp/dwd_kna1/` 三表，分别写入 `dwd/sales/dwd_vbak/`、`dwd/sales/dwd_vbap/`、`dwd/sales/dwd_kna1/`，且旧 system-分区**未被修改**

#### Scenario: 4 主题 6 表全部 dual-write
- **WHEN** 跑完脚本
- **THEN** 验证 `data/lakehouse/dwd/{sales,production,coal_quality,finance}/` 下每个目录都有 `_delta_log` 与 parquet 文件，且 `data/lakehouse/dwd/{sap_erp,pi_system,lims,oa}/` 原文件未变化

#### Scenario: dry-run 模式
- **WHEN** 执行 `uv run python scripts/restructure_dwd.py --dry-run`
- **THEN** 仅打印"将写入 X 行到 dwd/sales/dwd_vbak"等计划，不实际写文件

### Requirement: dim 表保留在 _dimensions/

`data/lakehouse/dwd/_dimensions/` 下的 `dim_mine/`、`dim_customer/`、`dim_material/` MUST NOT 被重组到 subject 目录；维度表全局共享，不属于任何单一业务域。

#### Scenario: _dimensions 不变
- **WHEN** 跑 `restructure_dwd.py` 后
- **THEN** `data/lakehouse/dwd/_dimensions/` 仍含 dim_mine/dim_customer/dim_material 三个子目录，路径与大小不变

#### Scenario: 文档说明维度共享
- **WHEN** 阅读 `docs/Module11.md` 第 2 节
- **THEN** MUST 含一段说明"dim_* 是跨域共享维度，不跟随业务域重分类" + 为什么（避免学员误操作）

### Requirement: DataHub 注册 dwd 自定义 platform 与新主题表 lineage

实施完成后 DataHub MUST 含 6 张新主题表的 `datasetKey` aspect（旧 system-分区的表保留 lineage）。自定义 platform `dwd` MUST 通过 SDK 注册。

#### Scenario: dwd platform 已注册
- **WHEN** 检查 DataHub 平台列表
- **THEN** MUST 含 platform 名 `dwd`，display name `DWD`（Detail Data Layer）

#### Scenario: 6 张新主题表 datasetKey 已写入
- **WHEN** 通过 `curl http://localhost:28080/aspects/urn:li:dataset:(urn:li:dataPlatform:dwd,dwd.sales.dwd_vbak,PROD)?aspect=datasetKey` 查
- **THEN** MUST 返回 datasetKey aspect（不返回 500）

#### Scenario: lineage 边存在
- **WHEN** `python scripts/verify_auto_lineage.py`（6.10 写的脚本）跑
- **THEN** 6 个 ETL job（ingest_dwd + 5 个 dwa/dim job）的 dataJobInputOutput 边继续存在；新主题表通过 datasetKey 索引可在 DataHub UI 浏览

### Requirement: notebook module11.ipynb 3 cells 演示

`notebook/module11.ipynb` MUST 含 3 cells：1) 列出新旧 DWD 目录结构对比；2) DuckDB 查新主题 `dwd/sales/dwd_vbak` 行数（应与旧 `dwd/sap_erp/dwd_vbak` 一致）；3) DataHub UI 截图（Playwright 抓 `dwd > sales > dwd_vbak` 树形浏览）。

#### Scenario: cell 1 目录结构输出
- **WHEN** 执行 cell 1
- **THEN** MUST 输出新旧两棵树（`dwd/sap_erp/` vs `dwd/sales/`）共 6 张表的位置对照

#### Scenario: cell 2 行数一致
- **WHEN** 用 DuckDB 查 `dwd/sales/dwd_vbak` 与 `dwd/sap_erp/dwd_vbak`
- **THEN** 两个查询返回的 `count(*)` MUST 相等

#### Scenario: cell 3 Playwright 截图
- **WHEN** cell 3 跑
- **THEN** 生成 `notebook/step_images/module11_subject_dwd.png`，含 DataHub UI 的 dwd > sales 树形浏览
