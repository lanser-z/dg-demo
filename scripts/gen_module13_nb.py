#!/usr/bin/env python
"""Generate notebook/module13_nl2sql.ipynb — NL2SQL 智能问数教学 Notebook。"""
import json
import uuid

def _markdown(source_lines):
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": [l + "\n" for l in source_lines],
    }

def _code(source_lines):
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "outputs": [],
        "source": [l + "\n" for l in source_lines],
    }

cells = []

# ── Cell 0: Title + Pain Point Story ────────────────────────────────
cells.append(_markdown([
    "# 模块十三：基于 DataHub 血缘的 NL2SQL 智能问数",
    "",
    "## 痛点故事",
    "",
    "> 业务主任想查「上个月精煤灰分排名」，但他不会写 SQL...",
    "> 找 IT 排期要 3 天，等报表要 2 天，拿到数已经下周了。",
    "> 如果能直接用中文问，系统自动生成 SQL 查数，5 秒出结果？",
    "",
    "DataHub 血缘图蕴含的表关系、JOIN 键、字段映射，正是 NL2SQL 最需要的上下文。",
    "本模块展示如何把血缘图从「可视化资产」升级为「AI 可消费的语义图谱」。",
]))

# ── Cell 1: Architecture Overview ────────────────────────────────────
cells.append(_markdown([
    "## 架构概览",
    "",
    "整个 NL2SQL 智能问数流程如下：",
    "",
    "```",
    "用户问题 ───────────────────────────────┐",
    "                                          v",
    "           ┌──────────────────┐     ┌──────────┐",
    "           │  上下文构建器     │◄────│ DataHub  │",
    "           │ (build_context)  │◄────│  GMS     │",
    "           └────────┬─────────┘     │ REST API │",
    "                    │               └──────────┘",
    "                    v",
    "           ┌──────────────────┐",
    "           │   NL2SQL 引擎    │───────► LLM (MiniMax-M2.7)",
    "           │  (NL2SQLEngine)  │───────► 生成 SQL",
    "           └────────┬─────────┘",
    "                    v",
    "           ┌──────────────────┐",
    "           │   DuckDB 执行    │───────► Delta Lake / Parquet",
    "           └────────┬─────────┘",
    "                    v",
    "           结果表格 + 血缘解释",
    "```",
    "",
    "**三步走**：问题 -> 上下文（血缘 + 词典 + schema）-> SQL 生成 + 执行 + 血缘溯源。",
    "核心洞察：血缘图不只是给人看的可视化，更是 AI 理解数据关系的语义骨架。",
]))

# ── Cell 2: Step Breakdown Table ──────────────────────────────────────
cells.append(_markdown([
    "## 5 步学习节奏",
    "",
    "| 步骤 | 目标 | 核心概念 |",
    "|------|------|----------|",
    "| 步骤 1: 字段业务词典 | 术语消解（精煤 -> SAMPLE_TYPE='精煤'） | glossaryTerms + glossary_terms.yaml |",
    "| 步骤 2: 列级血缘 | 字段溯源（avg_ash_content <- AD） | fineGrainedLineages + columnMappings |",
    "| 步骤 3: 上下文构建 | 从 GMS 真实查询血缘/词典/schema | build_context() |",
    "| 步骤 4: NL2SQL 引擎 | LLM 生成 SQL + DuckDB 执行 + 血缘解释 | NL2SQLEngine.ask() |",
    "| 步骤 5: 测试验证 | 8 题端到端验证 | 批量测试 + 判定 |",
]))

# ── Cell 3: Setup ─────────────────────────────────────────────────────
cells.append(_code([
    "# ── Setup ─────────────────────────────────────────────────────────────",
    "# 把 src/ 加入 Python 路径，以便 import 项目模块",
    "import sys, os, json, yaml",
    "sys.path.insert(0, os.path.join(os.getcwd(), 'src'))",
    "",
    "# ── GMS 连通性检查 ──",
    "import requests",
    "GMS = \"http://localhost:28080\"",
    "try:",
    "    r = requests.post(f\"{GMS}/api/graphql\",",
    "                      json={\"query\": \"{ __typename }\"},",
    "                      auth=(\"datahub\", \"datahub\"), timeout=3)",
    "    ok = r.status_code == 200 and r.json().get(\"data\", {}).get(\"__typename\") == \"Query\"",
    "    print(\"DataHub GMS:\", \"\\U0001f7e2 健康\" if ok else \"\\U0001f534 不可达\")",
    "except Exception as e:",
    "    print(\"DataHub GMS: \\U0001f534 不可达 (\", e, \")\")",
    "    ok = False",
    "print(\"项目根:\", os.getcwd())",
    "print(\"src/ 已加入 path, 准备导入工程模块\")",
]))

