# module2-quality-detection Specification (delta)

## ADDED Requirements

### Requirement: run_great_expectations.py 是 Checkpoint 的规则源

`scripts/run_great_expectations.py` 的 `RULES` 字典是 6.10 升级后 `QualityCheckpoint` 抽象的**唯一规则源**。`scripts/run_great_expectations.py` MUST 保持独立可执行（`--system sap_erp` CLI 仍可用），同时 MUST 暴露 `RULES` 模块级常量供 `src/dg_platform/quality_checkpoint.py` import。

#### Scenario: 模块级 RULES 可 import
- **WHEN** 在 Python REPL 执行 `from scripts.run_great_expectations import RULES`
- **THEN** MUST 成功导入 dict，包含 `{"sap_erp": {"vbak": [...], ...}, "pi_system": {...}, ...}` 结构

#### Scenario: 6.10 升级后 module2 notebook 仍可用
- **WHEN** 6.10 变更归档后执行 `uv run python scripts/run_great_expectations.py --system sap_erp`
- **THEN** MUST 输出与 6.9 之前一致的质量报告，**不依赖** 6.10 任何新模块

#### Scenario: 文档说明 6.10 升级路径
- **WHEN** 阅读 `scripts/run_great_expectations.py` 顶部 docstring
- **THEN** MUST 含 "6.10 升级：被 QualityCheckpoint 引用为规则源；CLI 仍可独立使用" 注释
