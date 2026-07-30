"""
context_builder — 从 DataHub GMS 真实查询血缘/schema/词典，构建 NL2SQL 上下文。

设计原则：
- 血缘（表级 + 列级）从 DataHub GMS REST `/aspects/{urn}?aspect=upstreamLineage` 真实读取
- 业务术语从 GMS REST `/aspects/{urn}?aspect=glossaryTerms` 真实读取
- schema 从 Parquet 文件 pyarrow 读取（GMS schemaMetadata 为空）
- GMS 不可用时：直接抛 RuntimeError，**不使用 lineage_recipe.yaml 退化**

URN 规范：
    dataset:   urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)
    schemaField: urn:li:schemaField:(urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD),{column})

Parquet 路径定位（按优先级）：
    1. data/lakehouse/dwa/**/{table}/*.parquet
    2. data/lakehouse/dwd/**/{table}/*.parquet
    3. data/lakehouse/ods/{platform}/{table}/*.parquet
    4. data/historical/{platform}/{table}*.parquet

用法：
    from dg_nl2sql import build_context
    ctx = build_context("各矿井精煤灰分排名")
"""
from __future__ import annotations

import glob
import os
import re
import sys
import urllib.parse
from pathlib import Path

import pyarrow.parquet as pq
import requests
import yaml

# ── 常量 ────────────────────────────────────────────────────────────────────
GMS_HOST = os.getenv("DATAHUB_GMS_URL", "http://localhost:28080")
GMS_AUTH = ("datahub", "datahub")
GMS_TIMEOUT = 10
TOP_K_TABLES = 5

# 4 张 DWA 宽表（主查询目标 / 默认候选集）
DWA_TABLES: list[tuple[str, str]] = [
    ("dwa", "dwa_coal_quality"),
    ("dwa", "dwa_sales_daily"),
    ("dwa", "dwa_tag_alarm"),
    ("dwa", "dwa_sales_production"),
]

# URN 正则
_DATASET_URN_RE = re.compile(
    r"^urn:li:dataset:\(urn:li:dataPlatform:([^,]+),([^,]+),PROD\)$"
)
_FIELD_URN_RE = re.compile(
    r"^urn:li:schemaField:\(urn:li:dataset:\(urn:li:dataPlatform:([^,]+),([^,]+),PROD\),([^)]+)\)$"
)


# ── URN 构造与解析 ──────────────────────────────────────────────────────────

def build_urn(platform: str, table: str) -> str:
    """构造 dataset URN。"""
    return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table},PROD)"


def parse_urn(urn: str) -> tuple[str, str] | None:
    """从 dataset URN 提取 (platform, table)；失败返回 None。"""
    m = _DATASET_URN_RE.match(urn)
    return (m.group(1), m.group(2)) if m else None


def parse_field_urn(urn: str) -> tuple[str, str, str] | None:
    """从 schemaField URN 提取 (platform, table, column)；失败返回 None。"""
    m = _FIELD_URN_RE.match(urn)
    return (m.group(1), m.group(2), m.group(3)) if m else None


# ── 项目根与 Parquet 定位 ──────────────────────────────────────────────────

def _project_root() -> Path:
    """返回项目根目录（src/dg_nl2sql/context_builder.py → 3 层上溯）。"""
    return Path(__file__).resolve().parent.parent.parent


def _find_parquet(platform: str, table: str) -> str | None:
    """按优先级 glob 查找 (platform, table) 对应的 Parquet 文件路径。"""
    root = _project_root() / "data"
    patterns = [
        str(root / "lakehouse" / "dwa" / "**" / table / "*.parquet"),
        str(root / "lakehouse" / "dwd" / "**" / table / "*.parquet"),
        str(root / "lakehouse" / "ods" / platform / table / "*.parquet"),
        str(root / "historical" / platform / f"{table}*.parquet"),
    ]
    for pat in patterns:
        matches = sorted(glob.glob(pat, recursive=True))
        if matches:
            return matches[0]
    return None


def _read_parquet_meta(path: str) -> tuple[list[dict[str, str]], int | None]:
    """从 Parquet 读 schema + 行数。"""
    try:
        schema = pq.read_schema(path)
        columns = [{"name": f.name, "type": str(f.type)} for f in schema]
        row_count: int | None = None
        try:
            row_count = pq.read_metadata(path).num_rows
        except Exception:  # noqa: BLE001
            pass
        return columns, row_count
    except Exception as e:  # noqa: BLE001
        print(f"[context_builder] 读 Parquet 失败: {path}: {e}", file=sys.stderr)
        return [], None


