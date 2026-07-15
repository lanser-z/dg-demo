## Context

当前 3 张 DWA 宽表都基于单系统 DWD（`dwd/sap_erp/`、`dwd/pi_system/`、`dwd/lims/`），无法做跨主题分析。6.11 主题域重组后 4 个表分散在 `dwd/{sales,production,coal_quality,finance}/` 主题目录，6.12 把 6.11 投资兑现为跨主题宽表。

**当前状态（module6）**：
- 3 张 DWA：`dwa_sales_daily` / `dwa_tag_alarm` / `dwa_coal_quality`，DuckDB 聚合 Delta Lake
- 6.11 dual-write 后 DWD 含 4 主题目录 + 4 旧 system-分区
- 6.11 delta 承诺 6.12 切 DWA 上游到 subject-分区

**约束**：
- 10 分钟 demo 时长
- 不引 ClickHouse / Doris（5+ 分钟 Docker 启动）
- 不引 Superset（部署链路过长）
- 4 表 JOIN 必须演示 `mine_code` 跨主题关联

**利益相关者**：教学讲师、学员、运维。

## Goals / Non-Goals

**Goals:**
1. 1 张 4 表 JOIN 跨系统宽表 `dwa_sales_production`
2. DuckDB 模拟物化视图（CREATE TABLE AS SELECT 写 Delta Lake）
3. 4 个分析场景 SQL 模板（产销对比 / 煤质定价 / 安全趋势 / 订单履约）
4. 旧 3 张 DWA 切上游到 subject-分区
5. notebook 演示完整闭环

**Non-Goals:**
- ClickHouse / Doris 部署（Phase 3）
- Superset 看板（Phase 3 演进路径）
- 实时刷新（demo 阶段一次性 ETL）
- 5+ 表 JOIN（4 表已足够演示）

## Decisions

### Decision 1: DuckDB 替代 ClickHouse/Doris

**选择**：用 `duckdb` Python 库（已在 `pyproject.toml`）。

**备选**：
- A. ClickHouse Docker（5+ 分钟启动）
- B. Doris FE+BE（8+ 分钟启动 + 多容器）
- C. **DuckDB**（0 setup，< 1s 4 表 JOIN）

**理由**：
- 10 分钟 demo 时长约束
- DuckDB 4 表 × ~1M 行 < 1s
- 跨 4 文件 read_parquet + 物化结果写 Delta Lake，流程清晰
- 生产换 ClickHouse 仅需替换 `scripts/build_dwa_sales_production.py` 中 DuckDB 部分

### Decision 2: 读 subject-分区（6.11 已建好）

**选择**：`dwd/sales/dwd_vbak` + `dwd/sales/dwd_kna1` + `dwd/production/dwd_tags` + `dwd/coal_quality/dwd_samples`。

**备选**：
- A. 读 subject-分区（**选择**）：跨主题 JOIN 自然
- B. 读旧 system-分区：与 6.11 主题域投资脱钩

**理由**：6.11 主题重组就是为了让 6.12 跨主题 JOIN 简单；不读新主题等于浪费 6.11 投资。

### Decision 3: CREATE TABLE AS SELECT 模拟物化视图

**选择**：`CREATE TABLE dwa_sales_production AS SELECT ...` 写 Delta Lake。

**备选**：
- A. CREATE TABLE AS SELECT（**选择**）：1 行，物理持久化，多次查询秒级
- B. CREATE VIEW：每次查询都重算，4 表 × 1M 行 demo 跑 5s
- C. ClickHouse MATERIALIZED VIEW：Phase 3 升级路径

**理由**：
- Demo 阶段避免重复计算（多次跑同 SQL 应秒回）
- Delta Lake 格式与现有 DWD 一致
- 用户改 SQL 调试时不需要每次重算

### Decision 4: 4 表 JOIN 用 `mine_code` 作 bridge key

**选择**：`vbak.MINE_CODE` ↔ `tags.mine` ↔ `samples.MINE_CODE`；`vbak.KUNNR` ↔ `kna1.KUNNR`。

**备选**：
- A. mine_code 全链路（**选择**）：跨 3 主题（sales/production/coal_quality）
- B. VBELN + ERDAT：缺少跨主题关联
- C. 引入 dim_mine：3 主题已共享 mine_code，不必 JOIN dim

**理由**：`mine_code` 是 5 系统共享的主数据标准（Background.md §3.2.1），跨主题 JOIN 应当用此键。

### Decision 5: 旧 3 张 DWA 切上游到 subject-分区

**选择**：`build_dwa_models.py` 中 3 个 DWA 函数的 SQL 引用从 `dwd/{system}/*` 切换到 `dwd/{sales,production,coal_quality}/*`。

**备选**：
- A. 切（**选择**）：兑现 6.11 delta 承诺
- B. 不切：保留 6.11 dual-write 优势

**理由**：6.11 delta 明确"6.12 跨主题 JOIN 时再统一切换"；不切等于 6.11 dual-write 长期共存。

### Architecture Diagram

