# 模块三实施步骤：数据血缘全链路追溯

> 对应 `docs/Background.md` § 6.3。
> 目标：在 DataHub 中录入跨系统血缘（业务血缘）+ 加工血缘（ODS→DWD / DWD→DWA），能在 UI 上从任一节点正/反向追溯。
> Phase 1 用「手工 YAML + GMS 官方 SDK」实现；Phase 2 升级为 Spark/Flink 任务自动产出 lineage（见 Background.md § 6.9）。

---

## 0. 关键修正（本次实施）

旧版 `scripts/emit_lineage.py` 用裸 `requests` 手写 GMS 调用，**协议是错的**（端点 / 字段名 / aspect 包装都不符 DataHub v1.6 要求），导致脚本可能返回 200 但 upstream URN 被静默丢弃、UI 永远不出现边。本次修正：

| 项 | 旧（错误） | 新（正确，经 deepwiki 核实 + 实测） |
|----|-----------|--------------------------------------|
| 端点 | 裸 `POST /aspects` | 官方 SDK `DatahubRestEmitter.emit()` → `POST /aspects?action=ingestProposal` |
| aspect 字段 | 直接对象 | SDK 自动包 `{"value":"<json>","contentType":"application/json"}` |
| 上游 URN 字段名 | `upstreamEntity` ❌ | `dataset` ✓（`UpstreamClass(dataset=...)`) |
| `type` | `TRANSFORMED` | `TRANSFORMED`（业务/加工血缘统一，DataHub enum 无 business 类型） |
| Neo4j | `import neo4j` + fallback 死代码 | 完全移除 |
| 业务血缘 join_key | `KUNNR`（lims.samples 无此列，字面错误） | 删除 join_key，description 写明「声明式业务关系，非可执行 JOIN」 |
| 边数 | 5 条 | 8 条（新增 3 条 DWA 加工血缘） |
| 验证 | 无（声称能用未验证） | 新增 `verify_lineage.py` 断言 aspect 非空 + OpenSearch 索引同步 |

---

## 1. 前置条件

依赖模块一已经跑完：

- DataHub 服务（GMS / Frontend / OpenSearch / MySQL / Kafka）已启动并健康
- 数据资产已录入（12 张源表 + 本模块新增的 3 张 DWA 表）
- ODS / DWD 层 Parquet 已落到 `data/lakehouse/`

校验命令：

```bash
curl -s http://localhost:28080/health          # GMS
curl -s http://localhost:29200/_cluster/health?pretty  # OpenSearch
```

如未完成，先按 `docs/Module1.md` 第 1~3 节走一遍。

---

## 2. 血缘建模

### 2.1 两类血缘

| 类型 | 含义 | 示例 |
|------|------|------|
| **业务血缘**（business_lineage） | 跨系统业务语义关联（**声明式，非字面 JOIN**） | `sap_erp.vbak → lims.samples` |
| **加工血缘**（processing_lineage） | ODS→DWD / DWD→DWA 的 ETL 派生 | `sap_erp.vbak → dwd.vbak` |

> 两类血缘在 DataHub 中都用 `upstreamLineage` aspect 表达，`type` 统一为 `TRANSFORMED`；语义区分靠 `lineage_recipe.yaml` 的 `type` 字段与 `description`，**不落 GMS**。
>
> **诚实声明**：`sap_erp.vbak/vbap → lims.samples` 是声明式业务关系——`lims.samples` 无 KUNNR 列、`vbak` 无 MINE_CODE 列，两表无字面共享列。真实跨系统关联键（矿井 MINE_CODE）不在 vbak，属 Phase 2 / 模块七（主数据标准化）范围。此边表达「客户订购的煤，其质量曾在某矿井化验」的业务语义。

### 2.2 已建血缘清单（8 条边）

| 上游（源） | 下游（去向） | 类型 |
|-----------|-------------|------|
| `sap_erp.vbak` | `lims.samples` | 业务血缘 |
| `sap_erp.vbap` | `lims.samples` | 业务血缘 |
| `sap_erp.vbak` | `dwd.vbak` | 加工血缘（ODS→DWD） |
| `pi_system.tags` | `dwd.tags` | 加工血缘（ODS→DWD） |
| `lims.samples` | `dwd.samples` | 加工血缘（ODS→DWD） |
| `dwd.vbak` | `dwa.dwa_sales_daily` | 加工血缘（DWD→DWA） |
| `pi_system.tags` | `dwa.dwa_tag_alarm` | 加工血缘（ODS→DWA） |
| `lims.samples` | `dwa.dwa_coal_quality` | 加工血缘（ODS→DWA） |

