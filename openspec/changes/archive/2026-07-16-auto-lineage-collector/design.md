# auto-lineage-collector — 技术设计

## Context

当前状态：

- `src/dg_platform/lineage_emitter.py` 的 `LineageEmitter` 上下文管理器已实现并通过 `sqlglot` 从 SQL 推导 inputs
- `build_dwa_sales_production.py` 已接入 LineageEmitter（job=`build_dwa_sales_production`，sql=`SQL_4TABLE_JOIN`）
- `build_dwa_models.py` 的 3 个 DWA ETL 函数（`build_dwa_sales_daily` / `build_dwa_tag_alarm` / `build_dwa_coal_quality`）**未接入**
- `verify_auto_lineage.py` 已定义 6 个 job 的预期 inputs，但 3 个 DWA job 从未被调用

约束：

- `LineageEmitter` 已稳定，不可修改接口
- GMS 在 `http://localhost:28080`，`DATAHUB_GMS_URL` 环境变量可覆盖
- 每个 DWA ETL 入口改动 ≤ 5 行（来自 `auto-lineage-collection` spec 要求）

## Goals / Non-Goals

**Goals:**

- 为 `build_dwa_models.py` 的 3 个 DWA ETL 函数接入 `LineageEmitter`
- 抽取共享 helper 函数，消除重复 boilerplate（`emit_output` + `__exit__` 调用）
- 更新 `verify_auto_lineage.py` 的 `EXPECTED_INPUT_FRAGMENTS` 与实际一致
- 更新文档，使 auto 通道描述与实际实现一致

**Non-Goals:**

- 不修改 `lineage_emitter.py` 本身（接口稳定）
- 不接入 `ingest_to_deltalake.py`（当前 `ingest_dwd` job 已在 `verify_auto_lineage.py` 但无 emit 实现，属于 Phase 2 下一轮范围）
- 不接入 `build_dimension_tables.py` 的 dim 函数（可选完善项）
- 不修改 `build_dwa_sales_production.py`（已接入，勿动）

## Decisions

### 决策 1：LineageEmitter 接入点在 `main()` 主循环，而非每个 ETL 函数内部

**选项 A（采用）**：在 `main()` 中每个 `write_delta()` 调用前加 `with LineageEmitter(...)` 包装

**选项 B**：在每个 `build_dwa_*()` 函数内部加 `with` 包装，修改函数签名

**选项 C**：用装饰器模式 `@emit_lineage(job_name, sql)` 包装函数

| | 优点 | 缺点 |
|---|---|---|
| A（采用）| 零侵入函数实现；SQL 字符串在 main 层可见，可直接传；与 `build_dwa_sales_production.py` 模式一致 | 每个 job 要单独写一个 `with` 块 |
| B | — | 修改函数内部逻辑；SQL 传入方式复杂化 |
| C | 最简洁 | 装饰器需额外模块；当前 `LineageEmitter` 接口不支持装饰器模式 |

**结论**：选项 A。与 `build_dwa_sales_production.py` 的实现模式保持一致。

### 决策 2：抽取共享 helper 函数消除 boilerplate

**重复代码模式**（3 个 job 各需）：

```python
if emit_lineage:
    ctx = LineageEmitter(job_name="...", sql=SQL, ...)
    ctx.__enter__()
    # ETL logic ...
    out_urn = f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"
    ctx.emit_output(out_urn, df)
    ctx.__exit__(None, None, None)
```

**共享 helper**：

```python
def _emit_lineage(job_name: str, sql: str, output_urn: str,
                  emit: bool = True) -> LineageEmitter | None:
    """包装 LineageEmitter 的 lifecycle，emit=False 时返回 None 不阻断 ETL。"""
    if not emit:
        return None
    ctx = LineageEmitter(job_name=job_name, sql=sql)
    ctx.__enter__()
    return ctx
```

每个入口简化为：

```python
ctx = _emit_lineage("build_dwa_sales_daily", SQL_SALES_DAILY, out_urn)
# ... ETL logic ...
if ctx:
    ctx.emit_output(out_urn, df)
    ctx.__exit__(None, None, None)
```

### 决策 3：SQL 字符串的组织

每个 DWA job 的 SQL 需要是"代表该 ETL 转换的 SQL"，供 `sqlglot` 解析推导 inputs。

| ETL job | SQL 内容 | inputs 推导结果 |
|---|---|---|
| `build_dwa_sales_daily` | `SELECT ... FROM dwd.vbak_parquet GROUP BY ERDAT` | `dwd.vbak` |
| `build_dwa_tag_alarm` | `SELECT ... FROM dwd.tags GROUP BY mine, face, tag` | `dwd.tags` |
| `build_dwa_coal_quality` | `SELECT ... FROM dwd.samples GROUP BY MINE_CODE, SAMPLE_TYPE` | `dwd.samples` |

**注意**：`sqlglot` 解析的是 view 名称（如 `dwd.vbak`），不是具体 parquet 文件路径——这是可接受的，因为 inputs 的语义是"数据来源表"，不是"具体文件"。

### 决策 4：`--lineage / --no-lineage` flag 复用

`build_dwa_sales_production.py` 已有 `--no-lineage` flag。`build_dwa_models.py` 的 `main()` 应复用相同逻辑：

```python
parser.add_argument("--lineage", action="store_true", default=True,
                    help="emit OpenLineage to GMS (default: True)")
```

## Risks / Trade-offs

| 风险 | 描述 | 缓解措施 |
|---|---|---|
| GMS 不可达时 ETL 失败 | `LineageEmitter._emit()` 失败会打印 warning 但不阻断（`except Exception: pass`） | 设计已处理，不额外处理 |
| `sqlglot` 解析 DuckDB SQL 失败 | `from_sql()` 失败降级返回 `inputs=[]`，event 仍发出但 inputs 为空 | 设计如此，无需改动 |
| `verify_auto_lineage.py` 查 MySQL 容器名变化 | hardcoded `"datahub-mysql-1"` 可能在不同环境失败 | 可接受，教学环境固定 |