```plantuml
@startuml
!theme plain

rectangle "6.11 主题域 DWD" {
  (dwd/sales/) {
    [dwd_vbak]   <- SAP 销售订单
    [dwd_kna1]   <- SAP 客户主数据
  }
  (dwd/production/) {
    [dwd_tags]   <- PI 时序
  }
  (dwd/coal_quality/) {
    [dwd_samples] <- LIMS 煤质
  }
  (dwd/_dimensions/) {
    [dim_mine] [dim_customer] [dim_material]
  }
}

rectangle "scripts/build_dwa_sales_production.py" <<ETL>> as B {
  [DuckDB 4-table JOIN\nmine_code bridge]
}

rectangle "DWA" {
  (dwa/) {
    [dwa_sales_production]  <- 4 表 JOIN
    [dwa_sales_daily]       <- 旧（已切 subject-分区）
    [dwa_tag_alarm]         <- 旧（已切 subject-分区）
    [dwa_coal_quality]      <- 旧（已切 subject-分区）
  }
}

B --> (dwd/sales/)
B --> (dwd/production/)
B --> (dwd/coal_quality/)
B --> (dwa/dwa_sales_production)

@enduml
```

### Data Flow: 4 表 JOIN 跨主题

```plantuml
@startuml
!theme plain

participant "Script" as S
participant "DuckDB" as D
participant "dwd/sales" as SA
participant "dwd/production" as P
participant "dwd/coal_quality" as CQ
participant "dwa/dwa_sales_production" as OUT

S -> D: 启动 DuckDB in-memory
D -> SA: CREATE VIEW vbak AS SELECT * FROM read_parquet('dwd/sales/dwd_vbak/')
D -> SA: CREATE VIEW kna1 AS SELECT * FROM read_parquet('dwd/sales/dwd_kna1/')
D -> P: CREATE VIEW tags AS SELECT * FROM read_parquet('dwd/production/dwd_tags/')
D -> CQ: CREATE VIEW samples AS SELECT * FROM read_parquet('dwd/coal_quality/dwd_samples/')
S -> D: CREATE TABLE dwa_sales_production AS
        SELECT v.VBELN, v.ERDAT, v.KUNNR, k.NAME1,
               t.mine, t.face, s.AD, s.QGR_AD, AVG(t.value) AS avg_production
        FROM vbak v
        LEFT JOIN kna1 k ON v.KUNNR = k.KUNNR
        LEFT JOIN tags t ON v.MINE_CODE = t.mine
        LEFT JOIN samples s ON t.mine = s.MINE_CODE
        GROUP BY ...
D -> OUT: write_deltalake('dwa/dwa_sales_production', df)

@enduml
```

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| DuckDB 不支持并发写入 | 演示阶段 1 用户 1 写入 OK；生产换 ClickHouse | 写在 design；演进路径明确 |
| 4 表 JOIN OOM 风险 | ~1.6 亿行 × 5 字段可能超 8GB 内存 | 加 `--sample` 模式做 demo 缩放 |
| `mine_code` 在 vbak 中为 NULL | LEFT JOIN 结果稀疏 | 过滤 NULL；说明业务键缺失情况 |
| DWA 上游切到 subject-分区后 DWA 列名需调整 | build_dwa_models.py 旧函数可能依赖原列名 | dual-write 阶段保留旧 system-分区路径，6.12 切换后逐步废弃 |
| Superset 部署链路过长 | 学员无法 5 分钟内重现 | design 写演进路径；demo 阶段不实现 |

## Migration Plan

**部署顺序**：
1. 新建 `scripts/build_dwa_sales_production.py`
2. 跑脚本生成 `dwa_sales_production` Delta Lake
3. DuckDB CLI 验证 4 个分析场景 SQL
4. 改 `scripts/build_dwa_models.py` 中 3 个 DWA 函数的 SQL 引用
5. 跑 `build_dwa_models.py --layer dwa` 验证旧 DWA 仍可跑
6. 跑 `verify_auto_lineage.py` 验证 lineage 仍通
7. 新建 `notebook/module12.ipynb`
8. 新建 `docs/Module12.md`
9. `openspec verify` + `openspec archive`

**回滚**（≤ 30 分钟）：
1. `rm -rf data/lakehouse/dwa/dwa_sales_production/`
2. `rm scripts/build_dwa_sales_production.py notebook/module12.ipynb`
3. `git checkout HEAD~1 -- scripts/build_dwa_models.py`
4. 旧 DWA 宽表仍用旧 system-分区

## Open Questions

- DuckDB `--sample 0.1` 是否影响 4 表 JOIN 性能？演示时是否必须缩放？
- `dwa_sales_production` 的 schema 字段数（待定）：用户改 SQL 时是否能保持 backward compat？
- 跨主题 JOIN 是否需要在 dwa_sales_production 上加 lineage 边（6.9 path）？建议加。

## Evolution Path（不实现，仅记录）

Phase 3 升级为 ClickHouse + Superset：
1. `docker run -d --name clickhouse-server -p 8123:8123 yandex/clickhouse-server:23.8`
2. `docker run -d --name superset -p 8088:8088 apache/superset:4.1.1-py312`
3. `scripts/build_dwa_sales_production.py` 替换为 `clickhouse-client` + `INSERT INTO dwa_sales_production SELECT ...`
4. Superset `SQLAlchemy URI: clickhouse://localhost:8123/default`
5. 看板 4 个图表：产销对比 / 煤质定价 / 安全趋势 / 订单履约
