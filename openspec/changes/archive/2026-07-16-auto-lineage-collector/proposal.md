# auto-lineage-collector — 变更提案

## Why

当前 `build_dwa_models.py` 的 3 个 DWA ETL 函数（`build_dwa_sales_daily` / `build_dwa_tag_alarm` / `build_dwa_coal_quality`）没有接入 `LineageEmitter`，导致 `verify_auto_lineage.py` 中 6 个 ETL job 里实际只有 `build_dwa_sales_production` 能 emit OpenLineage 事件。Module3 文档声称"auto 通道已完成"，但与实际情况不符。完成剩余 3 个 DWA ETL 入口的接入，使 auto 通道真正覆盖全部 ETL 入口。

## What Changes

1. **`scripts/build_dwa_models.py`**：在 `main()` 中为 `build_dwa_sales_daily`、`build_dwa_tag_alarm`、`build_dwa_coal_quality` 三个 ETL 入口接入 `LineageEmitter` 上下文管理器
2. **`scripts/build_dwa_models.py`**：抽取共享的 lineage emit 辅助函数，消除 3 个入口的代码重复
3. **`scripts/verify_auto_lineage.py`**：`EXPECTED_INPUT_FRAGMENTS` 确认 6 个 job 全部被覆盖，验证脚本可零误报运行
4. **`docs/Module3.md`**：更新 auto 通道实现状态，说明已接入的 ETL 入口清单

## Capabilities

### New Capabilities

- `dwa-lineage-emit`：为 `build_dwa_models.py` 的 3 个 DWA ETL 入口（`build_dwa_sales_daily` / `build_dwa_tag_alarm` / `build_dwa_coal_quality`）接入 `LineageEmitter` 自动 lineage emit 上下文管理器，emit COMPLETE 事件到 GMS OpenLineage 端点

### Modified Capabilities

- `auto-lineage-collection`（现有 spec）：`Requirement: ETL 入口通过 LineageEmitter 上下文管理器上报血缘` 中的 Scenario `when check ... scripts/build_dwa_models.py ... with LineageEmitter(` 当前 FAILED，修复后应 PASS

## Impact

| 受影响项 | 影响描述 |
|---|---|
| `scripts/build_dwa_models.py` | 新增 `with LineageEmitter(...)` 包装 ETL 入口，import 语句 |
| `scripts/verify_auto_lineage.py` | `EXPECTED_INPUT_FRAGMENTS` 更新，无需代码逻辑修改 |
| `docs/Module3.md` | 更新 §6.9 状态，ETL 入口清单与实际一致 |
| 无 BREAKING 变更 | 所有改为加法，无破坏性修改 |

## 回滚计划

若验证失败，逐个注释掉 `with LineageEmitter(...)` 上下文管理器即可回滚，数据湖写入逻辑不受影响。
