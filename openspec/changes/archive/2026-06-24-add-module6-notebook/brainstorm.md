# 模块六笔记本补全 — 变更发掘

## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 教学观察者 | Module6.md 是一套完整教学文档（含技术选型说明、SQL 模板、故障排查、快速命令），但这些内容从未进入任何 notebook，只存在于 docs 中 |
| 用户体验审查 | module5.ipynb 只承载了 4 个即席查询 code cell，缺少 Module6.md 规划的配套教学内容（为什么用 DuckDB、故障排查、快速命令等） |
| 归档审查 | `2026-06-23-module6-dwa-ad-hoc-query` 归档不完整，`openspec archive` 命令未执行，任务 4.3 未勾选 |
| 模块完整性审查 | Module6.md § 6 明确规划了独立 notebook 的教学目标，但 module5.ipynb 并未承担这个职责 |

## Ideas

- [ ] 想法 1：**新建 `notebook/module6.ipynb`**，将 Module6.md 的完整教学内容（含文档章节）迁入 notebook，作为模块六的独立教学载体。notebook 包含：痛点故事 → 技术选型（DuckDB vs ClickHouse）→ 4 个即席查询场景 → 故障排查 → 快速命令 → 诚实声明。
- [ ] 想法 2：**仅补充 module5.ipynb 的 markdown cell**，在 module5.ipynb 中补充技术选型说明和故障排查章节，不建独立 notebook（保持当前架构不变）。
- [ ] 想法 3：**将 Module6.md 拆分为 two-tier 教学**：保留 docs/Module6.md 作为技术参考手册，单独建 `notebook/module6.ipynb` 作为业务人员教学入口（推荐）。
- [ ] 想法 4：**修复归档流程**：先完成 `openspec archive` 命令，将 `2026-06-23-module6-dwa-ad-hoc-query` 正确归档，再补 module6.ipynb。

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1    | 可维护性 / 用户体验 | 独立 module6.ipynb 提供完整教学路径，Module6.md 的文档价值不只存在于 docs；业务人员打开 notebook 即可完成模块六全套学习 | ✅ 是 |
| 2    | 可维护性 | 改动最小，但 Module6.md 的教学设计意图未被尊重（其 § 2 明确写了「教学 notebook」），结构上 module5 和 module6 混在一起不清晰 | ❌ 否（破坏设计意图） |
| 3    | 可维护性 / 用户体验 | two-tier 结构：docs 做技术参考，notebook 做教学入口；职责清晰；后续模块七/八也是独立 notebook，模块六不应例外 | ✅ 是（推荐） |
| 4    | 流程完整性 | 归档不完整导致历史变更不可追溯；修复归档是流程健康度问题，但与补 module6.ipynb 是两个独立变更 | ⚠️ 可并行，不阻塞 Idea 1/3 |

---

## Plan

### 立即实现

- **Idea 编号**：Idea 3（新建 `notebook/module6.ipynb` + 保留 Module6.md 作为参考手册）
- **初步方案**：
  1. 新建 `notebook/module6.ipynb`，内容来自 Module6.md 教学章节 + module5.ipynb 步骤 2~5 的即席查询代码 cell
  2. Notebook 结构：痛点故事 → 为什么用 DuckDB → 依赖检查（模块五 DWA 表）→ 步骤 2~5 即席查询场景 → 故障排查 → 快速命令 → 诚实声明
  3. 保留 `docs/Module6.md`（不动），作为技术参考手册
- **关联 artifact**：`notebook/module6.ipynb`（新建）、`docs/Module6.md`（已有）
- **预计耗时**：0.5 天

### 等待观察

- **Idea 编号**：Idea 4（修复归档流程）
- **等待原因**：与 module6.ipynb 是两个独立问题，可后续单独走归档修复 change
- **触发条件**：归档问题积累到影响变更追溯时

## 变更产出

- **Change Proposal**：补建模块六教学 notebook
- **内容**：新建 `notebook/module6.ipynb`，将 Module6.md 教学章节迁入 notebook，保留 docs/Module6.md 作为技术参考
