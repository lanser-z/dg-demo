## ADDED Requirements

### Requirement: Kernel 章节存在
`CLAUDE.md` MUST 包含一个 Kernel 章节，位于文件顶部，紧接标题之后。

#### Scenario: Kernel 章节位于顶部
- **WHEN** 读取 `CLAUDE.md`
- **THEN** 文件首段（标题之后）必须出现以 `## Kernel`、`## 内核` 或语义等价的二级标题开头的章节

### Requirement: Kernel 包含三个子节
Kernel 章节 MUST 至少包含以下三个子节：(1) 项目身份、(2) 读文档约定、(3) 硬约束。

#### Scenario: 三个子节齐全
- **WHEN** Claude Code 加载 `CLAUDE.md`
- **THEN** Kernel 章节必须提供项目身份说明、"按需 Read 文档" 的明确指令、以及"绝对不能做"的行为禁止项清单

### Requirement: Kernel 总行数限制
Kernel 章节（从章节标题到下一个同级章节标题之间的所有内容） MUST 不超过 20 行。

#### Scenario: Kernel 行数 ≤ 20
- **WHEN** 统计 Kernel 章节的行数
- **THEN** 行数 SHALL ≤ 20

### Requirement: 硬约束只列行为禁止项
Kernel 章节的"硬约束"子节 MUST 仅包含 negative constraints（"不得做 X"），不得包含 positive guidance（"建议做 Y"）。

#### Scenario: 硬约束无建议性措辞
- **WHEN** 阅读硬约束子节的每一条
- **THEN** 每条 MUST 以"不得"、"禁止"、"不"等否定词开头，或为不带条件修饰的禁令陈述

### Requirement: 读文档约定是显式指令
Kernel 章节的"读文档约定"子节 MUST 显式声明：Claude 不得假设 `docs/*.md` 的内容已知，必须按需 `Read`。

#### Scenario: 约定含"按需 Read"指令
- **WHEN** 阅读读文档约定子节
- **THEN** 子节 MUST 出现"按需 Read"、"Read 文档"、"不得假设"或语义等价的指令性短语

### Requirement: Kernel 不得内联可索引内容
Kernel 章节 MUST NOT 包含任何可被文件指针替代的内容（如具体命令、目录树、技术栈列表、问题排查步骤）。

#### Scenario: Kernel 中无命令块
- **WHEN** 扫描 Kernel 章节
- **THEN** MUST NOT 出现 `uv run`、`pip install`、`git commit` 等具体命令块（出现即违反）