# ── Cell 4: Markdown Step 1 ───────────────────────────────────────────
cells.append(_markdown([
    "## 步骤 1：字段业务词典 —— 让 LLM 懂业务黑话",
    "",
    "**为什么需要词典？**",
    "LLM 不认识「精煤」「灰分」「热值」这些煤炭行业术语。",
    "数据库里只有 `SAMPLE_TYPE`、`AD`、`QGR_AD` 这样的字段名。",
    "字段业务词典（glossary_terms.yaml）就是连接「业务语言」和「数据库字段」的桥梁。",
    "",
    "**词典里有什么？**",
    "- `cn_name`: 字段中文名（灰分 -> AD）",
    "- `business_terms`: 业务同义词列表（精煤, 煤炭类型 -> SAMPLE_TYPE）",
    "- `value_mappings`: 编码值翻译（M001 -> 鄂尔多斯一号煤矿）",
    "",
    "下面先看看词典的原始内容，再查 DataHub GMS 中已经注册的 glossaryTerms。",
]))

# ── Cell 5: Code display glossary content ─────────────────────────────
cells.append(_code([
    "# ── 展示 glossary_terms.yaml 片段 ──",
    "with open('data/glossary_terms.yaml', encoding='utf-8') as f:",
    "    glossary = yaml.safe_load(f)",
    "",
    "entries = glossary.get('glossary', [])",
    "print(f\"词典共 {len(entries)} 张表\\n\")",
    "",
    "# 展示 dwa_coal_quality 的字段（NL2SQL 最常用的宽表）",
    "for entry in entries:",
    "    if entry.get('table') == 'dwa_coal_quality':",
    "        print(f\"═══ {entry['table']} ({entry.get('table_cn', '')}) ═══\")",
    "        for col in entry.get('columns', [])[:7]:",
    "            terms = col.get('business_terms', [])",
    "            vm = col.get('value_mappings', {})",
    "            print(f\"  {col['column']:20s} | {col['cn_name']:8s} | 术语={terms}\")",
    "            if vm:",
    "                print(f\"  {'':20s} | {'':8s} | 映射={dict(list(vm.items())[:3])}\")",
    "        break",
    "",
    "# 展示 lims.samples（核心源表，含 value_mappings）",
    "print()",
    "for entry in entries:",
    "    if entry.get('table') == 'samples' and entry.get('platform') == 'lims':",
    "        print(f\"═══ {entry['platform']}.{entry['table']} ({entry.get('table_cn', '')}) ═══\")",
    "        for col in entry.get('columns', [])[:5]:",
    "            terms = col.get('business_terms', [])",
    "            vm = col.get('value_mappings', {})",
    "            print(f\"  {col['column']:15s} | {col['cn_name']:6s} | 术语={terms}\")",
    "            if vm:",
    "                print(f\"  {'':15s} | {'':6s} | 映射={vm}\")",
    "        break",
]))

# ── Cell 6: Code query GMS glossaryTerms ──────────────────────────────
cells.append(_code([
    "# ── 从 DataHub GMS 查询 glossaryTerms ──",
    "# 构造 dataset URN",
    "import urllib.parse",
    "URN_DWA_CQ = \"urn:li:dataset:(urn:li:dataPlatform:dwa,dwa_coal_quality,PROD)\"",
    "encoded = urllib.parse.quote(URN_DWA_CQ, safe=\"\")",
    "",
    "# 查 glossaryTerms aspect",
    "r = requests.get(f\"{GMS}/aspects/{encoded}?aspect=glossaryTerms&version=0\",",
    "                 auth=(\"datahub\", \"datahub\"), timeout=10)",
    "if r.status_code == 200:",
    "    data = r.json()",
    "    aspect = data.get(\"aspect\", {}).get(\"com.linkedin.common.GlossaryTerms\", {})",
    "    terms = aspect.get(\"terms\", [])",
    "    print(f\"GMS 返回 glossaryTerms: {len(terms)} 条\\n\")",
    "    for t in terms[:8]:",
    "        term_name = t.get('urn', '').split(':')[-1] if t.get('urn') else ''",
    "        ctx = t.get('context', '')",
    "        print(f\"  \\U0001f4cc {term_name:30s}  ctx={ctx}\")",
    "    if len(terms) > 8:",
    "        print(f\"  ... (还有 {len(terms)-8} 条)\")",
    "else:",
    "    print(\"GMS 无 glossaryTerms 或请求失败:\", r.status_code)",
    "    print(\"(这可能是因为 glossaryTerms 尚未通过 emit_glossary.py 写入)\")",
]))

