## 1. 依赖核实与补充（无依赖，先做）

- [x] 1.1 核实 `pyproject.toml` 是否声明 `acryldata/datahub`（`datahub` 包）；若缺则 `uv add datahub`（`emit_via_rest_emitter.py` 已 import，应已装但未必声明）
- [x] 1.2 核实是否声明 `networkx`；若缺则 `uv add networkx`
- [x] 1.3 验证：`uv run python -c "import datahub; import networkx; print('ok')"` 成功

## 2. 重写 emit_lineage.py（依赖 1）

- [x] 2.1 删除 `import neo4j`、`write_lineage_to_neo4j()` 函数、`neo4j_fallback` 分支与 SUMMARY 中的 neo4j 计数
- [x] 2.2 改用 `DatahubRestEmitter` + `MetadataChangeProposalWrapper` + `schema_classes.UpstreamLineageClass/UpstreamClass`，参照 `emit_via_rest_emitter.py`
- [x] 2.3 保留 `load_recipe()` / `build_urn()` / `print_lineage_graph()`，重写 `build_upstream_lineage_aspect()` → 返回 `UpstreamLineageClass`
- [x] 2.4 `type` 字段：加工血缘用 `TRANSFORMED`，业务血缘边也用 `TRANSFORMED`（DataHub enum 无 business 类型，语义靠 recipe description）
- [x] 2.5 验证：`uv run python scripts/emit_lineage.py` 不报错，输出 8 条边写入成功

## 3. 修正 lineage_recipe.yaml（依赖 1）

- [x] 3.1 `sap_erp.vbak/vbap → lims.samples` 两条边删除 `join_key: KUNNR`，description 写明「声明式业务关系，两表无字面共享列」
- [x] 3.2 新增 3 条 DWA 加工血缘边：`dwd.vbak → dwa_sales_daily`、`pi_system.tags → dwa_tag_alarm`、`lims.samples → dwa_coal_quality`
- [x] 3.3 验证：`uv run python -c "import yaml; r=yaml.safe_load(open('lineage_recipe.yaml')); print(sum(len(x['upstream']) for x in r['lineage_relationships'] if x.get('upstream')))"` 输出 8

## 4. DWA 表注册 + 真验证脚本（依赖 2, 3）

- [x] 4.1 在 `scripts/emit_via_rest_emitter.py` 的 `ASSETS` 追加 3 张 DWA 表（platform=`dwa`，含中文描述）
- [x] 4.2 新增 `scripts/query_lineage.py`（只读）：对每条 recipe 边 `GET /aspects/<urn>?aspect=upstreamLineage`，取真实上游，输出 JSON 到 stdout（`{dataset, upstreams:[...]}`）
- [x] 4.3 新增 `scripts/verify_lineage.py`：复用 query_lineage 的查询逻辑，断言 `upstreams` 非空且含预期上游 URN；追加 OpenSearch `datasetindex_v2` 查询断言边已索引（轮询最长 30s）
- [x] 4.4 失败时非零退出 + 明确错误信息；可选 `--purge` 删除写入的 aspect（回滚用）
- [x] 4.5 验证：跑 `emit_via_rest_emitter.py`（注册 DWA）→ `emit_lineage.py`（写边）→ `verify_lineage.py` 全绿；`query_lineage.py` 输出合法 JSON

## 5. 离线血缘 API（依赖 1）

- [x] 5.1 新建 `src/dg_education/lineage.py`，实现 `load_lineage_graph(recipe_path)` 返回 networkx DiGraph
- [x] 5.2 实现 `upstream(graph, node)` / `downstream(graph, node)` / `blast_radius(graph, node)` 遍历函数
- [x] 5.3 实现 `render_ascii(graph)` 文本血缘图（DWA 层与源层分层显示）
- [x] 5.4 验证：`uv run python -c "from dg_education.lineage import load_lineage_graph; g=load_lineage_graph('lineage_recipe.yaml'); print(len(g.edges))"` 输出 8

## 6. 可视化扩展（依赖 5）

- [x] 6.1 在 `src/dg_education/visualization.py` 追加 `plot_lineage_graph(graph)`（networkx + matplotlib，中文字体沿用 `_ensure_chinese_font()`）
- [x] 6.2 追加 `plot_blast_radius(graph, node)` 影响面条形图
- [x] 6.3 验证：函数可调用，中文不乱码

## 7. API 导出（依赖 5, 6）

- [x] 7.1 更新 `src/dg_education/__init__.py`：导入 lineage + 新 visualization API
- [x] 7.2 更新 `__all__`
- [x] 7.3 验证：`uv run python -c "from dg_education import load_lineage_graph, plot_lineage_graph"` 成功

## 8. 教学 notebook（依赖 5, 6, 7）

- [x] 8.1 创建 `notebook/module3.ipynb`，第 1 cell 为「痛点故事」（< 200 字符，幕一/幕二对照：没血缘时追一个订单的煤质来源要翻 3 系统问 3 人 / 有血缘 5 分钟点图看到来源）
- [x] 8.2 第 2 cell：Setup（import + `load_lineage_graph`）
- [x] 8.3 第 3 cell：3 步学习节奏总览（markdown 表格）
- [x] 8.4 步骤 1：血缘是什么 + 两类（业务/加工）+ `render_ascii` 画 8 条边
- [x] 8.5 步骤 2：上下游追溯（从 `lims.samples` 上溯 2 跳、从 `dwa_coal_quality` 下钻），配业务影响白话；并 subprocess 调 `scripts/query_lineage.py` 拿 DataHub 真图，与 recipe 自建图对比确认边一致
- [x] 8.6 步骤 3：blast-radius 演示（DWA 层：异常煤质矿井 → 同期销售）+ 诚实声明「跨系统 CHARG 全链 = Phase 2 待解数据孤岛」
- [x] 8.7 附加：DataHub UI Lineage 标签页截图章节 + 延迟说明（5-30s）
- [x] 8.8 末尾引用 `notebook/module1.ipynb` / `module2.ipynb`

## 9. 文档与最终验证（依赖 8）

- [x] 9.1 更新 `docs/Module3.md`：写回正确端点/字段名/verify 脚本/诚实关系语义
- [x] 9.2 验证：`uv run jupyter notebook notebook/module3.ipynb` 全 cell 跑通无 error
- [x] 9.3 验证：module3.ipynb 全文搜索 `29200`/`/api/graphql`/`28080`/`emit_lineage.py`/`requests` 均 0 命中；`subprocess` 命中仅指向 `query_lineage.py`
- [x] 9.4 验证：`scripts/emit_lineage.py` 无 `import neo4j`
- [x] 9.5 验证：DataHub UI Lineage 标签页人工确认 8 条边可见
