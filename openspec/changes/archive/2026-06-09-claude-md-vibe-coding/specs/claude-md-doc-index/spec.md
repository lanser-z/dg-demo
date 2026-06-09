## ADDED Requirements

### Requirement: 索引章节存在
`CLAUDE.md` MUST 包含一个 Index 章节，位于 Kernel 章节之后。

#### Scenario: Index 章节在 Kernel 之后
- **WHEN** 读取 `CLAUDE.md`
- **THEN** Kernel 章节之后的下一个同级章节 MUST 为 Index（`## Index`、`## 索引` 或语义等价）

### Requirement: 索引按任务场景组织
Index 章节 MUST 以表格形式组织，每行第一列为"我想要……"格式的用户意图，第二列为指向具体文件的路径。

#### Scenario: 表格列结构为意图→文件
- **WHEN** 阅读 Index 表格的每一行
- **THEN** 第一列 MUST 以动词或"我想要"开头描述意图；第二列 MUST 为可被 `Read` 工具加载的文件路径（相对仓库根）

### Requirement: 索引条目数上限
Index 章节的条目数量 MUST 不超过 15 条。

#### Scenario: 条目数 ≤ 15
- **WHEN** 统计 Index 表格的行数
- **THEN** 行数 SHALL ≤ 15（不含表头与兜底条目）

### Requirement: 索引条目指向的文件必须存在
Index 章节中列出的每一个文件路径 MUST 对应 git 工作树中实际存在的文件。

#### Scenario: 路径可达
- **WHEN** 对 Index 中每条路径执行 `Read` 工具或文件系统检查
- **THEN** 文件 MUST 存在；不存在的路径视为违例

### Requirement: 索引不得内联可索引内容
Index 章节 MUST NOT 包含命令块、代码片段、设计决策说明、或与 `docs/*.md` 内容等价或重叠的文本段落。

#### Scenario: 索引无内联代码
- **WHEN** 扫描 Index 章节
- **THEN** MUST NOT 出现超过一行的 shell/Python/SQL 代码块；MUST NOT 出现与 `docs/*.md` 任一节文字实质性重叠的段落

### Requirement: 索引包含兜底条目
Index 章节 MUST 包含一行的兜底条目，提示"未在表中找到？先问 Claude"或语义等价的引导。

#### Scenario: 兜底条目存在
- **WHEN** 扫描 Index 表格的最后几行
- **THEN** MUST 存在一行的"意图"列为"未列出"或"其他"或"先问"，"文件"列为"问 Claude"或"无"

### Requirement: 索引必须覆盖 docs 全部文档
Index 章节 MUST 至少包含指向 `docs/Background.md`、`docs/Design.md`、`docs/ELTvsETL.md`、`docs/Demo.md`、`docs/Deps.md` 中每一篇的至少一条条目。

#### Scenario: 6 篇 docs 全部可达
- **WHEN** 收集 Index 中所有引用的 `docs/*.md` 路径
- **THEN** 该集合 MUST 包含 `Background.md`、`Design.md`、`ELTvsETL.md`、`Demo.md`、`Deps.md` 全部 5 项（`Step1.md` 为可选实例文档不强制）

### Requirement: 索引必须指向 src 关键入口
Index 章节 MUST 至少包含一条指向 `src/dg_simulator/` 下的具体文件的条目（用于排查代码层面问题）。

#### Scenario: src 入口可达
- **WHEN** 检查 Index 中的源码路径
- **THEN** MUST 至少存在一个 `src/dg_simulator/*.py` 形式的路径
