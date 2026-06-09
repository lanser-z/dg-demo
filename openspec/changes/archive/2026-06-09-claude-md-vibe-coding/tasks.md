## 1. 起草新 CLAUDE.md

- [x] 1.1 起草 Kernel 章节（项目身份、读文档约定、硬约束三子节，≤ 20 行）
- [x] 1.2 起草 Index 表格（覆盖 5 篇 docs + 至少 1 条 src 入口 + 兜底条目，≤ 15 条）
- [x] 1.3 在内核顶部加文件总标题与 Kernel/Index 章节标题

## 2. 静态自检

- [x] 2.1 行数预算检查：Kernel ≤ 20、Index 表格 ≤ 15、Total ≤ 50
- [x] 2.2 路径可达检查：Index 中每个文件路径在 `git ls-files` 输出中存在
- [x] 2.3 内容合规检查：Kernel 无 shell/Python/SQL 代码块；Index 无超过 1 行的代码块
- [x] 2.4 硬约束措辞检查：硬约束子节每条以否定词或禁令陈述开头，无"建议/应当"等 positive guidance

## 3. 落地

- [x] 3.1 用 `Write` 工具原子覆盖 `/home/szs/Playground/dg-demo/CLAUDE.md`
- [x] 3.2 `git diff --stat` 确认本次改动只涉及 `CLAUDE.md` 单文件
- [x] 3.3 `git status` 确认工作区无其他文件被误改

## 4. 回滚预案验证

- [x] 4.1 验证 `git show HEAD:CLAUDE.md` 可访问原版（无需实际回滚）
- [x] 4.2 在 `openspec/changes/claude-md-vibe-coding/rollback.md` 写一行回滚提示：`git restore CLAUDE.md`
