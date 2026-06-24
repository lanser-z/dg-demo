# Delta spec: module6-ad-hoc-notebook

> 本 delta spec 修正已有 `module6-ad-hoc-notebook` 规范中的 notebook 路径引用。

---

## MODIFIED Requirements

### Requirement: Notebook 结构

module6-ad-hoc-notebook SHALL contain the following sections in order:

1. 痛点故事（markdown）：「等 IT 排期 3 天才能拿到数据」的尬
2. 步骤 2（code）：即席查询——日销售趋势（`dwa_sales_daily`）
3. 步骤 3（code）：即席查询——传感器告警 Top（`dwa_tag_alarm`）
4. 步骤 4（code）：即席查询——月度煤质（`dwa_coal_quality`）
5. 步骤 5（code）：4 个分析场景验证 + 诚实声明
6. 诚实声明（markdown）：当前为单系统宽表，跨系统产销对比需 Phase 2

#### Scenario: Notebook 结构正确
- **WHEN** user opens `notebook/module6.ipynb`
- **THEN** the notebook contains sections 1 through 6 listed above in order