# ── Cell 7: Markdown Step 2 ───────────────────────────────────────────
cells.append(_markdown([
    "## 步骤 2：列级血缘 —— 字段从哪里来",
    "",
    "**为什么列级血缘对 NL2SQL 至关重要？**",
    "",
    "数据库字段名经常让人困惑：`avg_ash_content` 是什么意思？",
    "列级血缘告诉我们：这个字段来自 `lims.samples.AD` 字段的 `AVG(AD)` 聚合。",
    "LLM 有了这个信息，就能理解：",
    "- `avg_ash_content` = 平均灰分",
    "- 它上游是 `AD`（空气干燥基灰分）",
    "- 它的业务含义和 `AD` 一样，只是做了 AVG 聚合",
    "",
    "**lineage_recipe.yaml** 中定义了 3 张 DWA 表的 columnMappings（列级映射），",
    "下面先看文件中的声明，再从 GMS 查询已经注册的 fineGrainedLineages。",
]))

# ── Cell 8: Code display columnMappings ────────────────────────────────
cells.append(_code([
    "# ── 展示 lineage_recipe.yaml 的 columnMappings ──",
    "with open('lineage_recipe.yaml', encoding='utf-8') as f:",
    "    recipe = yaml.safe_load(f)",
    "",
    "for rel in recipe.get('lineage_relationships', []):",
    "    cm = rel.get('columnMappings')",
    "    if cm is None:",
    "        continue",
    "    ds = rel.get('downstream', {})",
    "    ds_name = f\"{ds.get('platform', '?')}.{ds.get('table', '?')}\"",
    "    print(f\"\\n═══ {ds_name} 的列级血缘 ({len(cm)} 条) ═══\")",
    "    for m in cm[:6]:",
    "        print(f\"  {m['upstream_column']:20s} -> {m['downstream_column']:20s}  ({m['transformation']})\")",
    "    if len(cm) > 6:",
    "        print(f\"  ... (还有 {len(cm)-6} 条)\")",
]))

# ── Cell 9: Code query GMS fineGrainedLineages ────────────────────────
cells.append(_code([
    "# ── 从 DataHub GMS 查询 upstreamLineage（含 fineGrainedLineages）──",
    "r = requests.get(f\"{GMS}/aspects/{encoded}?aspect=upstreamLineage&version=0\",",
    "                 auth=(\"datahub\", \"datahub\"), timeout=10)",
    "if r.status_code == 200:",
    "    data = r.json()",
    "    aspect = data.get(\"aspect\", {}).get(\"com.linkedin.dataset.UpstreamLineage\", {})",
    "    upstreams = aspect.get(\"upstreams\", [])",
    "    print(f\"表级上游: {len(upstreams)} 条\")",
    "    for up in upstreams[:3]:",
    "        ds_urn = up.get('dataset', '?')",
    "        ds_name = ds_urn.split(',')[-1].rstrip(')') if ',' in ds_urn else ds_urn",
    "        print(f\"  <- {ds_name}  (type={up.get('type')})\")",
    "",
    "    fgl = aspect.get(\"fineGrainedLineages\", [])",
    "    print(f\"\\n列级血缘 (fineGrainedLineages): {len(fgl)} 条\")",
    "    for f in fgl[:5]:",
    "        d = f['downstreams'][0].split(',')[-1].rstrip(')') if f.get('downstreams') else '?'",
    "        u = f['upstreams'][0].split(',')[-1].rstrip(')') if f.get('upstreams') else '?'",
    "        op = f.get('transformOperation', '')",
    "        print(f\"  {d} <- {u}  op={op}\")",
    "else:",
    "    print(\"GMS upstreamLineage 不可用:\", r.status_code)",
]))

