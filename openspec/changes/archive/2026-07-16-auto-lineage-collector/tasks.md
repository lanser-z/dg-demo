# auto-lineage-collector — 任务清单

## 1. 探索与准备

- [x] 1.1 确认 DataHub GMS 在 `localhost:28080` 可达（`curl http://localhost:28080/health`）
- [x] 1.2 确认 `openlineage-python` 和 `sqlglot` 已安装（`uv run python -c "from openlineage.client.run import RunEvent; from sqlglot import parse; print('OK')"`）

## 2. 核心实现

### 2.1 实现共享 helper 函数

- [x] 2.1.1 在 `build_dwa_models.py` 添加 import：`from dg_platform.lineage_emitter import LineageEmitter`
- [x] 2.1.2 实现 `_emit_lineage(job_name, sql, output_urn, emit)` helper 函数，封装 `__enter__` / `emit_output` / `__exit__` 生命周期
- [x] 2.1.3 在 `main()` 添加 `--lineage` CLI flag（`action="store_true", default=True`）

### 2.2 为 `build_dwa_sales_daily` 接入 LineageEmitter

- [x] 2.2.1 在 `main()` 中 `build_dwa_sales_daily` 的 `write_delta()` 调用前加 `with LineageEmitter("build_dwa_sales_daily", sql=SQL_SALES)` 包装块
- [x] 2.2.2 构造 output URN：`dwa.sales.dwa_sales_daily` → platform=`dwa`，table=`dwa_sales_daily`
- [x] 2.2.3 用 DuckDB 的 `CREATE VIEW` SQL 作为 `sql` 参数（`SELECT ... FROM vbak_parquet ...`）

### 2.3 为 `build_dwa_tag_alarm` 接入 LineageEmitter

- [x] 2.3.1 在 `main()` 中 `build_dwa_tag_alarm` 的 `write_delta()` 调用前加 `with LineageEmitter("build_dwa_tag_alarm", sql=SQL_ALARM)` 包装块
- [x] 2.3.2 构造 output URN：`dwa.production.dwa_tag_alarm` → platform=`dwa`，table=`dwa_tag_alarm`

### 2.4 为 `build_dwa_coal_quality` 接入 LineageEmitter

- [x] 2.4.1 在 `main()` 中 `build_dwa_coal_quality` 的 `write_delta()` 调用前加 `with LineageEmitter("build_dwa_coal_quality", sql=SQL_QUALITY)` 包装块
- [x] 2.4.2 构造 output URN：`dwa.coal_quality.dwa_coal_quality` → platform=`dwa`，table=`dwa_coal_quality`

### 2.5 定义各 DWA job 的 sqlglot 解析用 SQL 字符串

- [x] 2.5.1 定义 `SQL_SALES` = `SELECT ... FROM dwd.sales.dwd_vbak GROUP BY ERDAT`
- [x] 2.5.2 定义 `SQL_ALARM` = `SELECT ... FROM dwd.production.dwd_tags GROUP BY mine, face, tag`
- [x] 2.5.3 定义 `SQL_QUALITY` = `SELECT ... FROM dwd.coal_quality.dwd_samples GROUP BY MINE_CODE, SAMPLE_TYPE`

## 3. 验证

- [x] 3.1 运行 `uv run python scripts/build_dwa_models.py --layer dwa --lineage` 确认无报错，ETL 完成
- [x] 3.2 运行 `uv run python scripts/verify_auto_lineage.py` 确认 `build_dwa_sales_daily`（→ sales.dwd_vbak）/ `build_dwa_tag_alarm`（→ production.dwd_tags）/ `build_dwa_coal_quality`（→ coal_quality.dwd_samples）三个 job 的 inputs 非空，sqlglot SQL 解析正确
- [x] 3.3 GMS HTTP 200 OK，`datahub-gms-quickstart` 容器 healthy（Docker 验证通过）；Lineage UI 截图依赖 DataHub Frontend 交互，本次通过验证脚本确认

## 4. 文档更新

- [x] 4.1 更新 `docs/Module3.md` §6.9 实现状态，说明 4 个 ETL 入口（3 个 DWA + 1 个 cross-system）已接入 auto 通道
- [x] 4.2 更新快速命令汇总，加 `--lineage` / `--no-lineage` flag 说明（notebook 截图已存在，无需改动）
