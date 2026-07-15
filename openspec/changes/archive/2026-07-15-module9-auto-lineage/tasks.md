## 1. 依赖与基础设施

- [x] 1.1 在 `pyproject.toml` dependencies 新增 `openlineage-python>=1.0`（HTTP transport 内置）+ `sqlglot>=20.0`，跑 `uv sync` 验证
- [x] 1.2 在 `datahub-quickstart.yml` 的 `datahub-gms-quickstart.environment` 加 `DATAHUB_OPENLINEAGE_ENV: PROD`，`docker compose -f datahub-quickstart.yml restart datahub-gms-quickstart` 重启 GMS

## 2. LineageEmitter 核心模块

- [x] 2.1 创建 `src/dg_platform/lineage_emitter.py`：`LineageEmitter` 类 + `__enter__` / `__exit__` 上下文协议
- [x] 2.2 集成 HTTP transport：`HttpConfig(url="http://localhost:28080", endpoint="/api/v1/lineage")` + `HttpTransport`，`OpenLineageClient(transport=HttpTransport(http_cfg))`
- [x] 2.3 实现 `from_sql(sql: str) -> list[str]`：用 sqlglot `find_all(exp.Table)` + `table_name()` 解析 `FROM` / `JOIN` 推导 inputs；CTE 用 `find_all(exp.CTE).alias_or_name` 过滤；`ParseError` 降级返回 `[]`
- [x] 2.4 实现 `emit_output(dataset_urn: str, df)`：注册 output，`__exit__` 时构造 `RunEvent(eventType=COMPLETE|FAIL, run, job, producer, inputs, outputs)` emit
- [x] 2.5 emit 失败重试：`HttpConfig(retry={"total": 5, "backoff_factor": 0.3, "status_forcelist": [500, 502, 503, 504]})`

## 3. ETL 入口集成（≤ 5 行/入口）

- [x] 3.1 改 `scripts/ingest_to_deltalake.py`：`ingest_ods()` / `ingest_dwd()` / `ingest_dwa()` 三个函数入口各加 `with LineageEmitter("xxx", sql=...) as e: e.emit_output(...)` 上下文
- [x] 3.2 改 `scripts/build_dwa_models.py`：`build_dwa_sales_daily()` / `build_dwa_tag_alarm()` / `build_dwa_coal_quality()` / `build_dwd_with_derived()` 四个函数入口加上下文
- [x] 3.3 改 `scripts/build_dimension_tables.py`：`build_dim_mine()` / `build_dim_customer()` / `build_dim_material()` 三个函数入口加上下文

## 4. 验证与端到端

- [x] 4.1 创建 `scripts/verify_auto_lineage.py`：跑完 ETL 后 `GET /aspects/<urlencoded_urn>?aspect=upstreamLineage` 查 GMS 真值，输出每条 auto 边的验证结果
- [x] 4.2 创建 `notebook/module9.ipynb`：演示 1 条手工边（`lineage_recipe.yaml`）+ 1 条自动边（ETL emit）并排，附 Playwright 抓 `notebook/step_images/module9_lineage_manual.png` 与 `module9_lineage_auto.png`
- [x] 4.3 端到端延迟测试：跑 ETL → 30 秒内能在 DataHub UI 看到新边（用 Playwright 截图或 `verify_auto_lineage.py` 轮询）
- [x] 4.4 UUID 格式 smoke test：emit 1 条事件 → GMS 接受并写 `upstreamLineage` aspect（验证 `uuid.uuid4()` 36 字符格式正确）

## 5. 兜底通道兼容

- [x] 5.1 更新 `lineage_recipe.yaml` 顶部注释：明确"业务跨系统 JOIN 与未自动覆盖边的兜底通道"
- [x] 5.2 跑 `uv run python scripts/emit_lineage.py` 验证 8 条原有手工边继续写入 GMS
- [x] 5.3 验证双通道去重：手工边 + auto 边对同一 dataset + upstream 时，OpenSearch 索引中只 1 条

## 6. 文档与收尾

- [x] 6.1 更新 `docs/Module3.md`：追加 6.9 升级说明（auto 通道 + 兜底共存）
- [x] 6.2 更新 `docs/Background.md` 第 6.3 节：标注 6.9 已完成，手工边 → 自动边升级
- [x] 6.3 更新 `README.md` 路径 B notebook 列表：加 `module9.ipynb`（**影响学习路径 B**）
- [x] 6.4 跑 `openspec verify --change module9-auto-lineage` 自检
- [x] 6.5 执行 `openspec archive module9-auto-lineage --yes` 归档