# ── GMS REST 查询 ──────────────────────────────────────────────────────────

def _gms_alive() -> bool:
    """检查 GMS 是否可达（GraphQL ping）。"""
    try:
        resp = requests.post(
            f"{GMS_HOST}/api/graphql",
            json={"query": "{ __typename }"},
            auth=GMS_AUTH,
            timeout=3,
        )
        return (
            resp.status_code == 200
            and resp.json().get("data", {}).get("__typename") == "Query"
        )
    except requests.RequestException:
        return False


def _query_aspect(urn: str, aspect: str) -> dict | None:
    """GET /aspects/{urlencoded_urn}?aspect={aspect}&version=0。

    aspect → DataHub aspect 类的全限定名映射：
        upstreamLineage → com.linkedin.dataset.UpstreamLineage
        glossaryTerms   → com.linkedin.common.GlossaryTerms
        schemaMetadata  → com.linkedin.schema.SchemaMetadata
        datasetProperties → com.linkedin.dataset.DatasetProperties

    Returns:
        aspect payload dict（术语/血缘的 value 字段），或 None（404/网络错误时）
    """
    aspect_class = {
        "upstreamLineage": "com.linkedin.dataset.UpstreamLineage",
        "glossaryTerms": "com.linkedin.common.GlossaryTerms",
        "schemaMetadata": "com.linkedin.schema.SchemaMetadata",
        "datasetProperties": "com.linkedin.dataset.DatasetProperties",
    }.get(aspect, f"com.linkedin.dataset.{aspect}")

    encoded = urllib.parse.quote(urn, safe="")
    url = f"{GMS_HOST}/aspects/{encoded}?aspect={aspect}&version=0"
    try:
        resp = requests.get(url, auth=GMS_AUTH, timeout=GMS_TIMEOUT)
    except requests.RequestException as e:
        print(f"[context_builder] GMS 请求失败: {url}: {e}", file=sys.stderr)
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("aspect", {}).get(aspect_class)


def _query_upstream_lineage(urn: str) -> tuple[list[dict], list[dict]]:
    """从 GMS 查 dataset 的 upstreamLineage。

    Returns:
        (table_edges, column_edges)
        - table_edges: [{"upstream": "platform.table", "type": "TRANSFORMED"}]
        - column_edges: [{
            "downstream_table": "platform.table",
            "downstream_col": "col",
            "upstream_table": "platform.table",
            "upstream_col": "col",
            "transform": "AVG(AD)",
          }]
    """
    aspect = _query_aspect(urn, "upstreamLineage")
    if not aspect:
        return [], []
    table_edges: list[dict] = []
    for up in aspect.get("upstreams") or []:
        ds_urn = up.get("dataset")
        if not ds_urn:
            continue
        parsed = parse_urn(ds_urn)
        if not parsed:
            continue
        table_edges.append({
            "upstream": f"{parsed[0]}.{parsed[1]}",
            "type": up.get("type", "TRANSFORMED"),
        })
    column_edges: list[dict] = []
    for fgl in aspect.get("fineGrainedLineages") or []:
        ups = fgl.get("upstreams") or []
        downs = fgl.get("downstreams") or []
        transform = fgl.get("transformOperation", "")
        for d_urn in downs:
            d_parsed = parse_field_urn(d_urn)
            if not d_parsed:
                continue
            for u_urn in ups:
                u_parsed = parse_field_urn(u_urn)
                if not u_parsed:
                    continue
                column_edges.append({
                    "downstream_table": f"{d_parsed[0]}.{d_parsed[1]}",
                    "downstream_col": d_parsed[2],
                    "upstream_table": f"{u_parsed[0]}.{u_parsed[1]}",
                    "upstream_col": u_parsed[2],
                    "transform": transform,
                })
    return table_edges, column_edges