# ── Cell 10: Markdown Step 3 ───────────────────────────────────────────
cells.append(_markdown([
    "## 步骤 3：上下文构建器 —— 从 GMS 真实查询",
    "",
    "**关键设计决策：用真实血缘，不用模拟数据。**",
    "",
    "`context_builder.build_context(question)` 做 3 件事：",
    "",
    "1. **查 4 张 DWA 宽表**的 schema（从 Parquet 读取字段名和类型）",
    "2. **按问题关键词计算相关性**，选取 top-K 表（命中 business_terms +2，cn_name +1）",
    "3. **从 DataHub GMS 查血缘**（upstreamLineage + fineGrainedLineages）+ 词典（glossaryTerms）",
    "",
    "GMS 不可达时直接抛 `RuntimeError`，**不退回 lineage_recipe.yaml**。",
    "原因是：教学演示的核心价值就是验证「血缘从 GMS 来」这条通路。",
    "",
    "下面调用 `build_context(\"各矿井精煤灰分排名\")` 看看返回上下文的结构。",
]))

# ── Cell 11: Code build_context demo ──────────────────────────────────
cells.append(_code([
    "# ── build_context 演示 ──",
    "from dg_nl2sql.context_builder import build_context",
    "",
    "ctx = build_context(\"各矿井精煤灰分排名\")",
    "print(f\"\\U0001f4e1 上下文来源: {ctx['source']}\")",
    "print(f\"\\U0001f4ca 相关表: {len(ctx['tables'])} 张\")",
    "print(f\"\\U0001f517 血缘边: {len(ctx['lineage_edges'])} 条\")",
    "print(f\"\\U0001f4d6 词典条: {len(ctx['glossary'])} 条\")",
    "",
    "# 展示每张表的相关性",
    "print(\"\\n── 相关表详情 ──\")",
    "for t in ctx['tables']:",
    "    print(f\"  {t['platform']}.{t['table']:25s} relevance={t['relevance']:4s}  cols={len(t['columns']):2d}  rows={t.get('row_count', '?'):<6}\")",
    "    # 展示前 4 个字段",
    "    for c in t['columns'][:4]:",
    "        cn = c.get('cn_name', '')",
    "        terms = ','.join(c.get('business_terms', [])[:3]) if c.get('business_terms') else ''",
    "        print(f\"    {c['name']:20s} {c['type']:12s} {cn}  [{terms}]\")",
]))

# ── Cell 12: Code display lineage edges ───────────────────────────────
cells.append(_code([
    "# ── 展示血缘边和列级映射 ──",
    "print(f\"血缘边共 {len(ctx['lineage_edges'])} 条:\\n\")",
    "for i, edge in enumerate(ctx['lineage_edges']):",
    "    print(f\"  [{i+1}] {edge['downstream']:30s} <- {edge['upstream']:25s} (type={edge['type']})\")",
    "    cm = edge.get('column_mappings', [])",
    "    if cm:",
    "        for m in cm[:4]:",
    "            print(f\"      \\U0001f4cb {m['downstream_col']:20s} <- {m['upstream_col']:20s}  transform={m['transform']}\")",
    "        if len(cm) > 4:",
    "            print(f\"      ... (还有 {len(cm)-4} 条)\")",
    "",
    "# 展示 glossary 条目",
    "print(f\"\\n词典条目共 {len(ctx['glossary'])} 条 (前 6 条):\")",
    "for g in ctx['glossary'][:6]:",
    "    print(f\"  {g['term']:30s} | {g['table']:20s}.{g['column']:20s} | cn={g['cn_name']}\")",
]))

# ── Cell 13: Markdown Step 4 ───────────────────────────────────────────
cells.append(_markdown([
    "## 步骤 4：NL2SQL 引擎 —— 端到端智能问数",
    "",
    "`NL2SQLEngine.ask(question)` 执行完整流程：",
    "",
    "1. **`build_context(question)`** 构建上下文（血缘 + schema + 词典）",
    "2. **构造 prompt**：system prompt（SQL 规则）+ user message（上下文 JSON + 问题）",
    "3. **LLM 生成 SQL**：调用 MiniMax-M2.7-highspeed，返回候选 SQL",
    "4. **安全校验**：只允许 SELECT，禁止 INSERT/UPDATE/DELETE/DROP 等",
    "5. **表名替换**：把逻辑表名替换为 DuckDB `read_parquet('...')` 调用",
    "6. **DuckDB 执行**：在内存中执行 SQL，获取结果",
    "7. **执行失败重试**：最多 1 次，把错误回传 LLM 修正",
    "8. **血缘解释**：从 SQL 涉及的表名反查血缘边，生成中文溯源说明",
    "",
    "注意：第一步会调用 LLM，需要网络连接和 API Key（已内置在 llm_client.py 中）。",
    "如果 LLM 不可用，下面的 cell 会报错，可以跳过。",
]))

