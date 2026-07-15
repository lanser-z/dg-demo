# dwa-coal-quality Spec (delta)

## ADDED Requirements

### Requirement: 6.11 升级后 DWA 暂不切换 subject-分区上游（演示阶段）

`dwa_coal_quality` 宽表在 6.11 主题域重组后 MUST 继续读 `dwd/lims/dwd_samples/`（旧 system-分区）作为上游，不切换到 `dwd/coal_quality/dwd_samples/`（新 subject-分区）。6.12 跨主题 JOIN 时再统一切换。

#### Scenario: 演示阶段上游路径不变
- **WHEN** 6.11 变更归档后跑 `uv run python scripts/build_dwa_models.py --layer dwa`
- **THEN** `dwa_coal_quality` 宽表的 SQL 仍引用 `dwd/lims/dwd_samples/`，**不**引用 `dwd/coal_quality/dwd_samples/`

#### Scenario: 文档说明延迟切换
- **WHEN** 阅读 `docs/Module11.md` 第 4 节
- **THEN** MUST 含一段说明"DWA 宽表上游切换到 subject-分区是 6.12 范围；6.11 仅重组 DWD 与 lineage，DWA 仍读旧路径"
