"""
engine — NL2SQL 引擎：自然语言问题 -> 上下文构建 -> LLM 生成 SQL -> DuckDB 执行 -> 结果 + 血缘解释。

设计原则：
- 完全只读：拒绝任何写操作（INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE）
- 表名 -> read_parquet 自动替换：context_builder 已为每张表找到 _parquet_path
- 失败重试：SQL 执行失败时，把错误信息回传 LLM 修正，最多 1 次
- 血缘解释：从 context.lineage_edges 中查找 SQL 涉及表的下游链路

依赖：
- dg_nl2sql.context_builder（Task 3 产出）— 构建 context
- dg_nl2sql.llm_client — OpenAI 兼容 LLM 客户端
- duckdb — 本地 OLAP 执行

用法：
    from dg_nl2sql.engine import NL2SQLEngine
    engine = NL2SQLEngine()
    out = engine.ask("各矿井精煤灰分排名")
    print(out["sql"], out["result"], out["lineage_explanation"])
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import duckdb

from dg_nl2sql.context_builder import build_context
from dg_nl2sql.llm_client import LLMClient, LLMError, get_default_client

# ── Prompt 模板 ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个煤炭数据治理平台的 SQL 生成助手。根据用户问题生成 DuckDB SQL 查询。

规则：
1. 只生成 SELECT 语句，禁止 INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE
2. 表名使用提供的表名（如 dwa_coal_quality），引擎会自动替换为文件路径
3. 日期函数用 DuckDB 语法（如 STRFTIME, DATE_TRUNC, CURRENT_DATE - INTERVAL '30 day'）
4. 如果问题涉及跨系统 JOIN 但上下文中没有可执行 JOIN 路径，返回 "ERROR: 无法跨系统 JOIN" 并说明原因
5. 业务术语映射参考 glossary（如"精煤"对应 SAMPLE_TYPE='精煤'，"灰分"对应 avg_ash_content）
6. 字段名严格使用 schema 中提供的列名（区分大小写）
7. 仅返回 SQL 语句，不要任何额外解释。如果无法生成 SQL，返回 "ERROR: 原因"

输出格式：只返回 SQL 语句，不要解释。如果无法生成 SQL，返回 "ERROR: 原因"。"""


# 拒绝关键字（写操作 / DDL / 危险操作）
FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "COPY", "EXPORT",
    "GRANT", "REVOKE", "PRAGMA", "VACUUM",
)

# 表名替换时允许的 SQL 关键字（FROM/JOIN/INTO 后的标识符）
_TABLE_NAME_RE = re.compile(
    r"(?i)\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_.]*)"
)


# ── 辅助函数 ────────────────────────────────────────────────────────────────