# ── Cell 14: Code NL2SQL engine demo ─────────────────────────────────
cells.append(_code([
    "# ── NL2SQL 引擎演示 ──",
    "from dg_nl2sql.engine import NL2SQLEngine",
    "",
    "engine = NL2SQLEngine()",
    "result = engine.ask(\"各矿井精煤灰分排名\")",
    "",
    "print(f\"\"\"\\U0001f4ac 问题: {result['question']}",
    "\\U0001f4b1 SQL ({'\\U00002705 成功' if result['success'] else '\\U0000274c 失败'}):",
    "{result['sql']}",
    "\"\"\")",
    "",
    "if result['success']:",
    "    print(f\"\\U0001f4ca 结果 ({result['row_count']} 行):\")",
    "    if result.get('result'):",
    "        from dg_nl2sql.engine import format_result_table",
    "        print(format_result_table(result['result']))",
    "",
    "print(f\"\\n\\U0001f517 血缘解释:\")",
    "for line in result.get('lineage_explanation', []):",
    "    print(f\"  {line}\")",
]))

# ── Cell 15: Code more questions ──────────────────────────────────────
cells.append(_code([
    "# ── 再演示 2-3 个问题 ──",
    "for q in [\"告警最多的 10 个传感器\", \"各煤种的样品数量和平均热值\"]:",
    "    print(f\"{'='*60}\")",
    "    print(f\"\\U0001f4ac 问题: {q}\")",
    "    r = engine.ask(q)",
    "    status = \"\\U00002705\" if r['success'] else \"\\U0000274c\"",
    "    print(f\"  {status} SQL: {r['sql'][:120]}...\")",
    "    print(f\"  \\U0001f4ca 结果: {r['row_count']} 行\")",
    "    if r['success'] and r.get('result'):",
    "        from dg_nl2sql.engine import format_result_table",
    "        print(f\"  {format_result_table(r['result'])[:300]}\")",
    "    print(f\"  \\U0001f517 血缘:\")",
    "    for line in r.get('lineage_explanation', [])[:3]:",
    "        print(f\"    {line}\")",
    "    print()",
]))

# ── Cell 16: Markdown Step 5 ───────────────────────────────────────────
cells.append(_markdown([
    "## 步骤 5：测试验证 —— 8 个场景全覆盖",
    "",
    "`scripts/nl2sql_demo.py` 中定义了 8 个测试问题，覆盖以下场景：",
    "",
    "| # | 场景 | 问题 | 难度 |",
    "|---|------|------|------|",
    "| 1 | 单表聚合 | 各煤种的样品数量和平均热值 | \\U0001f7e2 基础 |",
    "| 2 | 业务术语消解 | 各矿井精煤的灰分排名 | \\U0001f7e1 关键 |",
    "| 3 | Top-N 排序 | 告警次数最多的 10 个传感器 | \\U0001f7e2 基础 |",
    "| 4 | 时间筛选 | 2022 年 1 月的煤质数据 | \\U0001f7e2 基础 |",
    "| 5 | 聚合统计 | 各矿井的平均灰分 | \\U0001f7e2 基础 |",
    "| 6 | 跨系统歧义 | 销售订单对应的煤质化验数据 | \\U0001f534 难点 |",
    "| 7 | 简单计数 | 总共有多少条销售记录 | \\U0001f7e2 基础 |",
    "| 8 | 多指标对比 | 各矿井的销售额和产量对比 | \\U0001f7e1 进深 |",
    "",
    "其中第 6 题（跨系统歧义）是设计亮点：",
    "sap_erp.vbak（销售）和 lims.samples（煤质）没有字面共享列，",
    "LLM 应正确返回「ERROR: 无法跨系统 JOIN」，视为 PASS —— 说明 AI 知道自己的边界。",
    "",
    "下面快速验证前 3 题（全部执行太慢，完整测试用 `uv run python scripts/nl2sql_demo.py`）。",
]))

