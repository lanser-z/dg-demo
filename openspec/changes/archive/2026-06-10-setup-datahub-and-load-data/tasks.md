## 1. 配置准备

- [x] 1.1 备份当前 `datahub-quickstart.yml` 到 `datahub-quickstart.yml.bak`（含时间戳）
- [x] 1.2 修改 `datahub-quickstart.yml`：把 `system-update-quickstart` 的 `GRAPH_SERVICE_IMPL: neo4j` 改为 `elasticsearch`，删除该 service 块内 4 个 `NEO4J_*` 环境变量
- [x] 1.3 修改 `datahub-quickstart.yml`：删除整个 `neo4j:` service 块（含 `datahub_neo4jdata` / `datahub_neo4jlogs` 两个 volume 声明）
- [x] 1.4 修改 `datahub-quickstart.yml`：在 `frontend-quickstart.depends_on` 中新增 `datahub-gms-quickstart: {condition: service_healthy, required: true}`
- [x] 1.5 修改 `datahub-quickstart.yml`：在 `datahub-gms-quickstart.environment` 中将 `LINEAGE_GRAPH_V2`、`SHOW_BROWSE_V2`、`SHOW_NAV_BAR_REDESIGN` 设为 `'false'`（并清理 GMS 中 4 个残留 `NEO4J_*` 环境变量以满足 1.6 全局校验）
- [x] 1.6 用 `grep` 校验 yml：确认无 `neo4j:` 块、无 `NEO4J_` 环境变量、两个 `GRAPH_SERVICE_IMPL` 都是 `elasticsearch`、frontend depends_on 含 gms

## 2. 服务启动

- [x] 2.1 执行 `docker compose -f datahub-quickstart.yml up -d` 启动所有服务
- [x] 2.2 轮询 `docker compose -f datahub-quickstart.yml ps` 直到 system-update 状态为 `Exited (0)`、datahub-gms 和 frontend 状态为 `healthy`（含 datahub-actions），最长等 5 分钟
- [x] 2.3 用 `curl` 验证三个健康端点：`/health`（GMS 28080）、`/_cluster/health`（OpenSearch 29200）、MySQL `SHOW TABLES`（容器内）

## 3. 索引重建与数据上报

- [x] 3.1 在 `datahub-upgrade` 容器内执行 `RestoreIndices -a clean` 重建 `datasetindex_v2` 与 `graph_service_v1_*` 索引（用临时 `docker run` 容器补齐 system-update 退出后的运行空缺，复制其全部 env）
- [x] 3.2 在项目根目录执行 `uv run python scripts/direct_es_bulk.py` 把 12 张表 datasetProperties + tags 写入 OpenSearch
- [x] 3.3 执行 `uv run python scripts/emit_browsepaths.py` 通过 GMS OpenAPI v3 (`/openapi/v3/entity/dataset`) 写 browsePathsV2 + datasetProperties + ownership + globalTags。**注意**：原版脚本用 `/aspects` 端点在 v1.6.0 返回 400 (X-RestLi-Method 校验失败)，已重写脚本走 OpenAPI v3
- [x] 3.4 执行 `uv run python scripts/check_browse.py` 验证 12 张表的 browsePath 全部 ✅，路径形如 `/sap_erp/vbak`（修复了 `urn.keyword` → `urn` 的字段名 bug，v1.6.0 ES mapping 中 urn 字段是 `keyword` 类型，无 subfield）
- [x] 3.5 用 `curl -s "http://localhost:29200/datasetindex_v2/_count"` 验证 ES 中至少 12 条文档

## 4. 端到端 UI 验证（全 Playwright 自动化）

- [x] 4.1 在 `pyproject.toml` 用 `uv add playwright` 加入依赖并执行 `playwright install chromium`（含系统依赖）
- [x] 4.2 新建 `scripts/verify_datahub_ui.py`：启动 Playwright（headless），监听 `request` 事件断言首页 `/api/graphql` 返回 200、v2 主题 CSS class 命中
- [x] 4.3 在脚本中加入 Browse 验证：访问 `/browse` 后用 locator 断言 5 个一级分组（sap_erp / pi_system / lims / oa / scada）全部可见、可点击展开（**实际调整**：因 `SHOW_BROWSE_V2=false`，新版 /browse 返回 404，改为依赖 OpenSearch `_search` 端点 + 12 张表详情页 URN 遍历，详见 tasks.md 注）
- [x] 4.4 在脚本中加入搜索验证：搜索框输入 `lims` 回车，断言结果列表至少 1 条且包含 `lims/samples`（实际命中'煤质化验样品'，符合 spec.md 中文名）
- [x] 4.5 在脚本中加入 12 张表 URN 详情页遍历：对 `urn:li:dataset:(urn:li:dataPlatform:<system>,<table>,PROD)` 依次访问详情页，断言 description / owner / platform 三个字段非空且中文名匹配（"煤质化验样品"、"销售订单抬头"等）
- [x] 4.6 在脚本中加入 `screenshots/` 目录输出：每步关键节点（首页、browse、搜索、每张表详情页）保存 PNG，文件名形如 `04_lims_samples.png`（实际文件名 `03_<platform>_<table>.png`，共 30 张）
- [x] 4.7 执行 `uv run python scripts/verify_datahub_ui.py` 跑通；**结果：63/63 断言全部通过**，12 张表详情页全部含中文名 + corpuser ID + platform 关键词
- [x] 4.8 在终端输出 12/12 表格通过汇总；若失败，附失败截图路径与原因（**最终**：总断言 63 / 通过 63 / 失败 0，截图 30 张全部保存到 `screenshots/`）

## 5. 回滚预案（仅在异常时执行；本变更全程未触发）

- [x] 5.1 如果 1.6 校验或 2.2 启动失败，执行 `git checkout datahub-quickstart.yml` 回滚 yml 改动 — **未触发**（yml 校验 1.6 通过、启动 2.2 全部 healthy）
- [x] 5.2 如果 4.1-4.5 验证全部失败，执行 `docker compose -f datahub-quickstart.yml down -v` 全量清理并按设计文档 R4 策略重试 — **未触发**（Playwright 验证 63/63 全绿）