def extract_sql(llm_response: str) -> str:
    """从 LLM 响应中提取 SQL。

    处理：
    - ```sql ... ``` / ``` ... ``` markdown 块
    - 首尾空白
    - 开头说明文字（"以下是 SQL:" 等）
    """
    text = llm_response.strip()
    if not text:
        return ""

    # 1) markdown ```sql ... ``` 块
    md_match = re.search(r"```(?:sql|duckdb)?\s*\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if md_match:
        text = md_match.group(1).strip()

    # 2) 去掉前导说明（取第一个 SELECT 关键字开始）
    if not text.lower().startswith("select"):
        sel_match = re.search(r"(?i)\bselect\b", text)
        if sel_match:
            text = text[sel_match.start():].strip()
        else:
            # 不是 SQL（如 ERROR: ...），原样返回
            return text

    # 3) 去掉末尾注释 / 解释
    text = text.split(";")[0].strip()
    if not text.lower().startswith("select"):
        # 仍不是 SELECT，认为是 ERROR
        return text

    # 确保以分号结尾
    if not text.endswith(";"):
        text = text + ";"
    return text


def is_safe_select(sql: str) -> tuple[bool, str]:
    """校验 SQL 是否为只读 SELECT（白名单：去掉注释/字符串后扫描关键字）。

    Returns:
        (is_safe, reason)  reason 为空字符串表示通过
    """
    if not sql or not sql.strip():
        return False, "空 SQL"

    # 去掉单行注释 -- ... 和 /* ... */
    cleaned = re.sub(r"--[^\n]*", " ", sql)
    cleaned = re.sub(r"/\*.*?\*/", " ", cleaned, flags=re.DOTALL)
    # 去掉单引号字符串中的内容（避免匹配到 'INSERT INTO' 字面量）
    cleaned = re.sub(r"'(?:''|[^'])*'", "''", cleaned)

    upper = cleaned.upper()
    # 必须以 SELECT 开头（容忍前置空白）
    if not re.match(r"^\s*SELECT\b", upper):
        return False, "非 SELECT 语句"

    # 检查禁用关键字
    for kw in FORBIDDEN_KEYWORDS:
        # 单词边界匹配（避免 LATER 这种假阳性）
        if re.search(rf"\b{kw}\b", upper):
            return False, f"包含禁用关键字: {kw}"

    return True, ""


def _glob_to_parquet(glob_pattern: str) -> str:
    """把 glob pattern 转成 DuckDB `read_parquet([...])` 调用（用 glob 形式即可）。

    DuckDB 原生支持 read_parquet('**/*.parquet', hive_partitioning=false)，
    但这里我们直接传 glob 模式（read_parquet 接受数组或 glob）。
    """
    return f"read_parquet('{glob_pattern}')"


def build_table_path_map(context: dict) -> dict[str, str]:
    """从 context.tables 构造 {table_name: parquet_glob} 映射。

    优先复用 context_builder 已找到的路径（_parquet_path 在 _build_table_record
    中填入但 build_context 会过滤掉 `_` 开头字段，所以这里要重新走 glob 兜底）。
    """
    from dg_nl2sql.context_builder import _find_parquet

    table_map: dict[str, str] = {}
    for t in context.get("tables") or []:
        platform = t.get("platform", "")
        table = t.get("table", "")
        if not table:
            continue
        # 优先用 _find_parquet 拿到的路径，反推 glob（路径中往往只是单文件）
        # DuckDB read_parquet 接受单文件 / 数组 / glob，统一用 glob 形式
        path = _find_parquet(platform, table)
        if path:
            # 若是单文件（往往是 part-*.parquet），找其所在目录的 *.parquet glob
            p = Path(path)
            if p.is_file():
                glob_pattern = str(p.parent / "*.parquet")
            else:
                glob_pattern = str(path)
            table_map[table] = glob_pattern
    return table_map


def replace_table_names(sql: str, table_map: dict[str, str]) -> str:
    """把 SQL 中的 FROM/JOIN 后面的表名替换为 read_parquet(...) 调用。

    匹配规则：
    - 匹配 FROM/JOIN 后的标识符
    - 如果该标识符在 table_map 中 → 替换为 read_parquet('...')
    - 保留 AS 别名
    """
    def _replace(m: re.Match) -> str:
        keyword = m.group(1)
        table = m.group(2)
        if table in table_map:
            return f"{keyword} {_glob_to_parquet(table_map[table])}"
        return m.group(0)

    pattern = re.compile(r"(?i)\b(from|join)\s+([A-Za-z_][A-Za-z0-9_.]*)")
    return pattern.sub(_replace, sql)


def execute_sql(sql: str, max_rows: int = 100) -> dict[str, Any]:
    """在 DuckDB 中执行 SQL，返回结构化结果。

    Returns:
        {"columns": [...], "rows": [...], "row_count": N, "truncated": bool}
    """
    con = duckdb.connect(":memory:")
    try:
        result = con.execute(sql)
        cols = [d[0] for d in result.description] if result.description else []
        rows = result.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        return {
            "columns": cols,
            "rows": [list(r) for r in rows],
            "row_count": len(rows),
            "truncated": truncated,
        }
    finally:
        con.close()


def format_result_table(result: dict[str, Any], max_col_width: int = 24) -> str:
    """把执行结果格式化为可打印的表格字符串。"""
    cols = result.get("columns") or []
    rows = result.get("rows") or []
    if not cols:
        return "(无结果)"

    # 截断过长的单元格
    def _trunc(v: Any) -> str:
        s = "" if v is None else str(v)
        if len(s) > max_col_width:
            s = s[: max_col_width - 1] + "…"
        return s

    # 计算每列宽度
    widths = [len(c) for c in cols]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(_trunc(v)))

    lines = []
    # 表头
    header = "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    sep = "  ".join("-" * w for w in widths)
    lines.append(header)
    lines.append(sep)
    for r in rows:
        lines.append("  ".join(_trunc(v).ljust(widths[i]) for i, v in enumerate(r)))
    if result.get("truncated"):
        lines.append(f"... (结果已截断到 {result.get('row_count')} 行)")
    return "\n".join(lines)