# ── Cell 17: Code batch test ─────────────────────────────────────────
cells.append(_code([
    "# ── 批量测试（前 3 题快速验证）──",
    "questions = [",
    "    \"各煤种的样品数量和平均热值\",",
    "    \"各矿井精煤的灰分排名\",",
    "    \"告警次数最多的 10 个传感器\",",
    "]",
    "",
    "passed = 0",
    "for i, q in enumerate(questions, 1):",
    "    print(f\"[{i}/{len(questions)}] {q}\")",
    "    r = engine.ask(q)",
    "    status = \"\\U00002705 PASS\" if r['success'] else \"\\U0000274c FAIL\"",
    "    print(f\"  {status}  rows={r['row_count']}  sql={r['sql'][:100]}...\")",
    "    if r['success']:",
    "        passed += 1",
    "    print()",
    "",
    "print(f\"通过 {passed}/{len(questions)}\")",
]))

# ── Cell 18: Markdown key design decisions ────────────────────────────
cells.append(_markdown([
    "## 关键设计决策回顾",
    "",
    "### 1. 真实血缘 vs 模拟血缘",
    "",
    "本模块所有血缘数据从 DataHub GMS 的 REST API 真实查询",
    "（`/aspects/{urn}?aspect=upstreamLineage`），",
    "不使用 `lineage_recipe.yaml` 的模拟值。",
    "GMS 不可达时直接抛异常，不退化。",
    "",
    "这样做的原因：教学的核心价值是「看得见真实的血缘图是怎么喂给 AI 的」。",
    "",
    "### 2. 列级血缘模型",
    "",
    "DataHub 的列级血缘（fineGrainedLineages）嵌套在 `upstreamLineage` aspect 内，",
    "通过 `transformOperation` 字段记录转换逻辑（如 `AVG(AD)`、`COUNT(*)`）。",
    "SDK 写入时用 `FineGrainedLineageClass`，REST 查询时从 `upstreamLineage.fineGrainedLineages` 取。",
    "",
    "### 3. 安全校验",
    "",
    "引擎使用白名单策略：只允许 `SELECT` 语句，拒绝 `INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE` 等。",
    "校验在 SQL 替换和执行之前，防止 LLM 误生成写操作。",
    "",
    "### 4. SQL 修正",
    "",
    "SQL 执行失败时，引擎把错误信息回传 LLM，让 LLM 修正自己的输出。最多修正 1 次，",
    "避免无限循环。修正后的 SQL 同样经过安全校验和表名替换。",
]))

# ── Cell 19: Markdown summary ─────────────────────────────────────────
cells.append(_markdown([
    "## 总结",
    "",
    "本模块展示了如何把 DataHub 血缘图从「可视化资产」升级为「AI 可消费的语义图谱」。",
    "",
    "### 核心流程",
    "",
    "```",
    "用户问题 ──► build_context() ──► GMS 血缘/词典/ schema ──►",
    "                      LLM 生成 SQL ──► DuckDB 执行 ──► 结果 + 血缘解释",
    "```",
    "",
    "### 三个关键收益",
    "",
    "1. **业务用户零门槛**：不会 SQL 也能查数，用自然语言直接问",
    "2. **AI 有据可依**：血缘 + 词典提供了 LLM 所需的全部业务上下文",
    "3. **结果可溯源**：每条查询结果都附带血缘解释，知道数据从哪里来、怎么加工的",
    "",
    "### 后续改进方向",
    "",
    "- **列级血缘全覆盖**：当前仅 3 张 DWA 表有 fineGrainedLineages，扩展到所有表",
    "- **多轮对话**：支持追问、WHERE 条件修改、结果排序切换",
    "- **查询审计**：记录每条 SQL 执行历史，支持回放和异常检测",
    "- **查询结果可视化**：对于时间序列数据自动选择折线图、饼图",
    "",
    "### 相关知识入口",
    "",
    "| 模块 | 内容 |",
    "|------|------|",
    "| 模块九 | OpenLineage 自动血缘采集（auto 通道） |",
    "| 模块八 | 生产级元数据接入（manual 通道） |",
    "| 模块十二 | DWA 宽表构建与 DuckDB OLAP |",
    "| 背景知识 | `docs/Background.md` 煤炭业务术语 |",
    "| 技术架构 | `docs/Design.md` NL2SQL 选型理由 |",
]))

# ── Assemble Notebook ─────────────────────────────────────────────────
nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out_path = "notebook/module13_nl2sql.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\\u2705 已生成 {out_path}")
print(f"   cells: {len(cells)} ({sum(1 for c in cells if c['cell_type']=='markdown')} markdown + {sum(1 for c in cells if c['cell_type']=='code')} code)")