def _query_glossary_terms(urn: str) -> list[dict]:
    """从 GMS 查 dataset 的 glossaryTerms。

    Returns:
        [{"term": "...", "column": "...", "table": "...",
          "cn_name": "...", "value_mappings": {...}}]
    """
    aspect = _query_aspect(urn, "glossaryTerms")
    if not aspect:
        return []
    result: list[dict] = []
    for term in aspect.get("terms") or []:
        ctx = term.get("context", "")
        # 解析 "column:col|cn:中文|table:tbl|values:k1=v1,k2=v2"
        parts: dict[str, str] = {}
        for seg in ctx.split("|"):
            if ":" in seg:
                k, v = seg.split(":", 1)
                parts[k] = v
        term_urn = term.get("urn", "")
        entry: dict = {
            "term": term_urn.rsplit(":", 1)[-1] if term_urn else "",
            "column": parts.get("column", ""),
            "table": parts.get("table", ""),
            "cn_name": parts.get("cn", ""),
        }
        # 解析 value_mappings: "k1=v1,k2=v2" → {"k1": "v1", "k2": "v2"}
        values_str = parts.get("values", "")
        if values_str:
            vm: dict[str, str] = {}
            for pair in values_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    vm[k] = v
            if vm:
                entry["value_mappings"] = vm
        result.append(entry)
    return result


# ── 词典加载 ────────────────────────────────────────────────────────────────

def _load_glossary_yaml() -> dict[tuple[str, str], dict[str, dict]]:
    """读 data/glossary_terms.yaml。

    Returns:
        {(platform, table): {column_name: column_dict}} 索引
    """
    path = _project_root() / "data" / "glossary_terms.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    idx: dict[tuple[str, str], dict[str, dict]] = {}
    for entry in data.get("glossary") or []:
        key = (entry.get("platform"), entry.get("table"))
        col_idx: dict[str, dict] = {}
        for col in entry.get("columns") or []:
            col_idx[col["column"]] = col
        idx[key] = col_idx
    return idx


_TABLE_CN_CACHE: dict[tuple[str, str], str] | None = None


def _lookup_table_cn(platform: str, table: str) -> str:
    """从 glossary_terms.yaml 查 (platform, table) -> table_cn，懒加载缓存。"""
    global _TABLE_CN_CACHE
    if _TABLE_CN_CACHE is None:
        path = _project_root() / "data" / "glossary_terms.yaml"
        cache: dict[tuple[str, str], str] = {}
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for entry in data.get("glossary") or []:
                key = (entry.get("platform"), entry.get("table"))
                cache[key] = entry.get("table_cn", "") or ""
        _TABLE_CN_CACHE = cache
    return _TABLE_CN_CACHE.get((platform, table), "")


# ── 表 record 构建 ──────────────────────────────────────────────────────────

def _build_table_record(
    platform: str,
    table: str,
    glossary_idx: dict[tuple[str, str], dict[str, dict]],
) -> dict:
    """为 (platform, table) 构造 record：URN + Parquet schema + YAML 词典合并。"""
    urn = build_urn(platform, table)
    pq_path = _find_parquet(platform, table)
    columns_raw, row_count = _read_parquet_meta(pq_path) if pq_path else ([], None)
    col_glossary = glossary_idx.get((platform, table), {})
    columns: list[dict] = []
    for col in columns_raw:
        g = col_glossary.get(col["name"], {})
        columns.append({
            "name": col["name"],
            "type": col["type"],
            "cn_name": g.get("cn_name", ""),
            "business_terms": g.get("business_terms", []) or [],
        })
    return {
        "platform": platform,
        "table": table,
        "table_cn": _lookup_table_cn(platform, table),
        "urn": urn,
        "columns": columns,
        "row_count": row_count,
        "_parquet_path": pq_path,
    }


# ── 相关性裁剪 ──────────────────────────────────────────────────────────────

def _score_relevance(question: str, record: dict) -> int:
    """基于中文关键词 + value_mappings 计算表的相关性分数。

    命中规则：
        - business_terms 中的任一词出现在 question 中 → +2
        - cn_name 出现在 question 中 → +1
        - value_mappings 的任一 value 出现在 question 中 → +1
    """
    if not question:
        return 0
    score = 0
    yaml_cols = _load_glossary_yaml().get(
        (record["platform"], record["table"]), {}
    )
    for col in record["columns"]:
        for term in col.get("business_terms", []):
            if term and term in question:
                score += 2
        cn = col.get("cn_name")
        if cn and cn in question:
            score += 1
        # 查 value_mappings
        yaml_col = yaml_cols.get(col["name"], {})
        for v in (yaml_col.get("value_mappings") or {}).values():
            if v and v in question:
                score += 1
    return score


