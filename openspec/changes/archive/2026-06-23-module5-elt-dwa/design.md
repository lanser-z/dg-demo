## Context

模块四（DWD 清洗层）已交付，Delta Lake 中已有干净的结构化数据（`data/lakehouse/dwd/`）。业务人员无法直接使用这些明细数据进行临时分析，需要等待技术人员编写 SQL 聚合。

本模块是教学导向：为模块五构建 DWA 汇总宽表并配套教学 notebook，让业务分析师和数据工程师理解「宽表如何支撑即席查询」。

---

## Goals / Non-Goals

**Goals:**
- 构建 3 张 DWA 单系统汇总宽表（日销售 / 传感器告警 / 月度煤质）
- 所有宽表落 Delta Lake，验证 OLAP 场景的数据可用性
- 配套教学 notebook，演示 DuckDB 即席查询 4 个业务分析场景
- notebook 每个 code cell ≤15 行，调用 `build_dwa_models.py` 函数而非内联 SQL

**Non-Goals:**
- 跨系统产销宽表（`dwa_sales_production`）—— 依赖 Phase 2 主数据标准化
- ClickHouse / Doris OLAP 引擎升级 —— Phase 2 范畴
- Superset 可视化看板 —— Phase 2 范畴
- 定时 ETL 调度（小时级）—— Phase 2/3 范畴

---

## Decisions

### Decision 1：DWA 聚合引擎选型

| 选项 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| **DuckDB**（已选）| in-memory OLAP，零部署，Python 直连 Parquet/Delta Lake，教学演示快 | 断电丢失，无持久化，不适合生产 | ✅ Phase 1 验证可用性首选 |
| Apache Spark SQL | 与现有 Delta Lake 生态一致，分布式 | 启动慢，资源占用大，杀鸡用牛刀 | ❌ Phase 1 教学场景过度设计 |
| ClickHouse / Doris | 向量化引擎，生产级性能 | 引入额外运维成本 | ❌ Phase 2 再引入 |

### Decision 2：聚合粒度

| 表名 | 聚合粒度 | 分组字段 | 业务场景 |
|------|---------|---------|---------|
| `dwa_sales_daily` | 日 | `ERDAT`（销售日期） | 日销售趋势 |
| `dwa_tag_alarm` | 全量 | `mine + face + tag` | 传感器告警 Top20 排名 |
| `dwa_coal_quality` | 月 | `MINE_CODE + month + SAMPLE_TYPE` | 月度煤质报告 |

> 传感器告警表不按时间聚合（业务需求是排名而非趋势），与销售/煤质表不同。

### Decision 3：Notebook 结构

遵循模块 1~4 的 notebook 风格：

```
痛点故事（markdown）
    ↓
步骤1：构建 DWA 宽表（code：调用 build_dwa_models.py）
    ↓
步骤2：即席查询——日销售趋势（code：DuckDB SQL）
    ↓
步骤3：即席查询——传感器告警 Top（code：DuckDB SQL）
    ↓
步骤4：即席查询——月度煤质（code：DuckDB SQL）
    ↓
步骤5：4 个分析场景验证（code：综合查询）
    ↓
诚实声明（markdown）：跨系统宽表未实现，依赖 Phase 2
```

### Decision 4：Delta Lake 写入策略

- `write_deltalake(..., mode="overwrite")` — 每次运行覆盖，不做增量追加（教学数据量小，overwrite 足够）
- 写入前 `df.where(pd.notnull(df), None)` — 防止 PyArrow 序列化 NaN

---

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|------|------|---------|
| DWA 表行数为空 | Parquet LIMIT 导致数据为空，或字段名大小写/空格不匹配 | 运行前校验 `data/historical/` 下 parquet 文件 schema；`build_dwa_models.py` 加 `--debug` 输出实际列名 |
| DuckDB 注册 Delta Lake 失败 | `get_duckdb()` 的 `os.walk` 路径与实际不符 | 确认 `LAKEHOUSE_ROOT` 指向 `/home/szs/Playground/dg-demo/data/lakehouse` |
| 教学 notebook 行数超标 | code cell 内联 SQL 超过 15 行 | 规则：所有聚合 SQL 在 `build_dwa_models.py` 中定义，notebook 仅调用函数 + 展示结果 |
| notebook 与 Module5.md 脱节 | 两者内容不一致 | Module5.md 作为最终验收标准，notebook 开发完成后对照检查 |

---

## Migration Plan

**部署步骤**：
1. 确认 DWD 层数据已落库（`data/lakehouse/dwd/` 有文件）
2. 运行 `uv run python scripts/build_dwa_models.py --layer dwa`
3. 验证 `data/lakehouse/dwa/` 下 3 张表目录有 Parquet 文件
4. 打开 `notebook/module5.ipynb` 从头跑一遍
5. 对照 `docs/Module5.md` 验收步骤逐一确认

**回滚策略**：
```bash
# 删除 notebook 和文档
rm notebook/module5.ipynb
rm docs/Module5.md

# 删除 DWA Delta Lake 表（不影响 ODS/DWD）
rm -rf data/lakehouse/dwa/sap_erp/dwa_sales_daily/
rm -rf data/lakehouse/dwa/pi_system/dwa_tag_alarm/
rm -rf data/lakehouse/dwa/lims/dwa_coal_quality/
```

---

## Open Questions

| 问题 | 状态 | 备注 |
|------|------|------|
| 跨系统产销宽表字段 Schema 是什么？ | 待定 | 依赖模块七（主数据标准化）先交付矿井/客户编码维表 |
| DuckDB 是否需要升级为 ClickHouse/Doris？ | Phase 2 再决策 | 当前阶段验证可行性，DuckDB 足够 |
| DWA 增量更新策略（overwrite vs append）？ | 已决定 overwrite | 教学数据量小，overwrite 足够；Phase 2 考虑 append 或 MERGE |