_OPERATION_PATTERNS: list[tuple[str, str]] = [
    (r"\bAVG\s*\(", "AVG聚合"),
    (r"\bSUM\s*\(", "SUM累加"),
    (r"\bCOUNT\s*\(", "COUNT计数"),
    (r"\bMAX\s*\(", "MAX极值"),
    (r"\bMIN\s*\(", "MIN极值"),
    (r"\bSUBSTR\s*\(", "字符串派生"),
    (r"\bCAST\s*\(", "类型转换"),
    (r"\bSTRFTIME\s*\(", "日期格式化"),
    (r"\bDATE_TRUNC\s*\(", "日期截断"),
    (r"\bCONCAT\s*\(|^\s*\|\|", "字符串拼接"),
    (r"ROUND\s*\(", "四舍五入"),
    (r"COALESCE\s*\(", "空值兜底"),
]


def _summarize_transforms(transforms: list[str]) -> str:
    """把一批 SQL transform 表达式归并为简短中文描述。

    策略：
    - 按操作类型（AVG/SUM/COUNT/MAX/MIN/SUBSTR...）归类
    - 统计总条数 + 主要操作
    - 空 / 只有直接映射 → "直接映射"
    """
    if not transforms:
        return "ETL加工"

    clean = [t for t in transforms if t and t.strip()]
    if not clean:
        return "直接映射"

    # 全部都是直接映射的标记
    direct_markers = {"", "直接映射", "IDENTITY", "identity"}
    only_direct = all(t.strip() in direct_markers for t in clean)
    if only_direct:
        return "直接映射"

    # 抽取出现的操作类型
    op_hits: list[str] = []
    text = " ".join(clean)
    for pat, label in _OPERATION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            op_hits.append(label)

    if not op_hits:
        return "ETL加工"

    if len(op_hits) == 1:
        return op_hits[0]
    if len(op_hits) <= 3:
        return "+".join(op_hits)
    return f"{op_hits[0]}+{op_hits[1]}+等{len(op_hits)}类"


def build_lineage_explanation(context: dict, sql_tables: set[str]) -> list[str]:
    """根据 SQL 涉及的表名，从 lineage_edges 生成血缘解释文本。

    Args:
        context: build_context() 输出
        sql_tables: SQL 中出现的下游表名集合（如 {"dwa_coal_quality"}）

    Returns:
        解释列表，每条形如 "数据来自: dwa_coal_quality <- lims.samples (加工: AVG聚合)"
    """
    explanations: list[str] = []
    seen: set[tuple[str, str]] = set()
    for edge in context.get("lineage_edges") or []:
        downstream = edge.get("downstream", "")
        # 提取下游表名（去掉 platform 前缀）
        downstream_table = downstream.split(".", 1)[-1] if "." in downstream else downstream
        if downstream_table not in sql_tables:
            continue
        upstream = edge.get("upstream", "未知来源")
        col_mappings = edge.get("column_mappings") or []
        # 汇总该边的 transform 描述
        transforms: list[str] = []
        for cm in col_mappings:
            t = (cm.get("transform") or "").strip()
            if t:
                transforms.append(t)
        transform_desc = _summarize_transforms(transforms)
        key = (downstream, upstream)
        if key in seen:
            continue
        seen.add(key)
        explanations.append(
            f"数据来自: {downstream} <- {upstream} (加工: {transform_desc})"
        )
    if not explanations:
        # 兜底：至少告诉用户表名
        for t in sorted(sql_tables):
            explanations.append(f"数据来自: dwa.{t} (加工: DWA 宽表)")
    return explanations


