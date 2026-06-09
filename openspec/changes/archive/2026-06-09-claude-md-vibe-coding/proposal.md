## Why

当前 `CLAUDE.md`（约 120 行）把 `docs/` 里的项目结构、技术栈、命令、设计决策、注意事项大量复制内联，导致两个问题：
1. **context window 浪费**：每次会话都加载大量与 docs 重复的内容
2. **单点修改漂移**：`docs/` 是项目前期工作与经验总结的唯一权威源（约 110KB / 6 篇），但 CLAUDE.md 拷贝副本后，docs 改动不会同步过来

本变更把 CLAUDE.md 改为"**最小内核 + 文件索引**"两段式结构：内核只放 Claude 不知道就一定会犯错的硬约束，索引只放文件指针——所有"可指向文件"的知识一律按需 `Read`。

## What Changes

- **改写** `CLAUDE.md`：从 ~120 行的"复制 docs"重构为 ~40 行的"内核 + 索引"
- **新增** 内核章节：项目身份、读文档约定、硬约束（内存阈值、`uv` 唯一、`data/` 不入 git）
- **新增** 文件索引章节：按"任务场景"组织的文件指针表
- **删除** 所有与 `docs/` 重复的内联内容（项目结构、技术栈速查、常用命令、关键设计决策、注意事项、问题排查思路）
- **修改** "必读顺序"为"按任务路由"——不再对所有场景强加 5 步阅读

**非破坏性变更**——CLAUDE.md 仍存在，仅内容被重写；不影响代码、API、依赖。

## Capabilities

### New Capabilities

- `claude-md-kernel`: 定义 CLAUDE.md 的最小内核——哪些内容属于"不带文件就读不到"的硬约束（项目身份、读文档约定、不可违反的约束）
- `claude-md-doc-index`: 定义 CLAUDE.md 的文件索引——按任务场景路由到 `docs/` 与 `src/` 中具体文件，禁止内联可被索引替代的内容
- `claude-md-update-rules`: 定义 CLAUDE.md 的维护规则——当 docs 或代码变更时，何时需要同步 CLAUDE.md、何时不需要

### Modified Capabilities

无（首次引入，无既有规范可改）。

## Impact

- **受影响的文件**：
  - `CLAUDE.md`（重写主体）
  - `docs/*.md`（**不**变更，仅被索引指向）
- **受影响的运行时行为**：Claude Code 在本项目的会话启动方式——从"先读 CLAUDE.md 全文 → 视情况读 docs"改为"读 CLAUDE.md 内核 → 按任务路由读 docs"
- **依赖**：
  - `docs/` 6 篇文档已就绪（Background、Design、ELTvsETL、Demo、Deps、Step1）
  - `src/dg_simulator/` 源码已存在，可被索引
- **回滚计划**：将 `CLAUDE.md` 回退到 git HEAD 版本即可，单文件变更无外部副作用

**不做的事**（明确排除）：
- 不重写 `docs/*.md` 的内容
- 不修改 `pyproject.toml` 或任何源码
- 不引入新的工具/脚本
- 不在 CLAUDE.md 中新增任何与 `docs/` 内容等价或重叠的章节