def _select_relevant_tables(
    question: str, dwa_records: list[dict]
) -> list[tuple[dict, str]]:
    """根据 question 选取 top-K DWA 表。

    Returns:
        [(record, relevance_label), ...]  # label ∈ {"high", "low"}
    """
    scored = [(rec, _score_relevance(question, rec)) for rec in dwa_records]
    max_score = max((s for _, s in scored), default=0)
    if max_score == 0:
        # 无关键词命中：返回全部 DWA，标记 low
        return [(rec, "low") for rec, _ in scored]
    # 按分数降序，取 top-K
    scored.sort(key=lambda x: -x[1])
    return [
        (rec, "high" if s > 0 else "low")
        for rec, s in scored[:TOP_K_TABLES]
    ]


# ── 3 层裁剪（field / glossary / mapping）──────────────────────────────────

def _is_key_column(col: dict) -> bool:
    """主键/分组键判断：列名后缀为 _CODE/_ID/_DATE/_NO，或 business_terms 含"编号"/"日期"/"号"。

    这些字段 LLM 生成 GROUP BY/JOIN 时必须有完整信息。
    """
    name = (col.get("name") or "").upper()
    if any(s in name for s in ("_CODE", "_ID", "_DATE", "_NO")):
        return True
    if name.endswith(("CODE", "ID", "DATE", "NO")):
        return True
    for t in (col.get("business_terms") or []):
        if "编号" in t or "日期" in t or "号" in t:
            return True
    return False


def _column_matches_question(
    col: dict, question: str, value_mappings: dict | None = None
) -> bool:
    """字段级关键词命中：cn_name / business_terms / value_mappings 任一值是 question 子串。"""
    if not question:
        return False
    cn = col.get("cn_name") or ""
    if cn and cn in question:
        return True
    for term in (col.get("business_terms") or []):
        if term and term in question:
            return True
    for v in (value_mappings or {}).values():
        if v and v in question:
            return True
    return False


def _filter_columns(
    question: str,
    columns: list[dict],
    glossary_idx: dict[tuple[str, str], dict[str, dict]],
    platform: str,
    table: str,
) -> list[dict]:
    """Layer 2: 字段级裁剪。

    - 匹配字段（cn_name / business_terms / value_mappings 命中问题子串）-> 完整保留
    - 主键字段（_is_key_column）-> 完整保留
    - 其他字段 -> 只保留 name
    """
    yaml_cols = (glossary_idx or {}).get((platform, table), {})
    result: list[dict] = []
    for col in columns or []:
        yaml_col = yaml_cols.get(col.get("name", ""), {})
        value_mappings = yaml_col.get("value_mappings") or {}
        if _is_key_column(col) or _column_matches_question(col, question, value_mappings):
            result.append({
                "name": col.get("name"),
                "type": col.get("type"),
                "cn_name": col.get("cn_name"),
                "business_terms": col.get("business_terms"),
            })
        else:
            result.append({"name": col.get("name")})
    return result


def _filter_glossary(question: str, glossary_list: list[dict]) -> list[dict]:
    """Layer 3: 词典裁剪。只保留 term / cn_name / column / table / value_mappings 中任一字段是问题子串的条目。"""
    if not question:
        return []
    result: list[dict] = []
    for entry in glossary_list or []:
        matched = False
        for k in ("term", "cn_name", "column", "table"):
            v = entry.get(k) or ""
            if v and v in question:
                matched = True
                break
        if not matched:
            for v in (entry.get("value_mappings") or {}).values():
                if v and v in question:
                    matched = True
                    break
        if matched:
            result.append(entry)
    return result


def _filter_column_mappings(
    column_mappings: list[dict], kept_columns: set[str] | list[str]
) -> list[dict]:
    """Layer 3: 列级映射裁剪。只保留 downstream_col 在 kept_columns 中的映射。"""
    if isinstance(kept_columns, list):
        kept_columns = set(kept_columns)
    return [
        cm for cm in (column_mappings or [])
        if cm.get("downstream_col") in kept_columns
    ]


# ── 主入口 ──────────────────────────────────────────────────────────────────

