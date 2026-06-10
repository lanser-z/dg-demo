# asset-metadata-ingestion Specification

## Purpose
TBD - created by archiving change setup-datahub-and-load-data. Update Purpose after archive.
## Requirements
### Requirement: 12 张表被识别为 dataset 实体
`data/historical/` 下的 12 张 Parquet 表 MUST 被上报为 DataHub dataset 实体，URN 格式为 `urn:li:dataset:(urn:li:dataPlatform:<system>,<table_name>,PROD)`。

涉及的 12 张表：

| 系统 | 表名 | 中文名 |
|------|------|--------|
| sap_erp | vbak | 销售订单抬头 |
| sap_erp | vbap | 销售订单行项目 |
| sap_erp | kna1 | 客户主数据 |
| sap_erp | likp | 交货单抬头 |
| sap_erp | lips | 交货单行项目 |
| sap_erp | mara | 物料主数据 |
| pi_system | tags | PI 时序标签数据 |
| lims | samples | 煤质化验样品 |
| oa | doc_flow | 文档流转记录 |
| oa | contract | 合同记录 |
| oa | meeting | 会议记录 |
| scada | equipment_status | 设备状态 |

#### Scenario: 12 张表均在 OpenSearch datasetindex_v2 中
- **WHEN** 执行 `curl -s "http://localhost:29200/datasetindex_v2/_count"`
- **THEN** 返回的 `count` MUST ≥ 12

#### Scenario: URN 命名符合规范
- **WHEN** 任选一张表（如 `lims/samples`）查询其 URN
- **THEN** URN MUST 形如 `urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)`（小写 platform 与 name）

### Requirement: 每张表有中文描述与所属 Owner
每条 dataset MUST 包含中文描述（来自 `Background.md` 表名说明）与对应 Owner（sap_erp 销售部、pi_system 安全部、lims 煤质中心、oa 综合管理部、scada 安全部）。

#### Scenario: 描述与 Owner 写入
- **WHEN** 执行 `scripts/direct_es_bulk.py` 后再执行 `scripts/emit_browsepaths.py`
- **THEN** OpenSearch `datasetindex_v2` 中 `_source` MUST 包含非空 `description` 字段与 ownership 信息

### Requirement: Browse 路径为 `<system>/<table_name>`
每张 dataset 的 browsePathV2 MUST 形如 `/{system}/{table_name}`，使 DataHub UI 左侧 Browse 树能按系统分组。

#### Scenario: Browse 路径正确写入
- **WHEN** 执行 `scripts/check_browse.py` 验证
- **THEN** 全部 12 张表 MUST 输出 `✅` 标记且 browsePath 形如 `/sap_erp/vbak`、`/lims/samples`

#### Scenario: UI 搜索可见 5 系统分组
- **WHEN** 浏览器在 http://localhost:29002 全局搜索框输入 `*`（或空查询）后回车
- **THEN** 搜索结果 MUST 包含 5 个系统分组（sap_erp、pi_system、lims、oa、scada）下的 12 张表（因 `SHOW_BROWSE_V2=false`，左侧 Browse 树不可用，资产可见性通过搜索结果页与详情页验证）

### Requirement: 资产卡可见元数据
DataHub UI 上点击任一 dataset 资产卡，MUST 看到数据集的描述、Owner、所属 platform、Tags 至少一项。

#### Scenario: 资产详情页正常
- **WHEN** 浏览器打开 http://localhost:29002/dataset/urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)
- **THEN** 页面 MUST 显示名称"samples"、中文描述"煤质化验样品"、Owner"煤质中心"（或对应中文名），不出现 404 或加载失败

### Requirement: 资产能被搜索
DataHub 全局搜索框输入系统名（如 "lims"）或表名（如 "samples"）MUST 能搜到对应 dataset。

#### Scenario: 搜索命中
- **WHEN** 浏览器在搜索框输入 "lims" 后回车
- **THEN** 搜索结果 MUST 包含 `lims/samples`，且点击进入资产详情页

### Requirement: 上报可重复执行
`scripts/direct_es_bulk.py` 与 `scripts/emit_browsepaths.py` MUST 支持幂等执行：重复运行不会产生重复 URN 或冲突，且能补全上次漏掉的部分。

#### Scenario: 重复运行不报错
- **WHEN** 连续执行 2 次 `direct_es_bulk.py`
- **THEN** 两次执行 MUST 都不抛异常，OpenSearch 中 `datasetindex_v2` 文档数仍为 12（不是 24）

