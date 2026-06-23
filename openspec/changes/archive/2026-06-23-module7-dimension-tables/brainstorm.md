## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 数据分析师 / BI 开发者 | 在构建跨系统产销宽表时，需要大量 WHERE 子句做字段名映射（如 `s.mine = 'M001' AND p.mine_code = 'M001' AND l.mine_code = 'M001'`），SQL 可读性差，JOIN 条件不直观，维护成本高 |
| 模块十二实施者 | PI + LIMS + SAP + KNA1 四表 JOIN 时，同一矿井有 3 种字段名（`mine`/`mine_code`/`WERKS`），每次写 JOIN 都要查映射关系，容易出错 |
| 数据架构师 | 当前 Phase 1 各系统字面统一（都用 M001），但字段名不同导致无法直接 JOIN，希望建立统一维表彻底解决 |

## Ideas

- [ ] 想法 1：**建立 dim_mine 矿井维表**，将 SAP 的 `WERKS`、PI 的 `TAG` 段、LIMS 的 `MINE_CODE` 统一映射到标准 `mine_code`，解决字段名歧义
- [ ] 想法 2：**建立 dim_customer 客户维表**，将 KNA1 的客户编码、名称、区域、信用等级统一管理，为跨系统客户分析提供单一数据源
- [ ] 想法 3：**建立 dim_material 物料维表**，将 MARA 物料编码与 LIMS/OA 系统关联，解决物料信息孤岛问题
- [ ] 想法 4：**引入轻量级 MDM（主数据管理）系统**，如 DataHub Metadata Platform，统一管理维表版本、血缘和治理策略

## 想法 4 验证（DataHub DeepWiki 调研）

> **结论：DataHub 可用于维表元数据治理，但不适合作为维表数据的物理存储**
>
> DataHub 的 **Logical Models** 功能可以：
> - 定义 canonical dimension table schema（标准维表结构），描述列、数据类型、描述
> - 将逻辑模型与多个物理实例（gold/silver/bronze 各层的同名维表）链接，实现**一次性元数据变更自动下发**
> - 支持 Glossary Terms、Tags、Ownership、Domains 等治理能力
>
> **局限**：DataHub 是元数据**治理平台**，不是**数据存储**。维表的实际数据（`dim_mine`/`dim_customer`/`dim_material` 的具体行）仍需存储在 Delta Lake / Database 中。DataHub 只负责存储这些维表的**元数据**（schema、描述、标签、血缘）。
>
> 当前 Module7 方案（Delta Lake 物理存储 + Module1 DataHub 元数据接入）已覆盖 DataHub 可提供的能力。

- [ ] 想法 5：**在 DWD 层建立字段映射视图（view）**，替代物理维表，不修改现有清洗逻辑，渐进式演进

## 想法 5 验证（Delta Lake / DuckDB 约束能力调研）

> **结论：view 方式可缓解维护负担，但无法根本解决字段名不一致问题**
>
> 1. **DuckDB 确实支持 FOREIGN KEY 约束**（referential integrity enforcement）
> 2. **Delta Lake 的 CONSTRAINT 仅为 informational，不实际强制执行**（来自 Reddit r/dataengineering 讨论："primary key and foreign key constraints encode relationships between fields in tables and are not enforced"）
> 3. view 的局限性：
>    - view 只是预写的 SQL 查询，仍然需要维护字段映射逻辑（只是从多个 WHERE 子句变成 view 内部的 JOIN）
>    - view 不解决"join 条件不直观"的核心痛点——用户查询 view 时仍然需要知道底层字段名
>    - view 不能被其他 BI 工具直接发现和浏览（没有独立的元数据）
>
> **结论**：想法 5 的评估保持 ❌，view 方式是"换汤不换药"，不解决根本问题。

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1    | 可维护性、可观测性 | 维表 JOIN 替代大量 WHERE 映射，SQL 可读性提升，错误率降低 | ✅ 是 |
| 2    | 可维护性、数据质量 | 客户信息统一管理，避免重复客户数据，支持客户层级的信用分析 | ✅ 是 |
| 3    | 可维护性、数据完整性 | 物料信息跨系统关联，支持物料追溯和质量分析 | ✅ 是 |
| 4    | 治理能力、可观测性 | DataHub Logical Models 可管理维表元数据（schema、标签、血缘），但数据本身仍需物理维表存储。适合作为 Module1 DataHub 接入的扩展，而非独立变更 | ⚠️ 暂不独立实施（依赖维表物理实现） |
| 5    | 可维护性、侵入性 | view 方式 DuckDB 支持 FK 约束但不强制，Delta Lake 的 CONSTRAINT 为 informational；view 内部仍需维护映射逻辑，不能根本解决 JOIN 不直观问题 | ❌ 否（不解决根本问题） |

---

## Plan

### 立即实现

- **Idea 编号**：想法 1、2、3
- **初步方案**：
  1. 在 `data/lakehouse/dwd/_dimensions/` 下创建 3 个 Delta Lake 目录
  2. 编写 `scripts/build_dimension_tables.py`，从 `data/historical/` 各系统 parquet 文件聚合、去重、写入维表
  3. 编写 `notebook/module7.ipynb` 教学 notebook，对比有维表 vs 无维表的 JOIN 差异
- **涉及文件**：
  - `scripts/build_dimension_tables.py`（新建）
  - `notebook/module7.ipynb`（新建）
  - `data/lakehouse/dwd/_dimensions/dim_mine/`（Delta Lake）
  - `data/lakehouse/dwd/_dimensions/dim_customer/`（Delta Lake）
  - `data/lakehouse/dwd/_dimensions/dim_material/`（Delta Lake）
- **预计耗时**：约 2~3 小时（含数据验证）

### 等待观察

- **Idea 编号**：想法 4（DataHub Logical Models 维表元数据管理）
- **等待原因**：DataHub Logical Models 依赖物理维表先建立，当前 Module1 DataHub 接入仅覆盖表级元数据，尚未扩展到维表元数据治理层面
- **触发条件**：维表物理实现完成后（Module7 Phase 2 交付），作为 Module1 DataHub 接入的扩展（建议另起 change）

## 变更产出（可选）

本 brainstorming 产生的"立即实现"Idea 建议创建 **Change Proposal**，对应 Module7.md 的维表构建需求。后续 artifact `proposal.md` 将详细描述变更范围、影响和实现路径。