def build_context(question: str) -> dict:
    """从 DataHub GMS 真实查询血缘/schema/词典，构建 NL2SQL 上下文（3 层裁剪后）。

    3 层裁剪：
      Layer 1 表级：low 表仅返回概览（无 columns + 跳过 GMS）；1 跳血缘邻居标 "neighbor"
      Layer 2 字段：匹配/主键字段完整保留，其他字段只保留 name
      Layer 3 词典/映射：glossary 与 column_mappings 只保留与问题子串相关的条目

    Args:
        question: 用户自然语言问题（中文/英文均可；中文按子串匹配）

    Returns:
        {
          "source": "gms",
          "tables": [
            {"platform", "table", "table_cn", "urn"?,
             "columns"?, "row_count", "relevance"}  # relevance ∈ {high, low, neighbor}
          ],
          "lineage_edges": [{"downstream", "upstream", "type", "column_mappings"?}],
          "glossary": [{"term", "column", "table", "cn_name", "value_mappings"?}],
        }

    Raises:
        RuntimeError: GMS 不可达时（不退回 lineage_recipe.yaml）
    """
    if not _gms_alive():
        raise RuntimeError(
            f"DataHub GMS 不可达 ({GMS_HOST})，无法构建 NL2SQL 上下文。"
            "请确认 GMS 已启动（docker ps | grep datahub-gms）。"
        )

    glossary_idx = _load_glossary_yaml()

    # 1) 4 张 DWA 表的 schema + URN
    dwa_records = [
        _build_table_record(p, t, glossary_idx) for p, t in DWA_TABLES
    ]

    # 2) 相关性裁剪
    selected = _select_relevant_tables(question, dwa_records)

    # 3) 查血缘 + 词典（仅对 high 表调用 GMS；low 表无列，省 API）
    all_lineage_edges: list[dict] = []
    all_glossary: list[dict] = []
    neighbor_records: dict[str, dict] = {}  # 1-hop 血缘邻居（platform.table -> record）

    for rec, rel in selected:
        if rel != "high":
            continue
        ds_short = f"{rec['platform']}.{rec['table']}"
        table_edges, column_edges = _query_upstream_lineage(rec["urn"])
        # 把列级映射按上游表分组挂到表级边上
        col_map_by_upstream: dict[str, list[dict]] = {}
        for ce in column_edges:
            if ce["downstream_table"] != ds_short:
                continue
            col_map_by_upstream.setdefault(ce["upstream_table"], []).append({
                "downstream_col": ce["downstream_col"],
                "upstream_col": ce["upstream_col"],
                "transform": ce["transform"],
            })
        for te in table_edges:
            edge = {
                "downstream": ds_short,
                "upstream": te["upstream"],
                "type": te["type"],
            }
            mappings = col_map_by_upstream.get(te["upstream"])
            if mappings:
                edge["column_mappings"] = mappings
            all_lineage_edges.append(edge)
            # 收集 1-hop 血缘邻居（无 columns，仅概览）
            if te["upstream"] not in neighbor_records:
                up_platform, up_table = te["upstream"].split(".", 1)
                neighbor_records[te["upstream"]] = {
                    "platform": up_platform,
                    "table": up_table,
                    "urn": build_urn(up_platform, up_table),
                    "relevance": "neighbor",
                }
        all_glossary.extend(_query_glossary_terms(rec["urn"]))

    # 4) Layer 2 字段级裁剪 + 构造 tables 输出
    final_tables: list[dict] = []
    kept_full_columns: set[str] = set()  # 完整保留的 downstream_col 集合
    for rec, rel in selected:
        out = {k: v for k, v in rec.items() if not k.startswith("_")}
        if rel == "high":
            kept_cols = _filter_columns(
                question, rec["columns"], glossary_idx, rec["platform"], rec["table"]
            )
            kept_full_columns.update(c["name"] for c in kept_cols if "type" in c)
            out["columns"] = kept_cols
        else:
            # low: 去掉 columns，仅保留概览
            out.pop("columns", None)
        out["relevance"] = rel
        final_tables.append(out)

    # 追加 1-hop 邻居（无 columns）
    for nrec in neighbor_records.values():
        final_tables.append(nrec)

    # 5) Layer 3 词典裁剪
    kept_glossary = _filter_glossary(question, all_glossary)

    # 6) Layer 3 列级映射裁剪
    final_lineage_edges: list[dict] = []
    for edge in all_lineage_edges:
        new_edge = {k: v for k, v in edge.items() if k != "column_mappings"}
        mappings = edge.get("column_mappings")
        if mappings:
            kept = _filter_column_mappings(mappings, kept_full_columns)
            if kept:
                new_edge["column_mappings"] = kept
        final_lineage_edges.append(new_edge)

    return {
        "source": "gms",
        "tables": final_tables,
        "lineage_edges": final_lineage_edges,
        "glossary": kept_glossary,
    }


if __name__ == "__main__":
    # CLI: uv run python -m dg_nl2sql.context_builder "问题"
    import json
    q = sys.argv[1] if len(sys.argv) > 1 else ""
    print(json.dumps(build_context(q), ensure_ascii=False, indent=2))
