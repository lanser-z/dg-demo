# dwa-sales-daily Spec (delta)

## ADDED Requirements

### Requirement: 6.11 升级后 DWA 暂不切换 subject-分区上游（演示阶段）

`dwa_sales_daily` 宽表在 6.11 主题域重组后 MUST 继续读 `dwd/sap_erp/dwd_vbak/`（旧 system-分区），不切换到 `dwd/sales/dwd_vbak/`。6.12 跨主题 JOIN 时再统一切换。

#### Scenario: 演示阶段上游路径不变
- **WHEN** 6.11 变更归档后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_sales_daily` 宽表的 SQL 仍引用 `dwd/sap_erp/dwd_vbak/`

#### Scenario: 文档说明延迟切换
- **WHEN** 阅读 `docs/Module11.md` 第 4 节
- **THEN** MUST 含说明"DWA 切换是 6.12 范围"
