# 模块六笔记本补全 — 变更提案

## Why

Module6.md 是一套完整教学文档，规划了独立教学 notebook 的结构（技术选型说明 → 4 个即席查询场景 → 故障排查 → 快速命令）。但 Module6.md § 2 规划的"教学 notebook"从未以独立 `.ipynb` 文件实现，其内容只存在于 `docs/Module6.md` 中；module5.ipynb 虽然包含了步骤 2~5 的代码 cell，但缺少 Module6.md 规划的配套教学内容（为什么用 DuckDB、故障排查、快速命令等）。模块六的教学目标因此无法被业务人员独立完成。

## What Changes

1. **新建 `notebook/module6.ipynb`**：将 Module6.md 的教学章节（含技术选型、痛点故事、4 个即席查询场景、故障排查、快速命令）迁入独立 notebook，作为模块六的专属教学载体。
2. **更新 `docs/Background.md` § 6.6**：标记模块六已完成，补上线教学 notebook 路径。
3. **保留现有 `notebook/module5.ipynb`**：不做修改，module5.ipynb 继续承载模块五的 DWA 构建步骤。

## Capabilities

### New Capabilities

- `module6-teaching-notebook`：独立教学 notebook，承载模块六全套教学内容（痛点故事 → 技术选型 → 即席查询验证 → 故障排查 → 快速命令），与模块五的 DWA 构建职责分离，职责边界更清晰。

### Modified Capabilities

- `module6-ad-hoc-notebook`：已有 spec 但从未生成独立 notebook 文件（历史问题：内容被混入了 module5.ipynb）。本次为该能力创建对应的物理 notebook 文件，spec 约束与 notebook 实现保持一致。
- `module6-documentation`：已有 spec，内容为 docs/Module6.md。保留不变，作为技术参考手册。

## Impact

**新增文件**：
- `notebook/module6.ipynb`

**修改文件**：
- `docs/Background.md` § 6.6（状态更新 + notebook 路径）

**不受影响**：
- `notebook/module5.ipynb`（不变）
- `docs/Module6.md`（保留，作为技术参考手册）
- `scripts/build_dwa_models.py`（不变）

**回滚计划**：
- 删除 `notebook/module6.ipynb`，恢复 `docs/Background.md` § 6.6 状态
- 不影响 module5.ipynb 和 module6-ad-hoc-notebook spec
