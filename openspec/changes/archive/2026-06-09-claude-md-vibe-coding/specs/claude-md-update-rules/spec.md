## ADDED Requirements

### Requirement: 文件存在性变化触发索引同步
当 `docs/`、`src/`、`scripts/`、`config/` 中任一文件被新增、删除或重命名时，`CLAUDE.md` 的 Index 章节 MUST 被同步更新（新增条目 / 删除条目 / 修改路径）。

#### Scenario: 新增文件需加索引
- **WHEN** 在 `docs/` 下新增一个文件
- **THEN** 维护者 MUST 在 Index 中新增一条意图→该文件路径的条目

#### Scenario: 删除文件需去索引
- **WHEN** 在 `docs/`、`src/`、`scripts/`、`config/` 下删除一个文件，且该文件曾出现在 Index 中
- **THEN** 维护者 MUST 从 Index 移除对应条目

#### Scenario: 重命名文件需更新路径
- **WHEN** 一个被 Index 引用的文件被重命名
- **THEN** 维护者 MUST 更新 Index 中对应条目的文件路径

### Requirement: 文件内容变化不触发 CLAUDE.md 同步
当 `docs/*.md`、`src/**/*.py`、`scripts/*.py` 等被引用文件的**内容**发生变更时（不涉及文件增删改路径），`CLAUDE.md` MUST NOT 被修改。

#### Scenario: 内容修改不需改 CLAUDE.md
- **WHEN** 修改 `docs/Background.md` 的某段文字
- **THEN** 维护者 MUST NOT 修改 `CLAUDE.md`（除非该修改同时改变了文件路径或新增/删除了文件）

### Requirement: Kernel 硬约束同步规则
Kernel 章节的硬约束子节 MUST 仅在以下情况变更：(1) 项目级新禁令出现；(2) 已有禁令被解除；(3) 硬约束对象文件被删除。

#### Scenario: 新增项目级禁令需更新 Kernel
- **WHEN** 项目增加一条新的"绝对不能做"规则（如新增工具限制）
- **THEN** 维护者 MUST 在 Kernel 硬约束子节追加该规则

#### Scenario: 解除禁令需移除条目
- **WHEN** 某条硬约束不再适用（如不再使用某工具）
- **THEN** 维护者 MUST 从 Kernel 移除该条目

### Requirement: 行数预算维护
`CLAUDE.md` 的总行数 MUST 不超过 50 行。超出时维护者 MUST 优先合并相近的 Index 条目，再考虑删除 Kernel 硬约束。

#### Scenario: 总量 ≤ 50 行
- **WHEN** 统计 `CLAUDE.md` 的总行数
- **THEN** 行数 SHALL ≤ 50

#### Scenario: 超出预算时的处置顺序
- **WHEN** `CLAUDE.md` 行数超过 50
- **THEN** 维护者 MUST 先尝试合并 Index 中相近任务场景的条目；若仍超限，THEN 再考虑精简 Kernel；MUST NOT 通过删除 Kernel 中的硬约束来腾出空间（除非该约束已不再适用）
