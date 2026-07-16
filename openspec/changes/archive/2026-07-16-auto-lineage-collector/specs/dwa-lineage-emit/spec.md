# auto-lineage-collector — 详细规格

## ADDED Requirements

### Requirement: `build_dwa_models.py` 的 DWA ETL 入口接入 LineageEmitter

`scripts/build_dwa_models.py` MUST 在 `main()` 中为 `build_dwa_sales_daily`、`build_dwa_tag_alarm`、`build_dwa_coal_quality` 三个 ETL 函数各自调用 `LineageEmitter` 上下文管理器，emit COMPLETE 事件到 GMS OpenLineage 端点。

#### Scenario: 上下文管理器被调用
- **WHEN** 检查 `scripts/build_dwa_models.py` 全文件搜索 `with LineageEmitter(`
- **THEN** `build_dwa_sales_daily`、`build_dwa_tag_alarm`、`build_dwa_coal_quality` 三个 job MUST 各至少 1 次命中

#### Scenario: 每个入口改动不超过 5 行
- **WHEN** 统计 `main()` 中 LineageEmitter 相关代码行数（从 `with LineageEmitter(` 到 `ctx.emit_output(` 闭包）
- **THEN** 每个 job MUST ≤ 5 行

#### Scenario: 输出 URN 正确构造
- **WHEN** 每个 DWA job 的 output URN 构造
- **THEN** URN MUST 符合 `urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)` 格式，platform 从 `write_delta()` 调用的 `table_key` 推导（如 `dwa/sales/dwa_sales_daily` → platform=`dwa`，table=`dwa_sales_daily`）

### Requirement: 共享 lineage emit helper 函数

`scripts/build_dwa_models.py` MUST 定义 `_emit_lineage(job_name, sql, output_urn, emit)` 辅助函数，消除 3 个入口的 boilerplate 代码重复。

#### Scenario: Helper 函数存在
- **WHEN** 检查 `scripts/build_dwa_models.py`
- **THEN** 函数 `_emit_lineage` MUST 存在且可被 3 个 job 调用

#### Scenario: `--lineage` flag 控制 emit
- **WHEN** `main()` 增加 `--lineage` CLI flag（`action="store_true", default=True`）
- **THEN** `--lineage` 时 emit，`--no-lineage` 时跳过 emit 不阻断 ETL

---

## MODIFIED Requirements

### Requirement: ETL 入口通过 LineageEmitter 上下文管理器上报血缘

`Requirement: ETL 入口通过 LineageEmitter 上下文管理器上报血缘` 的 `#### Scenario: 上下文管理器存在并被 ETL 调用` 场景 **WHEN** 条件更新为：

- **WHEN** 检查 `scripts/ingest_to_deltalake.py` / `scripts/build_dwa_models.py` / `scripts/build_dimension_tables.py` / `scripts/build_dwa_sales_production.py` 四文件全文搜索 `with LineageEmitter(`
- **THEN** `build_dwa_models.py` MUST 至少 3 次命中（3 个 DWA job），其余文件各至少 1 次命中

> **变更原因**：原 spec 假设 3 个文件各接 1 次；实际 `build_dwa_models.py` 有 3 个 DWA ETL job 需要各自接入，`build_dwa_sales_production.py` 已单独接入。
