# data-lineage-ingestion Spec (delta)

## ADDED Requirements

### Requirement: 4 表 JOIN 跨主题宽表 lineage 边

`scripts/build_dwa_sales_production.py` 跑完时 MUST 通过 6.9 `LineageEmitter` emit lineage 事件，含 4 个 inputs（dwd/sales/dwd_vbak、dwd/sales/dwd_kna1、dwd/production/dwd_tags、dwd/coal_quality/dwd_samples）+ 1 个 output（dwa_sales_production）。

#### Scenario: LineageEmitter 包装
- **WHEN** 检查 `scripts/build_dwa_sales_production.py` 源码
- **THEN** MUST 含 `with LineageEmitter("dwa_sales_production", sql=SQL_4TABLE_JOIN) as e: e.emit_output("urn:li:dataset:(urn:li:dataPlatform:dwa,dwa_sales_production,PROD)", df)`

#### Scenario: lineage 边写入 GMS
- **WHEN** 跑脚本 + `python scripts/verify_auto_lineage.py`
- **THEN** MUST 输出新 job `dwa_sales_production` 的 inputs 数 = 4，outputs 数 = 1
