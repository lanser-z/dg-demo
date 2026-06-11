"""One-shot generator: build the refactored step1.ipynb + datahub_setup.ipynb.

Run from repo root:
    PYTHONPATH=src uv run python scripts/_build_notebooks.py

This script is the source of truth for the new notebook structure. After
running, the resulting .ipynb files are committed to git and the script
itself can be removed (or kept as reference).

Design rationale (see openspec/changes/improve-step1-notebook-onboarding/):
  - step1.ipynb: teaching notebook (3 步 learning rhythm + 痛点 story +
    业务影响 annotations + DataHub UI walkthrough)
  - datahub_setup.ipynb: dev-only DataHub ingestion scripts (extracted
    from old section 7 — keep dev API calls out of the teaching flow)
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/home/szs/Playground/dg-demo")
NB_DIR = REPO / "notebook"


def md(*lines: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [l + "\n" for l in lines[:-1]] + [lines[-1]],
    }


def code(*lines: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [l + "\n" for l in lines[:-1]] + [lines[-1]],
    }


# ---------------------------------------------------------------------------
# step1.ipynb — refactored teaching notebook
# ---------------------------------------------------------------------------

STEP1 = [
    md(
        "# Step 1：模块一 — 数据资产可视化",
        "",
        "## 痛点故事",
        "",
        "> **没有可视化的世界**（想象一下）：",
        "> 小白接到任务：「把 5 个系统的数据接进来」。他打开 SAP 看一眼，再打开 PI 看一眼，",
        "> 又跑去 LIMS 找表格，OA 还要问同事要权限……一周过去了，他还在「找数据」阶段，",
        "> 谁也不知道总共有多少表、谁负责、质量如何。",
        "",
        "> **有可视化的世界**（本模块目标）：",
        "> 一个 DataHub 搜索框，全公司 13 张表、5 个系统、记录数 / 存储 / Owner 全部一目了然，",
        "> 质量告警用红黄绿色卡显示，每条告警都翻译成「一年花多少钱 / 有什么风险」。",
        "> 小白第一天就能回答老板：「我们有 X 张表，Y 类问题，年度成本 Z 万元」。",
        "",
        "## 目录",
        "",
        "1. [3 步学习节奏](#3-步学习节奏)",
        "2. [步骤 1：资产目录与存储分布](#步骤-1资产目录与存储分布)",
        "3. [步骤 2：质量评分卡 + 业务影响翻译](#步骤-2质量评分卡--业务影响翻译)",
        "4. [步骤 3：安全分级](#步骤-3安全分级)",
        "5. [附加：DataHub UI 是什么、怎么用](#附加datahub-ui-是什么怎么用)",
    ),

    code(
        "# ── Setup ─────────────────────────────────────────────────────────────",
        "# 把 src/ 加入 Python 路径，以便 import dg_education",
        "import os, sys",
        "sys.path.insert(0, os.path.join(os.path.dirname(os.getcwd()), 'src'))",
        "",
        "from dg_education import (",
        "    build_asset_catalog, SYSTEM_INFO, all_datasets,",
        "    check_sap_quality, check_pi_quality, check_lims_quality, check_oa_quality,",
        "    calc_quality_score, DIMENSION_WEIGHTS,",
        "    plot_storage_distribution, plot_quality_scorecard,",
        "    plot_security_levels, plot_business_impact,",
        "    estimate_annual_cost, format_business_impact_line, COST_TABLE,",
        ")",
        "",
        "# 历史数据根目录（与原 notebook 一致）",
        "DATA_ROOT = os.path.join(os.path.dirname(os.getcwd()), 'data', 'historical')",
        "print(f\"DATA_ROOT = {DATA_ROOT}\")",
        "print(f\"已加载 {len(SYSTEM_INFO)} 个系统，{len(all_datasets())} 张表\")",
    ),

    md(
        "## 3 步学习节奏",
        "",
        "本模块分 3 步走完：",
        "",
        "| 步骤 | 目标 | 核心概念 |",
        "|------|------|----------|",
        "| 步骤 1 | 看见「有什么」 | 资产目录、存储分布 |",
        "| 步骤 2 | 看清「好不好」 | 4 维质量评分卡 + 业务影响翻译 |",
        "| 步骤 3 | 看懂「重不重要」 | 核心/重要/一般 三级安全分级 |",
        "",
        "走完这 3 步，你就掌握了「数据治理第一步」：**让数据可见、可评、可控**。",
    ),

    md(
        "## 步骤 1：资产目录与存储分布",
        "",
        "**为什么从这里开始？** 治理的第一性原理：你得先知道自己有什么，才能谈得上治理。",
        "",
        "下面用 `build_asset_catalog()` 扫描 `data/historical/` 下的 Parquet 文件，自动生成资产目录。",
        "（核心代码在 `src/dg_education/catalog.py`，小白不用关心怎么扫文件，只要看结果即可。）",
    ),

    code(
        "# 扫描 5 个系统的 Parquet，生成资产目录",
        "df_catalog = build_asset_catalog(DATA_ROOT)",
        "display_cols = ['系统', '表/数据集', '记录数', '存储大小(MB)', 'Owner', '安全级别', '说明']",
        "df_view = df_catalog[display_cols].copy()",
        "df_view['记录数'] = df_view['记录数'].apply(lambda x: f\"{x:,}\")",
        "print(\"=== 资产目录（共 {} 张表）===\".format(len(df_catalog)))",
        "df_view",
    ),

    code(
        "# 可视化：饼图（存储分布）+ 柱状图（记录数）",
        "fig = plot_storage_distribution(df_catalog)",
        "fig  # 在 notebook 中渲染（也可 fig.savefig('screenshots/storage.png', bbox_inches='tight')）",
    ),

    md(
        "## 步骤 2：质量评分卡 + 业务影响翻译",
        "",
        "光有「有什么」还不够，得知道数据「好不好」。我们用 4 个维度评估每个系统的数据质量：",
        "",
        "- **完整性** = 1 - 空值比例（没有 null/空字段吗？）",
        "- **一致性** = 跨系统/跨表数据是否一致（订单表与行项目能对得上吗？）",
        "- **准确性** = 数据是否落在业务合理区间（灰分 10-50% 是原煤合理区间）",
        "- **唯一性** = 1 - 重复行比例（同一订单录了 2 次吗？）",
        "",
        "核心代码在 `src/dg_education/quality.py` —— 小白不用关心规则怎么写，",
        "只要看「评分卡」和「业务影响」就行。",
    ),

    code(
        "# 加载 2023 年样本数据（避免加载全量数据卡顿）",
        "import pandas as pd",
        "kna1  = pd.read_parquet(f'{DATA_ROOT}/sap_erp/kna1.parquet')",
        "vbak  = pd.read_parquet(f'{DATA_ROOT}/sap_erp/vbak_year=2023.parquet')",
        "vbap  = pd.read_parquet(f'{DATA_ROOT}/sap_erp/vbap_year=2023.parquet')",
        "pi    = pd.read_parquet(f'{DATA_ROOT}/pi_system/tags_year=2023_month=01.parquet')",
        "lims  = pd.read_parquet(f'{DATA_ROOT}/lims/samples_year=2023.parquet')",
        "oa    = pd.read_parquet(f'{DATA_ROOT}/oa/doc_flow_year=2023.parquet')",
        "",
        "# 跑 4 个系统的质量检测（核心代码下沉到 src/dg_education/quality.py）",
        "sap_q  = check_sap_quality(vbak, vbap, kna1)",
        "pi_q   = check_pi_quality(pi)",
        "lims_q = check_lims_quality(lims)",
        "oa_q   = check_oa_quality(oa)",
        "",
        "# 把检测结果反推成 4 维评分（简化：每个质量比例 ×10 从 100 减下去）",
        "def _to_score(null_pct, dup_pct, outlier_pct, link_pct):",
        "    return {",
        "        '完整性': round(max(0, 100 - null_pct * 10), 1),",
        "        '唯一性': round(max(0, 100 - dup_pct * 10), 1),",
        "        '准确性': round(max(0, 100 - outlier_pct * 5), 1),",
        "        '一致性': round(max(0, 100 - link_pct * 5), 1),",
        "    }",
        "",
        "sys_scores = {",
        "    'SAP-ERP':  _to_score(",
        "        null_pct=(sap_q.get('null_NETWR', 0) + sap_q.get('null_ERNAM', 0)) / 2,",
        "        dup_pct=sap_q['dup_vbak'],",
        "        outlier_pct=0,",
        "        link_pct=sap_q['invalid_link_pct'],",
        "    ),",
        "    'PI-System': _to_score(",
        "        null_pct=pi_q['missing_pct'],",
        "        dup_pct=0,",
        "        outlier_pct=pi_q.get('wagas_danger_pct', 0),",
        "        link_pct=pi_q.get('wagas_anomaly_pct', 0),",
        "    ),",
        "    'LIMS':     _to_score(",
        "        null_pct=lims_q.get('null_AD', 0),",
        "        dup_pct=lims_q['dup_pct'],",
        "        outlier_pct=lims_q['ad_outlier_pct'],",
        "        link_pct=0,",
        "    ),",
        "    'OA':       _to_score(",
        "        null_pct=oa_q.get('null_FLOW_TYPE', 0),",
        "        dup_pct=oa_q['dup_pct'],",
        "        outlier_pct=0,",
        "        link_pct=0,",
        "    ),",
        "}",
        "df_scores = calc_quality_score(sys_scores)",
        "print(\"=== 4 维质量评分卡 ===\")",
        "df_scores",
    ),

    code(
        "# 可视化：4 维分组柱状图 + 综合得分排名",
        "fig = plot_quality_scorecard(df_scores)",
        "fig",
    ),

    md(
        "### 业务影响：把告警翻译成「白话 + 钱」",
        "",
        "评分卡上那些 0.x% 的「空值率」「重复率」对小白来说太抽象。",
        "下面用「行数 × 注入率 × 单位成本」把每条告警翻译成「**一年大概花多少钱 / 有什么风险**」。",
        "",
        "> **教学参考值**（重要）：单位成本是行业公开参考值（煤价 800 元/吨、工时 50 元/h 等），",
        "> 不是 A 公司真实业务数字。生产环境请用真实数据替换 `COST_TABLE`（`src/dg_education/business_impact.py`）。",
    ),

    code(
        "# 把每条主告警翻译成业务影响（白话 + 钱）",
        "alert_rows = {",
        "    'SAP.dup_vbak':         len(vbak),",
        "    'SAP.invalid_link_pct': len(vbap),",
        "    'PI.wagas_danger_pct':  len(pi),",
        "    'PI.wagas_anomaly_pct': len(pi),",
        "    'LIMS.ad_outlier_pct':  len(lims),",
        "    'LIMS.dup_pct':         len(lims),",
        "    'OA.dup_pct':           len(oa),",
        "}",
        "alert_rates = {",
        "    'SAP.dup_vbak':         sap_q['dup_vbak'],",
        "    'SAP.invalid_link_pct': sap_q['invalid_link_pct'],",
        "    'PI.wagas_danger_pct':  pi_q.get('wagas_danger_pct', 0),",
        "    'PI.wagas_anomaly_pct': pi_q.get('wagas_anomaly_pct', 0),",
        "    'LIMS.ad_outlier_pct':  lims_q['ad_outlier_pct'],",
        "    'LIMS.dup_pct':         lims_q['dup_pct'],",
        "    'OA.dup_pct':           oa_q['dup_pct'],",
        "}",
        "",
        "for key, rows in alert_rows.items():",
        "    print(format_business_impact_line(key, rows, alert_rates[key]))",
        "    print()",
    ),

    code(
        "# 可视化：业务影响条形图（log scale）",
        "impacts = [estimate_annual_cost(k, alert_rows[k], alert_rates[k]) for k in alert_rows]",
        "fig = plot_business_impact(impacts)",
        "fig",
    ),

    md(
        "## 步骤 3：安全分级",
        "",
        "数据治理的最后一步：按「一旦泄露影响多大」给资产定级，决定谁能看、谁能改。",
        "",
        "| 级别 | 定义 | 本项目数据集 |",
        "|------|------|---------------|",
        "| 🔴 核心资产 | 一旦泄露影响安全生产 | PI-System tags、SCADA equipment_status |",
        "| 🟠 重要资产 | 影响经营分析准确性 | SAP KNA1/VBAK/VBAP、LIMS samples |",
        "| 🟡 一般资产 | 内部流程数据 | OA doc_flow/contract/meeting |",
    ),

    code(
        "# 安全分级可视化",
        "import pandas as pd",
        "df_sec = pd.DataFrame({",
        "    '系统': ['PI-System', 'SAP-ERP', 'LIMS', 'OA'],",
        "    '高度': [100, 95, 93, 90],",
        "    '标签': ['核心资产(加密+审计)', '重要资产(访问控制)', '重要资产(访问控制)', '一般资产(基础管控)'],",
        "    '安全级别': ['核心资产', '重要资产', '重要资产', '一般资产'],",
        "})",
        "fig = plot_security_levels(df_sec)",
        "fig",
    ),

    md(
        "## 附加：DataHub UI 是什么、怎么用",
        "",
        "到这里，小白在 notebook 里已经把数据「看全、看清楚、看分级」了。",
        "那 DataHub UI（http://localhost:29002 ）是干嘛的？",
        "",
        "**一句话**：DataHub UI 是「治理结果的可视化呈现」，notebook 是「治理过程的可视化讲解」。两者对同一份数据，给不同的人看：",
        "",
        "- **notebook**（本文件）：给小白学习用，重在「为什么、怎么算、有什么业务影响」",
        "- **DataHub UI**：给业务方/数据分析师日常用，重在「搜资产、查血缘、订阅告警」",
        "",
        "### 截图演示",
        "",
        "下面 3 张截图取自我们部署好的 DataHub 实例，展示新人最常用的 3 个界面。",
    ),

    md(
        "### 截图 1：搜索首页（也是落地页）",
        "",
        "打开 DataHub，第一眼看到的就是搜索页。左上角可以按 **Type / Platform / Owner / Tag** 过滤，",
        "右侧是「选中资产的 Summary / Documentation / Owners / Tags / Terms」面板。",
        "",
        "![DataHub 搜索首页](../screenshots/datahub_01_home.png)",
    ),

    md(
        "### 截图 2：搜索「lims」",
        "",
        "在搜索框输入 `lims`，立刻看到煤质化验样品 dataset（属于 LIMS 平台、重要资产、coal_quality_team 负责）。",
        "点一下进入详情页，看下一步。",
        "",
        "![搜索 lims 结果](../screenshots/datahub_02_search_lims.png)",
    ),

    md(
        "### 截图 3：dataset 详情页（Columns / Documentation / Lineage / Quality）",
        "",
        "详情页的顶部 9 个 tab 是 DataHub 的核心：",
        "",
        "- **Columns**：字段说明、数据类型、NULL 统计",
        "- **Documentation**：富文本描述（谁能用、什么场景）",
        "- **Lineage**：血缘（这张表的上游是谁、下游是谁）",
        "- **Properties**：自定义属性（保留天数、脱敏规则）",
        "- **Quality**：数据质量趋势（每天/每周的评分）",
        "- **Governance / Incidents**：治理事件、事件工单",
        "",
        "![LIMS samples 详情页](../screenshots/datahub_03_lims_samples.png)",
    ),

    md(
        "### 怎么把这些数据放进 DataHub？",
        "",
        "截图里的数据不是天上掉下来的 —— 是用 `scripts/direct_es_bulk.py` 把 `data/historical/` 的元数据",
        "（中文字段名、Owner、安全级别）写入 DataHub 的 OpenSearch 索引实现的。",
        "",
        "具体的上报脚本和验证脚本（OpenSearch delete-by-query、GraphQL browse/search）",
        "已经移到独立的 `notebook/datahub_setup.ipynb`，避免教学时被技术细节打断。",
        "",
        "**下一步**：",
        "- 想了解「数据怎么进 DataHub」 → 打开 [`datahub_setup.ipynb`](./datahub_setup.ipynb)",
        "- 想直接看本模块的「教学版」 → 继续往下读模块一总结",
    ),

    md(
        "## 模块一总结",
        "",
        "走完 3 步学习节奏，我们已经达成：",
        "",
        "| 步骤 | 达成 | 关键产出 |",
        "|------|------|----------|",
        "| ✅ 步骤 1 资产目录 | 5 个系统 / 13 张表 / 中文说明 / Owner / 安全级别 一目了然 | `build_asset_catalog()` + `plot_storage_distribution()` |",
        "| ✅ 步骤 2 质量评分 + 业务影响 | 4 维评分卡 + 每条告警翻译成「白话 + 元/年」 | `check_*_quality()` + `plot_quality_scorecard()` + `format_business_impact_line()` |",
        "| ✅ 步骤 3 安全分级 | 核心/重要/一般 三级分类 | `plot_security_levels()` |",
        "",
        "### 关键发现",
        "",
        "1. **SAP-ERP** 主要问题为 VBAP 关联失效（孤儿行项目）—— 一年可能影响库存盘点",
        "2. **PI-System** 主要问题为 WAGAS 瓦斯超 1% 告警 —— 单起可能引发停产 + 调查",
        "3. **LIMS** 主要问题为灰分超出合理区间 —— 影响煤价定价（800 元/吨）",
        "4. **OA** 主要问题为重复流程记录 —— 量大但单条成本低",
        "",
        "### 下一步",
        "",
        "模块一展示了「看得见」的能力；下一步进入 **模块二：数据质量检测与根因定位**，",
        "对以上告警做自动化监控、告警触发、血缘链路分析。",
    ),
]


# ---------------------------------------------------------------------------
# datahub_setup.ipynb — extracted dev scripts (section 7)
# ---------------------------------------------------------------------------

DATAHUB_SETUP = [
    md(
        "# DataHub 接入与验证（开发脚本）",
        "",
        "> **使用对象**：要修改 DataHub 接入流程 / 验证数据上报的开发者",
        "> **不推荐**：给「小白」学习用 —— 这是 OpenSearch / GraphQL 的硬核 API，",
        "> 不在「数据治理入门」必修路径上。教学路径请回到 [`step1.ipynb`](./step1.ipynb)。",
        "",
        "## 这个 notebook 做什么",
        "",
        "把 5 个系统的元数据从本地 `data/historical/` 通过 `scripts/direct_es_bulk.py` 写入",
        "DataHub 后端的 OpenSearch 索引，并验证：",
        "",
        "1. 各服务健康状态（GMS / OpenSearch / Neo4j）",
        "2. 清除 OpenSearch 中已有的资产（模拟「重新上报」）",
        "3. 调用 `direct_es_bulk.py` 重新写入",
        "4. 验证：OpenSearch `_count` / `_search`",
        "5. 验证：DataHub Browse GraphQL",
        "6. 验证：DataHub Search GraphQL",
        "",
        "**前置条件**：DataHub 已启动（`docs/Deps.md` 的 quickstart 步骤），且 `http://localhost:29002` 可达。",
    ),

    md(
        "## 1. 服务状态确认",
        "",
        "在重新上报前，先确认 DataHub 各服务正常运行：",
    ),

    code(
        "import requests",
        "",
        "GMS_URL = \"http://localhost:28080\"",
        "ES_URL  = \"http://localhost:29200\"",
        "AUTH    = (\"datahub\", \"datahub\")",
        "",
        "def check_service(url, name):",
        "    try:",
        "        r = requests.get(url, timeout=5)",
        "        return r.status_code < 500",
        "    except Exception:",
        "        return False",
        "",
        "print(\"=== DataHub 服务状态 ===\")",
        "print(f\"  GMS API (localhost:28080):    {'OK 可达' if check_service(f'{GMS_URL}/health', 'GMS') else 'X 不可达'}\")",
        "print(f\"  OpenSearch (localhost:29200): {'OK 可达' if check_service(f'{ES_URL}/_cluster/health', 'ES') else 'X 不可达'}\")",
        "print()",
        "print(\"各服务端口对照：\")",
        "print(\"  前端 Web UI:  http://localhost:29002\")",
        "print(\"  GMS API:     http://localhost:28080\")",
        "print(\"  Neo4j:       http://localhost:27474\")",
        "print(\"  OpenSearch:  http://localhost:29200\")",
    ),

    md(
        "## 2. 清除已有数据",
        "",
        "先删除 OpenSearch 中已存在的资产数据，模拟「重新上报」场景。",
        "**警告**：这是 `delete_by_query` —— 会清掉符合 URN 模式的所有资产，请确认不要影响生产数据。",
    ),

    code(
        "def es_count(index):",
        "    r = requests.get(f\"{ES_URL}/{index}/_count\", timeout=10)",
        "    return r.json().get('count', 0)",
        "",
        "print(\"=== 删除前 ===\")",
        "cnt_before = es_count('datasetindex_v2')",
        "print(f\"datasetindex_v2 文档数: {cnt_before}\")",
        "",
        "delete_by_query = {",
        "    \"query\": {",
        "        \"bool\": {",
        "            \"should\": [",
        "                {\"wildcard\": {\"urn\": \"urn:li:dataset:(urn:li:dataPlatform:lims,*\"}},",
        "                {\"wildcard\": {\"urn\": \"urn:li:dataset:(urn:li:dataPlatform:sap_erp,*\"}},",
        "                {\"wildcard\": {\"urn\": \"urn:li:dataset:(urn:li:dataPlatform:pi_system,*\"}},",
        "                {\"wildcard\": {\"urn\": \"urn:li:dataset:(urn:li:dataPlatform:oa,*\"}},",
        "                {\"wildcard\": {\"urn\": \"urn:li:dataset:(urn:li:dataPlatform:scada,*\"}},",
        "            ],",
        "            \"minimum_should_match\": 1",
        "        }",
        "    }",
        "}",
        "r = requests.post(",
        "    f\"{ES_URL}/datasetindex_v2/_delete_by_query\",",
        "    json=delete_by_query,",
        "    headers={\"Content-Type\": \"application/json\"},",
        "    timeout=30,",
        ")",
        "result = r.json()",
        "deleted = result.get('deleted', 0)",
        "print(f\"已删除 {deleted} 条文档\")",
        "",
        "print(\"=== 删除后 ===\")",
        "cnt_after = es_count('datasetindex_v2')",
        "print(f\"datasetindex_v2 文档数: {cnt_after}\")",
    ),

    md(
        "## 3. 重新导入数据",
        "",
        "调用 `scripts/direct_es_bulk.py` 将资产重新写入 OpenSearch。",
        "这个脚本读取 `data/historical/` 下的元数据 + `src/dg_platform/datahub_client.py` 的映射规则，",
        "生成符合 DataHub 期望的 MCE 事件 JSON，再通过 OpenSearch `_bulk` 端点直接写入（绕开 GMS）。",
    ),

    code(
        "import subprocess, os",
        "",
        "WORK_DIR = \"/home/szs/Playground/dg-demo\"",
        "script_path = os.path.join(WORK_DIR, \"scripts\", \"direct_es_bulk.py\")",
        "print(f\"执行脚本: {script_path}\")",
        "print(\"输出:\")",
        "result = subprocess.run(",
        "    [\"uv\", \"run\", \"python\", script_path],",
        "    cwd=WORK_DIR,",
        "    capture_output=True,",
        "    text=True,",
        "    timeout=120,",
        ")",
        "print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)",
        "if result.stderr:",
        "    print(\"STDERR:\", result.stderr[-500:])",
        "print(f\"\\n返回码: {result.returncode}\")",
    ),

    md(
        "## 4. 验证：导入后数据",
        "",
        "通过 OpenSearch REST API 直接查询 dataset index，确认资产是否已录入。",
    ),

    code(
        "r = requests.get(f\"{ES_URL}/datasetindex_v2/_count\", timeout=10)",
        "d = r.json()",
        "total = d.get('count', 0)",
        "print(f\"OpenSearch datasetindex_v2 中资产数量: {total}\")",
        "print()",
        "",
        "# 按平台统计",
        "r2 = requests.get(f\"{ES_URL}/datasetindex_v2/_search?size=50&_source=platform,name,urn\", timeout=10)",
        "d2 = r2.json()",
        "",
        "platform_count = {}",
        "assets = []",
        "for h in d2.get('hits', {}).get('hits', []):",
        "    s = h['_source']",
        "    plat = s.get('platform', 'unknown')",
        "    platform_count[plat] = platform_count.get(plat, 0) + 1",
        "    assets.append({'platform': plat, 'name': s.get('name', ''), 'urn': s.get('urn', '')})",
        "",
        "print(\"=== 各平台资产统计 ===\")",
        "for plat, cnt in sorted(platform_count.items()):",
        "    print(f\"  {plat:15s}: {cnt} 张表\")",
        "print()",
        "print(\"=== 资产清单 ===\")",
        "for a in sorted(assets, key=lambda x: (x['platform'], x['name'])):",
        "    print(f\"  {a['platform']:15s} / {a['name']:20s}\")",
    ),

    md(
        "## 5. 验证：DataHub Browse 页面",
        "",
        "通过 GMS GraphQL API 查询 Browse 侧边栏，确认左侧导航能展示各平台。",
    ),

    code(
        "platforms = [\"lims\", \"sap_erp\", \"pi_system\", \"oa\"]",
        "print(\"=== DataHub Browse API 验证 ===\")",
        "for platform in platforms:",
        "    browse_q = {",
        "        \"query\": f'''",
        "        query BrowsePlatform {{",
        "            browse(input: {{ type: DATASET, path: [\"{platform}\"], start: 0, count: 10 }}) {{",
        "                total",
        "                groups {{ name count }}",
        "            }}",
        "        }}",
        "        '''",
        "    }",
        "    try:",
        "        r = requests.post(",
        "            f\"{GMS_URL}/api/graphql\",",
        "            json=browse_q,",
        "            auth=AUTH,",
        "            timeout=10,",
        "        )",
        "        d = r.json()",
        "        errors = d.get(\"errors\", [])",
        "        if errors:",
        "            print(f\"  {platform}: 查询失败 — {errors[0]['message'][:80]}\")",
        "            continue",
        "        browse = d.get(\"data\", {}).get(\"browse\", {})",
        "        total = browse.get(\"total\", 0)",
        "        groups = browse.get(\"groups\", [])",
        "        print(f\"  {platform}: {total} 张表\")",
        "        for g in groups:",
        "            print(f\"    └─ {g['name']}: {g['count']}\")",
        "    except Exception as e:",
        "        print(f\"  {platform}: 请求异常 — {e}\")",
    ),

    md(
        "## 6. 验证：搜索功能",
        "",
        "通过 GraphQL `searchAcrossEntities` 验证搜索是否正常工作：",
    ),

    code(
        "search_q = {",
        "    \"query\": '''",
        "    query SearchVerify {{",
        "        searchAcrossEntities(input: {{ query: \"*\", type: DATASET, start: 0, count: 20 }}) {{",
        "            total",
        "            searchResults {{",
        "                entity {{",
        "                    ... on Dataset {{ name platform {{ name }} }}",
        "                }}",
        "            }}",
        "        }}",
        "    }}",
        "    '''",
        "}",
        "try:",
        "    r = requests.post(f\"{GMS_URL}/api/graphql\", json=search_q, auth=AUTH, timeout=10)",
        "    d = r.json()",
        "    errors = d.get(\"errors\", [])",
        "    if errors:",
        "        print(f\"搜索失败: {errors[0]['message'][:100]}\")",
        "    else:",
        "        results = d.get(\"data\", {}).get(\"searchAcrossEntities\", {})",
        "        total = results.get(\"total\", 0)",
        "        items = results.get(\"searchResults\", [])",
        "        print(f\"=== 搜索结果: 共 {total} 条匹配 (显示前 {len(items)} 条) ===\")",
        "        for res in items:",
        "            ent = res.get(\"entity\", {})",
        "            print(f\"  {ent.get('platform',{}).get('name','?')}/{ent.get('name','?')}\")",
        "except Exception as e:",
        "    print(f\"搜索请求异常: {e}\")",
    ),

    md(
        "## 7. 结论",
        "",
        "本 notebook 演示了完整的数据资产上报流程：",
        "",
        "```",
        "1. 清除已有数据  →  OpenSearch DELETE by query",
        "2. 重新导入数据  →  scripts/direct_es_bulk.py",
        "3. 验证写入结果  →  OpenSearch _count + _search",
        "4. 验证Browse导航 →  GMS GraphQL browse API",
        "5. 验证搜索功能  →  GMS GraphQL searchAcrossEntities",
        "```",
        "",
        "**关键操作**：",
        "- 写入 API：`POST /_bulk` 直接 bulk 写入 OpenSearch（绕开 GMS，走 ingestion pipe）",
        "- 验证 API：`POST /datasetindex_v2/_search` 确认数据存在",
        "- Browse API：`POST /api/graphql` GraphQL browse 查询导航路径",
        "",
        "> 若需通过 GMS 正式上报（写入 MySQL + 同步 OpenSearch），应使用 `datahub` CLI 的 `ingest` 命令，",
        "> 或调用 `POST /operations?action=restoreIndices` 将 MySQL 数据同步到 OpenSearch。",
    ),
]


def _wrap(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12",
                "mimetype": "text/x-python",
                "codemirror_mode": {"name": "ipython", "version": 3},
                "pygments_lexer": "ipython3",
                "nbconvert_exporter": "python",
                "file_extension": ".py",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    NB_DIR.mkdir(parents=True, exist_ok=True)
    (NB_DIR / "step1.ipynb").write_text(
        json.dumps(_wrap(STEP1), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"wrote {NB_DIR / 'step1.ipynb'}  ({len(STEP1)} cells)")
    (NB_DIR / "datahub_setup.ipynb").write_text(
        json.dumps(_wrap(DATAHUB_SETUP), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"wrote {NB_DIR / 'datahub_setup.ipynb'}  ({len(DATAHUB_SETUP)} cells)")


if __name__ == "__main__":
    main()
