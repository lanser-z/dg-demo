# 模块六笔记本补全 — 技术设计

## Context

### 背景

Module6.md § 2 明确规划了「教学 notebook」作为模块六的专属教学载体，但该 notebook 从未以物理文件实现。module5.ipynb 虽包含步骤 2~5 的即席查询代码 cell，却缺少 Module6.md 规划的配套教学内容。

本次变更目标：新建 `notebook/module6.ipynb`，将 Module6.md 的教学章节迁入独立 notebook，与 module5.ipynb 的 DWA 构建职责分离。

### 约束

- 教学数据规模约 1GB Parquet，内存可完全加载
- 业务人员零运维成本，不引入独立 OLAP 服务
- 每个 notebook code cell ≤15 行，不内联大段 SQL
- Notebook 依赖模块五产出的 DWA 宽表（前置条件）

## Goals / Non-Goals

**Goals:**
- 业务人员打开 `notebook/module6.ipynb` 能独立完成模块六的全套学习
- Notebook 包含 Module6.md 规划的所有教学章节（技术选型 → 痛点故事 → 即席查询 → 故障排查 → 快速命令）
- 与 module5.ipynb 职责分离：module5 管 DWA 构建，module6 管即席查询教学

**Non-Goals:**
- 不修改 module5.ipynb
- 不修改 docs/Module6.md（保留作为技术参考手册）
- 不修改 `scripts/build_dwa_models.py` 的聚合逻辑
- 不引入 ClickHouse / Doris 等独立 OLAP 引擎

## Decisions

### Decision 1：独立 notebook 而非修改 module5.ipynb

**选择**：新建 `notebook/module6.ipynb`

**理由**：
- Module6.md § 2「教学 notebook」的设计意图是独立 notebook，不是叠加在 module5 里
- 模块七（module7.ipynb）和模块八（module8.ipynb）均为独立 notebook，模块六不应例外
- 独立 notebook 允许业务人员直接打开模块六开始学习，无需先跑完模块五的 DWA 构建步骤（notebook 内有依赖检查 cell）

**备选**：
- 修改 module5.ipynb 补充 Module6.md 内容：破坏设计意图，module5 和 module6 职责混在一起

### Decision 2：DuckDB 即席查询引擎（引用归档设计）

**选择**：DuckDB（in-process，零运维）

**理由**（引用 `2026-06-23-module6-dwa-ad-hoc-query` 归档 design.md）：
- 单节点 <100GB 规模下，DuckDB 性能优于 ClickHouse（ClickBench 2025年10月排名第一）
- 嵌入式，无需启动服务，Jupyter notebook 内直接 `import duckdb` 使用
- 直接扫描 Parquet / Delta Lake 文件，无需数据导入
- 教学数据约 1GB，完全在 DuckDB 舒适区

**备选**：
- ClickHouse：分布式，适合 TB 级数据，但需要独立服务，教学环境不必要的开销

### Decision 3：复用 module5.ipynb 的即席查询代码 cell

**选择**：module6.ipynb 步骤 2~5 的 code cell 直接复用 module5.ipynb 的代码

**理由**：
- 代码完全相同（都是对同一张 DWA 表的 DuckDB 查询）
- module6.ipynb 的职责是教学承载，不重新发明即席查询逻辑
- 修改 module5.ipynb 会引入版本同步风险

### Decision 4：保留 docs/Module6.md 作为技术参考手册

**选择**：不动 docs/Module6.md

**理由**：
- docs/Module6.md 包含更详细的技术说明（ClickBench 数据、故障排查表格、SQL 模板完整版）
- 业务人员用 notebook 教学，技术人员用 docs 做参考，two-tier 结构职责清晰

## Notebook 结构

```
notebook/module6.ipynb
│
├── 痛点故事（markdown）：「等 IT 排期 3 天」的尬
├── 技术选型（markdown）：为什么用 DuckDB vs ClickHouse（引用 Module6.md § 1）
├── 依赖检查（code）：检查模块五 DWA 表是否存在
├── 步骤 2（code）：即席查询——日销售趋势（dwa_sales_daily）
├── 步骤 3（code）：即席查询——传感器告警 Top（dwa_tag_alarm）
├── 步骤 4（code）：即席查询——月度煤质（dwa_coal_quality）
├── 步骤 5（code）：4 个分析场景验证 + 诚实声明
├── 故障排查（markdown）：5 个常见问题 + 报错自查清单（引用 Module6.md § 5）
└── 快速命令（markdown）：4 个场景 SQL 模板 + CLI 命令速查（引用 Module6.md § 6）
```

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|------|------|---------|
| R1 | module5.ipynb 未跑，DWA 表不存在，module6.ipynb 报错 | 依赖检查 cell 提前报错，给出 `build_dwa_models.py --layer dwa` 命令 |
| R2 | DuckDB 内存不足（机器 <8GB） | 教学中限制 Parquet 读取量（已有 LIMIT）；文档中说明内存要求 |
| R3 | 产销对比场景给业务人员造成「已经能做」的误解 | 步骤 5 cell 和诚实声明 markdown 明确标注当前为单系统宽表 |
| R4 | module6.ipynb 和 module5.ipynb 代码重复，维护成本 ×2 | 两者职责不同：module5 是 DWA 构建演示，module6 是即席查询教学；代码 cell 相同但教学目标不同，暂可接受 |

## Open Questions

- Q1：module6.ipynb 的依赖检查 cell 如果发现 DWA 表不存在，是抛出异常还是给出修复命令后继续？
  - 答案：给出修复命令后 raise SystemExit（不让业务人员跑空 notebook）
- Q2：是否需要在 module6.ipynb 中补充 DuckDB CLI 速查？
  - 答案：作为快速命令 markdown cell 提供（引用 Module6.md § 6，不在 code cell 中执行）