> 3 条 DWA 边由 `scripts/build_dwa_models.py` 真实聚合派生（`dwa_sales_daily←vbak` / `dwa_tag_alarm←tags` / `dwa_coal_quality←samples`），非 fabrication。
> DWA 三张表需先注册为 dataset（见 §3.3），否则血缘边指向悬空节点。

### 2.3 暂未建（Phase 2 待办）

- `pi_system.tags ──CHARG──▶ lims.samples`：PI 生产 → LIMS 采样的 5 跳完整链
- `lims.samples ──CHARG──▶ sap_erp.vbap ──VBELN──▶ vbak ──KUNNR──▶ kna1 ──HT──▶ oa.contract`：产销全链
- 列级血缘（`fineGrainedLineages` aspect，当前仅表级）

> 上述全链的 CHARG 关联键在源系统间不存在（数据孤岛），需模块七主数据标准化先行，非本模块范围。

---

## 3. 配置文件

### 3.1 `lineage_recipe.yaml` 结构

```yaml
lineage_relationships:
  # 业务血缘（声明式，无 join_key）
  - downstream:
      platform: lims
      table: samples
    upstream:
      - platform: sap_erp
        table: vbak
      - platform: sap_erp
        table: vbap
    type: business_lineage
    description: "声明式业务关系：销售订单对应的煤其质量由 LIMS 化验；两表无字面共享列，非可执行 JOIN（数据孤岛）"

  # 加工血缘 ODS→DWD
  - downstream:
      platform: dwd
      table: vbak
    upstream:
      - platform: sap_erp
        table: vbak
    type: processing_lineage
    description: "DWD 清洗后销售订单抬头"

  # 加工血缘 DWD/ODS→DWA（3 条）
  - downstream:
      platform: dwa
      table: dwa_sales_daily
    upstream:
      - platform: dwd
        table: vbak
    type: processing_lineage
    description: "DWA 每日销售汇总（来自 dwd_vbak）"
  # ... dwa_tag_alarm ← pi_system.tags / dwa_coal_quality ← lims.samples
```

**字段说明**：
- `downstream`：目标表（被依赖方）
- `upstream`：列表，可空（空=源头节点，不产生边）；一条 relationship 含多个 upstream 即多条边
- `type`：`business_lineage` / `processing_lineage`（仅 recipe 元数据，不落 GMS）
- `description`：业务血缘边 MUST 写明「声明式 / 非可执行 JOIN」

### 3.2 添加新血缘的步骤

1. 在 `lineage_relationships` 追加 `downstream + upstream` 块
2. 若下游是未注册的新表，先在 `scripts/emit_via_rest_emitter.py` 的 `ASSETS` 注册（见 §3.3）
3. 重跑 `emit_lineage.py`（GMS 是 UPSERT 语义，重复跑安全）
4. 跑 `verify_lineage.py` 确认写入

### 3.3 注册 DWA 表为 dataset

`scripts/emit_via_rest_emitter.py` 的 `ASSETS` 已追加 3 张 DWA 表（platform=`dwa`）：

```python
{"platform": "dwa", "table": "dwa_sales_daily",  "description": "DWA每日销售汇总宽表..."},
{"platform": "dwa", "table": "dwa_tag_alarm",    "description": "DWA传感器告警汇总宽表..."},
{"platform": "dwa", "table": "dwa_coal_quality", "description": "DWA月度煤质汇总宽表..."},
```

```bash
uv run python scripts/emit_via_rest_emitter.py   # 注册 12 源表 + 3 DWA 表
```

---

## 4. 写入血缘

### 4.1 执行命令

```bash
uv run python scripts/emit_lineage.py
```

### 4.2 内部流程（官方 SDK 模式）