def extract_sql_table_names(sql: str, table_map: dict[str, str]) -> set[str]:
    """从 SQL 中提取 table_map 中已知的表名集合。"""
    found: set[str] = set()
    for m in _TABLE_NAME_RE.finditer(sql):
        ident = m.group(1)
        if ident in table_map:
            found.add(ident)
    return found


# ── 引擎主类 ────────────────────────────────────────────────────────────────

class NL2SQLEngine:
    """NL2SQL 端到端引擎。

    Attributes:
        llm_client: LLM 客户端
        max_retries: SQL 修正最大次数（默认 1）
    """

    def __init__(self, llm_client: LLMClient | None = None, max_retries: int = 1) -> None:
        self.llm_client = llm_client or get_default_client()
        self.max_retries = max_retries

    def ask(self, question: str) -> dict[str, Any]:
        """完整流程：问题 -> 上下文 -> SQL -> 执行 -> 血缘解释。

        Returns:
            {
                "question": str,
                "sql": str,                  # 最终执行的 SQL
                "raw_sql": str,              # LLM 直接返回的 SQL（替换前）
                "result": {columns, rows, row_count, truncated} | None,
                "row_count": int,
                "lineage_explanation": [str, ...],
                "success": bool,
                "error": str | None,
                "context_source": str,
            }
        """
        out: dict[str, Any] = {
            "question": question,
            "sql": "",
            "raw_sql": "",
            "result": None,
            "row_count": 0,
            "lineage_explanation": [],
            "success": False,
            "error": None,
            "context_source": "",
        }

        # 1) 上下文
        try:
            context = build_context(question)
        except Exception as e:  # noqa: BLE001
            out["error"] = f"context 构建失败: {e}"
            return out
        out["context_source"] = context.get("source", "")

        # 2) 构造 prompt
        user_message = self._build_user_message(question, context)
        table_map = build_table_path_map(context)

        # 3) LLM 生成 SQL
        try:
            raw_response = self.llm_client.chat(SYSTEM_PROMPT, user_message)
        except LLMError as e:
            out["error"] = f"LLM 调用失败: {e}"
            return out

        raw_sql = extract_sql(raw_response)
        out["raw_sql"] = raw_sql

        # 处理 LLM 显式返回的 ERROR
        if raw_sql.upper().startswith("ERROR"):
            out["error"] = raw_sql
            return out

        # 4) 安全校验
        safe, reason = is_safe_select(raw_sql)
        if not safe:
            out["error"] = f"SQL 安全校验失败: {reason}"
            return out

        # 5) 表名替换 + 执行（含 1 次修正重试）
        final_sql, exec_result, exec_error = self._execute_with_retry(
            raw_sql, table_map, user_message
        )
        out["sql"] = final_sql
        if exec_result is not None:
            out["result"] = exec_result
            out["row_count"] = exec_result.get("row_count", 0)
            out["success"] = True
        else:
            out["error"] = exec_error

        # 6) 血缘解释
        sql_tables = extract_sql_table_names(raw_sql, table_map)
        if not sql_tables:
            # 兜底：取 context 的所有表
            sql_tables = {t["table"] for t in context.get("tables") or [] if t.get("table")}
        out["lineage_explanation"] = build_lineage_explanation(context, sql_tables)

        return out

    # ── 内部 ────────────────────────────────────────────────────────────────

    def _build_user_message(self, question: str, context: dict) -> str:
        """构造 LLM 输入：问题 + 上下文 JSON。"""
        # 控制上下文大小：只保留必要字段
        slim_ctx = {
            "tables": [
                {
                    "table": t.get("table"),
                    "platform": t.get("platform"),
                    "columns": [
                        {"name": c.get("name"), "type": c.get("type"),
                         "cn_name": c.get("cn_name"), "business_terms": c.get("business_terms")}
                        for c in (t.get("columns") or [])
                    ],
                    "relevance": t.get("relevance"),
                }
                for t in (context.get("tables") or [])
            ],
            "lineage_edges": [
                {
                    "downstream": e.get("downstream"),
                    "upstream": e.get("upstream"),
                    "column_mappings": [
                        {"downstream_col": cm.get("downstream_col"),
                         "upstream_col": cm.get("upstream_col"),
                         "transform": cm.get("transform")}
                        for cm in (e.get("column_mappings") or [])
                    ],
                }
                for e in (context.get("lineage_edges") or [])
            ],
            "glossary": context.get("glossary") or [],
        }
        ctx_json = json.dumps(slim_ctx, ensure_ascii=False, indent=2)
        return (
            f"## 用户问题\n{question}\n\n"
            f"## 可用表/字段/血缘上下文（JSON）\n```json\n{ctx_json}\n```\n\n"
            f"请基于上述 schema 与血缘，生成 DuckDB SQL。"
        )

    def _execute_with_retry(
        self,
        raw_sql: str,
        table_map: dict[str, str],
        user_message: str,
    ) -> tuple[str, dict | None, str | None]:
        """执行 SQL，失败时让 LLM 修正一次。"""
        # 第一次执行
        sql_with_paths = replace_table_names(raw_sql, table_map)
        try:
            result = execute_sql(sql_with_paths)
            return sql_with_paths, result, None
        except Exception as e:  # noqa: BLE001
            first_error = f"{type(e).__name__}: {e}"
            if self.max_retries <= 0:
                return sql_with_paths, None, first_error

        # 修正重试
        correction_prompt = (
            f"{user_message}\n\n"
            f"## 你上一轮生成的 SQL\n```sql\n{raw_sql}\n```\n\n"
            f"## 执行错误\n{first_error}\n\n"
            f"请重新生成正确的 DuckDB SQL，遵守所有规则。"
        )
        try:
            corrected_response = self.llm_client.chat(SYSTEM_PROMPT, correction_prompt)
        except LLMError as e:
            return sql_with_paths, None, f"修正请求失败: {e}; 原始错误: {first_error}"

        corrected_sql = extract_sql(corrected_response)
        if corrected_sql.upper().startswith("ERROR"):
            return sql_with_paths, None, f"LLM 放弃: {corrected_sql}; 原始错误: {first_error}"

        safe, reason = is_safe_select(corrected_sql)
        if not safe:
            return sql_with_paths, None, f"修正后 SQL 不安全: {reason}; 原始错误: {first_error}"

        corrected_with_paths = replace_table_names(corrected_sql, table_map)
        try:
            result = execute_sql(corrected_with_paths)
            return corrected_with_paths, result, None
        except Exception as e:  # noqa: BLE001
            return corrected_with_paths, None, (
                f"修正后仍失败: {type(e).__name__}: {e}; 原始错误: {first_error}"
            )


__all__ = [
    "NL2SQLEngine",
    "SYSTEM_PROMPT",
    "extract_sql",
    "is_safe_select",
    "replace_table_names",
    "execute_sql",
    "format_result_table",
    "build_table_path_map",
    "build_lineage_explanation",
    "extract_sql_table_names",
]


if __name__ == "__main__":
    # 简单烟雾测试
    q = sys.argv[1] if len(sys.argv) > 1 else "各矿井精煤灰分排名"
    out = NL2SQLEngine().ask(q)
    print(json.dumps({k: v for k, v in out.items() if k != "result"}, ensure_ascii=False, indent=2))
    if out.get("result"):
        print(format_result_table(out["result"]))
