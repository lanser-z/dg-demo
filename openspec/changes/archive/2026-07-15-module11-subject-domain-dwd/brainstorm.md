## Feedback

| 角色 | 核心反馈 |
|------|----------|
| 教学讲师（Background.md 6.11） | "从「按系统分 DWD 表」升级为「按业务主题重组 DWD 表」"；原 plan "Phase 1 出口条件：4 个分析场景可在 OLAP 看板中切换维度实时出数" |
| 学员（module4 实操） | "dwd/sap_erp/dwd_vbak 与 dwd/lims/dwd_samples 跨目录 JOIN 写起来很别扭"；"想按业务概念（销售/生产/煤质）找表" |
| 运维（生产环境） | "按系统分利于 ETL 维护，按主题分利于分析；组织越大越倾向主题分" |
| 现有 `data/lakehouse/dwd/` 布局 | 5 系统分区已就位（sap_erp/pi_system/lims/oa + _dimensions/），共 6 张 DWD 表 + 3 张 dim 表 |

## Ideas

- [ ] **Idea 1**：把 5 系统分区 DWD 表按主题重组：sales（vbak+vbap+kna1）/production（tags）/coal_quality（samples）/finance（doc_flow），保留 `_dimensions/` 不动
- [ ] **Idea 2**：保留旧 `dwd/{system}/` 目录，dual-write 新 `dwd/{subject}/` 目录（演示阶段 1.0× vs 1.0× 存储；教学对比清晰）
- [ ] **Idea 3**：用 Alibaba MaxCompute 命名规范 `dwd_{domain}_{process}` 简化命名（去掉 `system_` 前缀）
- [ ] **Idea 4**：DataHub 用 `delta-lake` source 配 `base_path: data/lakehouse/dwd` 自动递归发现新主题目录
- [ ] **Idea 5**：跨主题 JOIN 演示保留在 6.12（产销 4 表 JOIN）；6.11 只做"目录重组 + DataHub UI 主题视图"演示
- [ ] **Idea 6**：dim 表（dim_mine/customer/material）保留在 `_dimensions/`，**不**移到 `dwd/sales/` 下（维度全局共享）
- [ ] **Idea 7**：用 `acryl-datahub` SDK 注册 `dwd` 自定义 platform，subject 维度用 `customProperties` 标注
- [ ] **Idea 8**：`notebook/module11.ipynb` 演示：1) 列出主题目录结构；2) 同一查询在旧/新布局下对比；3) DataHub UI 看新主题

## Value

| Idea | 影响的非功能属性 | 价值描述 | 是否值得转为变更？ |
|------|----------------|----------|-------------------|
| 1 | 可发现性 / 教学性 | 按业务概念找表，跨系统业务 JOIN 不再别扭 | ✅ 是 |
| 2 | 可回滚 / 教学对比 | 演示阶段零风险；学员能对比新旧布局 | ✅ 是 |
| 3 | 命名一致性 / 行业标准 | 阿里 MaxCompute 是国内最广泛参考的标准 | ✅ 是 |
| 4 | 自动化 / 运维 | 删一行 YAML 即可扫描新主题目录 | ✅ 是 |
| 5 | 范围控制 | 6.11 聚焦"主题重组"；6.12 聚焦"跨主题 JOIN" | ✅ 是 |
| 6 | 共享性 / 设计原则 | 维度全共享，不属于任何业务域 | ✅ 是 |
| 7 | 治理成熟度 | DataHub UI 看到 `dwd > sales > dwd_vbak` 树形结构 | ✅ 是 |
| 8 | 教学性 | 完整演示新旧对比 + DataHub 视图 | ✅ 是 |

---

## Plan

### 立即实现
- **Idea 编号**：1 + 2 + 3 + 4 + 5 + 6 + 7 + 8（合为 6.11 主变更）
- **初步方案**：
  1. `scripts/restructure_dwd.py`：dual-write ETL（read 旧 / write 新）
  2. DataHub 配 `delta-lake` source + `dwd` platform 注册
  3. 重新 emit 新主题 DWD 表的 lineage
  4. `notebook/module11.ipynb` 3 cells 演示
  5. 文档 + Background 状态更新
- **负责人/角色**：教学工程师
- **预计耗时**：1 周（Background.md 6.11 估时 2 周，但 demo 范围较小）

### 等待观察
- **Idea 编号**：无
- **触发条件**：6.12 跨主题 JOIN 时复用本变更的主题目录
