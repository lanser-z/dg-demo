# data-lineage-ingestion Specification (delta)

## ADDED Requirements

### Requirement: lineage_recipe.yaml 与 auto-lineage-collection 通道并存

`lineage_recipe.yaml` 在 6.9 引入 `auto-lineage-collection` capability 后 MUST 继续作为**业务跨系统 JOIN 边**的兜底通道，与 `auto-lineage-collection` 自动通道并存。`lineage_recipe.yaml` 中声明的边（业务血缘 + 加工血缘）由 `scripts/emit_lineage.py` 手工写入；auto 通道的边由 ETL 任务 emit；两通道写入的边在 GMS 索引中按 `(dataset, upstream)` 唯一键去重，DataHub UI MUST 仅展示 1 条。

#### Scenario: 手工通道 8 条边继续工作
- **WHEN** 6.9 变更归档后执行 `uv run python scripts/emit_lineage.py`
- **THEN** MUST 成功写入 `lineage_recipe.yaml` 中所有 8 条边到 GMS `upstreamLineage` aspect，无 `auto-lineage-collection` 通道干扰

#### Scenario: 双通道去重
- **WHEN** `lineage_recipe.yaml` 中某条边（如 `dwd.vbak ← sap_erp.vbak`）与 `auto-lineage-collection` 跑出的边对应同一对 dataset
- **THEN** DataHub OpenSearch 索引中 MUST 仅保留 1 条（按 dataset URN + upstream URN 唯一）

#### Scenario: lineage_recipe.yaml 角色明确为兜底
- **WHEN** 阅读 `lineage_recipe.yaml` 顶部注释
- **THEN** MUST 明确说明此文件为"业务跨系统 JOIN 与未自动覆盖边的兜底通道"，不再作为唯一血缘来源
