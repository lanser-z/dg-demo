# dwa-coal-quality Spec (delta)

## ADDED Requirements

### Requirement: 6.12 切换上游到 subject-分区

`dwa_coal_quality` 宽表上游 MUST 从 `dwd/lims/dwd_samples/` 切换到 `dwd/coal_quality/dwd_samples/`（6.11 主题域重组后兑现）。

#### Scenario: 切换后 SQL 引用
- **WHEN** 检查 `scripts/build_dwa_models.py` 中 `build_dwa_coal_quality()` 的 read_parquet 调用
- **THEN** MUST 含 `dwd/coal_quality/dwd_samples/`，**MUST NOT** 含 `dwd/lims/dwd_samples/`

#### Scenario: 切换后宽表行数一致
- **WHEN** 6.12 切换后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_coal_quality` 宽表行数与 6.11 时一致（subject-分区与 system-分区数据相同）

#### Scenario: 文档说明切换完成
- **WHEN** 阅读 `docs/Module12.md` 第 3 节
- **THEN** MUST 含"dwa_coal_quality / dwa_sales_daily / dwa_tag_alarm 在 6.12 切到 subject-分区上游"说明
