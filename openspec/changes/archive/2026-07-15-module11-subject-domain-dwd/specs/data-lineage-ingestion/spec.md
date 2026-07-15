# data-lineage-ingestion Specification (delta)

## ADDED Requirements

### Requirement: 主题域重组后 dual-write 模式

`scripts/emit_lineage.py` 与 `lineage_recipe.yaml` 在 6.11 引入主题域 DWD 重组后 MUST 同时支持新旧两套路径的 lineage emit。两套 lineage 在 GMS 索引中按 `(dataset, upstream)` 唯一键去重；DataHub UI MUST 同时展示两套视图。

#### Scenario: 新旧同名 dataset 共存
- **WHEN** 6.11 变更归档后跑 `uv run python scripts/emit_lineage.py`（写旧 system-分区 lineage）
- **THEN** GMS OpenSearch `datasetindex_v2` 索引 MUST 同时含 `urn:li:dataset:(urn:li:dataPlatform:sap_erp,dwd_vbak,PROD)` 与 `urn:li:dataset:(urn:li:dataPlatform:dwd,dwd.sales.dwd_vbak,PROD)` 两条 dataset 记录

#### Scenario: lineage 边对应正确 platform
- **WHEN** 查 GMS dataJobInputOutput aspect
- **THEN** ingest_dwd job 的 inputDatasetEdges MUST 同时含旧 system-分区的 source 与新 subject-分区的 source（如有）

#### Scenario: 双通道去重仍工作
- **WHEN** 同一对 `dataset + upstream` 同时出现在两套平台
- **THEN** GMS OpenSearch 索引按 `dataset_urn` 唯一（不同 platform 算不同 dataset，所以**不去重**——这是预期行为）