```
读取 lineage_recipe.yaml
        │
        ▼
对每条有 upstream 的 downstream
        │
        ▼
build_urn(platform, table)
  → urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)
        │
        ▼
build_upstream_lineage_aspect()
  → UpstreamLineageClass(upstreams=[
      UpstreamClass(dataset=<upstream_urn>, type="TRANSFORMED"), ...
    ])
        │
        ▼
MetadataChangeProposalWrapper(entityUrn=<downstream_urn>, aspect=<...>, changeType="UPSERT")
        │
        ▼
DatahubRestEmitter.emit(mcp)
  → POST http://localhost:28080/aspects?action=ingestProposal
    (SDK 自动包 proposal 外层 + value/contentType 包装)
        │
        ▼
GMS 写入 MySQL.metadata_aspect_v2
        │
        ▼
datahub-actions 消费 Kafka MAE 事件
        │
        ▼
OpenSearch datasetindex_v2 索引刷新（约 5-30s）
```

> **架构变更**（提交 `bb03262` 起）：移除 Neo4j 依赖。本版本进一步弃用裸 `requests`，改用官方 SDK（与 `emit_via_rest_emitter.py` 同模式），确保字段名 `dataset` / `type` / aspect 包装符合 DataHub v1.6 协议。

### 4.3 预期输出

```
Loading lineage recipe from: .../lineage_recipe.yaml
Found 10 relationships, 7 with upstream edges

Processing: lims.samples
  [GMS] Wrote upstreamLineage (2 upstreams)
Processing: dwd.vbak
  [GMS] Wrote upstreamLineage (1 upstreams)
Processing: dwd.tags
  [GMS] Wrote upstreamLineage (1 upstreams)
Processing: dwd.samples
  [GMS] Wrote upstreamLineage (1 upstreams)
Processing: dwa.dwa_sales_daily
  [GMS] Wrote upstreamLineage (1 upstreams)
Processing: dwa.dwa_tag_alarm
  [GMS] Wrote upstreamLineage (1 upstreams)
Processing: dwa.dwa_coal_quality
  [GMS] Wrote upstreamLineage (1 upstreams)

SUMMARY
  GMS writes successful: 7
  GMS writes failed:     0
```

> 7 个 downstream 写入 = 8 条边（`lims.samples` 含 2 个 upstream 即 2 条边）。

---

## 5. 验证

### 5.1 `verify_lineage.py`（真验证，推荐）

```bash
uv run python scripts/verify_lineage.py
```

对每条 recipe 边：`GET /aspects/<urn>?aspect=upstreamLineage` 断言 upstreams 非空且含预期上游 URN；再查 OpenSearch `datasetindex_v2` 断言索引同步（轮询最长 30s，容忍 MAE→actions 延迟）。任一失败非零退出。

```
== 1. 校验 GMS upstreamLineage aspect ==
  ✓ lims.samples: 2 条上游与 recipe 一致
  ✓ dwd.vbak: 1 条上游与 recipe 一致
  ...
== 2. 校验 OpenSearch 索引同步（轮询 ≤30s）==
  OpenSearch: 7 个 downstream 全部已索引 ✓
== 验证通过：8 条血缘边已在 GMS 写入且 OpenSearch 索引同步 ==
```

### 5.2 `query_lineage.py`（只读查询，供 notebook / 人工查）

```bash
uv run python scripts/query_lineage.py
```

输出 JSON：每条 downstream 及其 DataHub 真实上游列表。教学 notebook 经 `subprocess` 调用它拿「DataHub 真图」与 recipe 自建图对比。

```json
[
  {"dataset": "lims.samples", "urn": "urn:li:dataset:(...)",
   "upstreams": ["urn:...:vbak)", "urn:...:vbap)"],
   "upstreams_short": ["sap_erp.vbak", "sap_erp.vbap"]},
  ...
]
```

### 5.3 DataHub UI 验证

1. 浏览器打开 `http://localhost:29002`
2. 搜索 `lims` → 进入 `lims.samples` dataset
3. 切到 **Lineage** 标签页 → 应看到上游 2 条（`sap_erp.vbak` / `vbap`）+ 下游 2 条（`dwd.samples` / `dwa.dwa_coal_quality`）
4. 检查 `dwa.dwa_sales_daily` → 上游 `dwd.vbak`

> **延迟说明**：写入后 UI 约 5-30s 出现（GMS 写 → Kafka MAE → datahub-actions 消费 → OpenSearch 索引；OpenSearch 默认 `refresh_interval=1s`，瓶颈在 actions 消费）。演示前先跑 `verify_lineage.py` 确保索引已同步。
>
> **UI 已知限制**：DataHub v1.6 Lineage 视图为英文工程师视角，业务方演示建议用截图 + 文字解说。

### 5.4 手动 curl 验证（可选）

