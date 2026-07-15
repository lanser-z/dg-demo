# dwa-sales-daily Spec (delta)

## ADDED Requirements

### Requirement: 6.12 切换上游到 subject-分区

`dwa_sales_daily` 宽表上游 MUST 从 `dwd/sap_erp/dwd_vbak/` 切换到 `dwd/sales/dwd_vbak/`（6.11 主题域重组后兑现）。

#### Scenario: 切换后 SQL 引用
- **WHEN** 检查 `scripts/build_dwa_models.py` 中 `build_dwa_sales_daily()` 的 read_parquet 调用
- **THEN** MUST 含 `dwd/sales/dwd_vbak/`，**MUST NOT** 含 `dwd/sap_erp/dwd_vbak/`

#### Scenario: 切换后宽表行数一致
- **WHEN** 6.12 切换后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_sales_daily` 宽表行数与 6.11 时一致

#### Scenario: 文档说明切换完成
- **WHEN** 阅读 `docs/Module12.md` 第 3 节
- **THEN** MUST 含"DWA 在 6.12 切到 subject-分区上游"说明
