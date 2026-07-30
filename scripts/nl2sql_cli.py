#!/usr/bin/env python
"""
nl2sql_cli — NL2SQL 命令行入口。

用法：
    # 单条问题
    uv run python scripts/nl2sql_cli.py "各矿井精煤灰分排名"

    # 交互模式（无参数）
    uv run python scripts/nl2sql_cli.py

    # 显示 JSON 输出
    uv run python scripts/nl2sql_cli.py --json "最近30天销售额趋势"

    # 限制结果行数
    uv run python scripts/nl2sql_cli.py --max-rows 5 "告警最多的10个传感器"

交互模式命令：
    :q / :quit / exit  退出
    :help              显示帮助
    :sql               显示上一次生成的 SQL
    :json              切换 JSON/人类可读输出
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 确保 src/ 在 import 路径上（项目已 uv pip install -e .，但保底）
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dg_nl2sql.engine import NL2SQLEngine, format_result_table  # noqa: E402


# ── 渲染器 ──────────────────────────────────────────────────────────────────

def render_human(out: dict, max_rows: int) -> None:
    """人类可读输出。"""
    print(f"\n问题: {out['question']}")
    if out.get("error"):
        print(f"错误: {out['error']}")
        return

    if out.get("sql"):
        print("SQL:")
        for line in out["sql"].splitlines():
            print(f"  {line}")

    result = out.get("result")
    if result:
        rc = result.get("row_count", 0)
        suffix = " (已截断)" if result.get("truncated") else ""
        print(f"\n结果 ({rc} 行){suffix}:")
        print(format_result_table(result))
    else:
        print("\n结果: (无)")

    lineage = out.get("lineage_explanation") or []
    if lineage:
        print("\n血缘:")
        for line in lineage:
            print(f"  {line}")


def render_json(out: dict) -> None:
    """JSON 输出（结构化结果 + 血缘）。"""
    payload = {
        "question": out["question"],
        "success": out.get("success", False),
        "sql": out.get("sql") or None,
        "error": out.get("error") or None,
        "row_count": out.get("row_count", 0),
        "lineage_explanation": out.get("lineage_explanation") or [],
    }
    if out.get("result"):
        payload["result"] = {
            "columns": out["result"].get("columns", []),
            "rows": out["result"].get("rows", []),
            "row_count": out["result"].get("row_count", 0),
            "truncated": out["result"].get("truncated", False),
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


# ── REPL ────────────────────────────────────────────────────────────────────

HELP_TEXT = """\
交互模式命令：
  :q / :quit / exit   退出
  :help               显示本帮助
  :sql <问题>         只生成 SQL 不执行
  :json <问题>        JSON 格式输出
  <任何文本>          作为问题执行 NL2SQL
"""


def repl(engine: NL2SQLEngine, max_rows: int, fmt: str) -> None:
    print("NL2SQL 交互模式（输入 :help 查看命令，:q 退出）")
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return
        if not line:
            continue
        cmd = line.lower()
        if cmd in {":q", ":quit", "exit", "quit"}:
            print("bye")
            return
        if cmd in {":help", ":h", "help"}:
            print(HELP_TEXT)
            continue
        if line.lower().startswith(":json "):
            out = engine.ask(line[6:].strip())
            render_json(out)
            continue
        if line.lower().startswith(":sql "):
            out = engine.ask(line[5:].strip())
            print(out.get("sql") or out.get("error") or "(无)")
            continue
        # 默认：作为问题执行
        out = engine.ask(line)
        if fmt == "json":
            render_json(out)
        else:
            render_human(out, max_rows)


# ── CLI 主流程 ──────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nl2sql_cli",
        description="NL2SQL CLI — 自然语言问题 -> SQL -> DuckDB 执行 -> 血缘解释",
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="自然语言问题（不提供则进入交互模式）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出（默认人类可读）",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=50,
        help="返回结果最大行数（默认 50）",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="覆盖默认 LLM 模型名（也可通过环境变量 NL2SQL_MODEL 配置）",
    )
    args = parser.parse_args(argv)

    # 构造 engine（按需覆盖模型）
    if args.model:
        from dg_nl2sql.llm_client import LLMClient
        engine = NL2SQLEngine(llm_client=LLMClient(model=args.model))
    else:
        engine = NL2SQLEngine()

    fmt = "json" if args.json else "human"

    if args.question is None:
        # 交互模式
        try:
            repl(engine, args.max_rows, fmt)
        except RuntimeError as e:
            print(f"启动失败: {e}", file=sys.stderr)
            return 2
        return 0

    # 单条问题
    try:
        out = engine.ask(args.question)
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"执行失败: {e}", file=sys.stderr)
        return 1

    if fmt == "json":
        render_json(out)
    else:
        render_human(out, args.max_rows)

    return 0 if out.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