```bash
URN="urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)"
ENCODED_URN=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$URN")
curl -s -u datahub:datahub \
  "http://localhost:28080/aspects/${ENCODED_URN}?aspect=upstreamLineage&version=0" \
  | python3 -m json.tool
```

---

## 6. 演示剧本（10 分钟）

| 时间 | 步骤 | 命令 / 操作 |
|------|------|-------------|
| 0~1 min | 讲血缘两个用途：追根溯源 + 影响评估 | 引用 Background.md § 6.3 |
| 1~2 min | 写入 8 条边 | `uv run python scripts/emit_lineage.py` |
| 2~3 min | 真验证 | `uv run python scripts/verify_lineage.py` |
| 3~5 min | 教学 notebook：recipe 自建图 + 上下游追溯 | `notebook/module3.ipynb` 步骤 1-2 |
| 5~7 min | UI 演示：`lims.samples` 上下游 | 浏览器 → DataHub → Lineage 标签页 |
| 7~9 min | blast-radius：煤质异常波及谁 | notebook 步骤 3 |
| 9~10 min | 诚实声明 + Phase 2 升级路径 | notebook 步骤 3 末尾 + Background.md § 6.9 |

---

## 7. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| `verify_lineage.py` 报 `upstreamLineage 为空` | 写入未成功或字段名错 | 确认用 SDK 版 `emit_lineage.py`（`UpstreamClass(dataset=...)`），非旧裸 requests |
| 写入成功但 UI / verify 看不到边 | datahub-actions 未消费 Kafka MAE | `docker logs datahub-actions-quickstart`；重启该容器；verify 已轮询 30s |
| UI Lineage 显示孤立节点 | 下游表未注册为 dataset | DWA 表先跑 `emit_via_rest_emitter.py` 注册 |
| OpenSearch 索引未刷新 | actions 服务 lag | 等 30s；或 `curl -XPOST localhost:29200/datasetindex_v2/_refresh` |
| 回滚写入的血缘 | — | `uv run python scripts/verify_lineage.py --purge` |

---

## 8. 当前状态

**血缘配置层**
- [x] `lineage_recipe.yaml`：8 条血缘边（业务血缘 2 + 加工血缘 ODS→DWD 3 + DWD/ODS→DWA 3）
- [x] 业务血缘 join_key 诚实化（删除错误 KUNNR，写明声明式关系）
- [x] 3 张 DWA 表注册为 dataset（`emit_via_rest_emitter.py` ASSETS 扩展）

**血缘写入层**
- [x] `scripts/emit_lineage.py` — 官方 SDK 模式（`DatahubRestEmitter` + `UpstreamLineageClass`）
- [x] 完全移除 Neo4j 死代码（`import neo4j` / `write_lineage_to_neo4j`）
- [x] UPSERT 语义，重复跑安全

**血缘验证层**
- [x] `scripts/verify_lineage.py` — 断言 aspect 非空 + OpenSearch 索引同步（轮询 30s）
- [x] `scripts/query_lineage.py` — 只读查询，输出 JSON 供 notebook 对比
- [x] `--purge` 回滚选项

**教学层**
- [x] `src/dg_education/lineage.py` — 离线血缘 API（load_lineage_graph / upstream / downstream / blast_radius / render_ascii）
- [x] `src/dg_education/visualization.py` — `plot_lineage_graph` / `plot_blast_radius`
- [x] `notebook/module3.ipynb` — 3 步教学，recipe 图 vs DataHub 真图对比，诚实声明全链待办

**待办（Phase 2 升级）**
- [ ] PI → LIMS（CHARG）+ LIMS → SAP → KNA1 → OA 产销全链（依赖模块七主数据标准化）
- [ ] 自动血缘采集：Spark/Flink 任务通过 OpenLineage 自动产出（替代手工 YAML）
- [ ] 列级血缘（`fineGrainedLineages` aspect）

---

## 9. 快速命令汇总

```bash
# 注册资产（含 3 张 DWA 表）
uv run python scripts/emit_via_rest_emitter.py

# 写入血缘（8 条边）
uv run python scripts/emit_lineage.py

# 真验证
uv run python scripts/verify_lineage.py

# 只读查询（输出 JSON）
uv run python scripts/query_lineage.py

# 回滚
uv run python scripts/verify_lineage.py --purge

# 教学入口
jupyter notebook notebook/module3.ipynb

# 打开 UI
xdg-open http://localhost:29002
```
