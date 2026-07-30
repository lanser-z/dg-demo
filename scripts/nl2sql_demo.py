#!/usr/bin/env python
"""
nl2sql_demo — NL2SQL 端到端批量测试。

用法：
    uv run python scripts/nl2sql_demo.py

8 个测试问题覆盖多场景（单表聚合 / 业务术语消解 / Top-N / 时间筛选 / 跨系统歧义 / 简单计数 / 多指标对比）。

退出码：始终 0（单题失败不中断整个测试）。
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path
from typing import Any

# 确保 src/ 在 import 路径上
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dg_nl2sql.engine import NL2SQLEngine, format_result_table  # noqa: E402


# ── 8 个测试问题（按场景分组）────────────────────────────────────────────────

TEST_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": 1,
        "scenario": "单表聚合 - 煤种统计",
        "question": "各煤种的样品数量和平均热值",
        "expect": "返回 ~5 行（SAMPLE_TYPE 维度），SUM/AVG 聚合成功",
    },
    {
        "id": 2,
        "scenario": "业务术语消解 - 精煤灰分",
        "question": "各矿井精煤的灰分排名",
        "expect": "依赖 glossary 映射 SAMPLE_TYPE='精煤' + avg_ash_content",
    },
    {
        "id": 3,
        "scenario": "Top-N 排序 - 传感器告警",
        "question": "告警次数最多的10个传感器",
        "expect": "dwa_tag_alarm GROUP BY tag ORDER BY COUNT DESC LIMIT 10",
    },
    {
        "id": 4,
        "scenario": "时间筛选 - 月度煤质",
        "question": "2022年1月的煤质数据",
        "expect": "dwa_coal_quality month='2022-01'",
    },
    {
        "id": 5,
        "scenario": "聚合统计 - 矿井平均灰分",
        "question": "各矿井的平均灰分",
        "expect": "GROUP BY mine + AVG(avg_ash_content)",
    },
    {
        "id": 6,
        "scenario": "跨系统歧义 - 数据孤岛识别",
        "question": "销售订单对应的煤质化验数据",
        # 销售在 sap_erp，煤质在 lims，无字面共享列
        # 期望 LLM 返回 "ERROR: 无法跨系统 JOIN" → 视为 PASS
        "expect": "LLM 应返回 ERROR: 无法跨系统 JOIN（正确识别数据孤岛）",
        "is_cross_system": True,
    },
    {
        "id": 7,
        "scenario": "简单计数 - 销售记录总数",
        "question": "总共有多少条销售记录",
        "expect": "dwa_sales_daily COUNT(*)",
    },
    {
        "id": 8,
        "scenario": "多指标 - 销售额和产量对比",
        "question": "各矿井的销售额和产量对比",
        "expect": "通常需 dwa_sales_daily + dwa_sales_production 联合",
    },
]


# ── 判定逻辑 ────────────────────────────────────────────────────────────────

# 跨系统无法 JOIN 的提示关键字（命中其一即视为正确识别）
CROSS_SYSTEM_HINTS = (
    "无法跨系统",
    "无字面共享列",
    "无join路径",
    "无 join 路径",
    "无明显关联",
    "无法join",
    "无法 join",
    "数据孤岛",
    "跨系统join",
    "跨系统 join",
)


def is_cross_system_error(error: str | None) -> bool:
    """判定 error 字段是否表示正确识别了数据孤岛。"""
    if not error:
        return False
    e = error.lower()
    return any(hint.lower() in e for hint in CROSS_SYSTEM_HINTS)


def judge(test: dict, out: dict) -> tuple[str, str]:
    """判定 PASS/FAIL。

    Returns:
        (status, reason)  status ∈ {"PASS", "FAIL"}
    """
    success = bool(out.get("success"))
    error = out.get("error")
    sql = (out.get("sql") or "").strip()

    # 跨系统题特殊处理：正确识别数据孤岛也 PASS
    if test.get("is_cross_system") and is_cross_system_error(error):
        return "PASS", "正确识别数据孤岛（无法跨系统 JOIN）"

    # 常规判定
    if not success:
        return "FAIL", f"success=False; error={error}"

    if not sql:
        return "FAIL", "SQL 为空"

    # row_count >= 0 即认为通过（0 行也可接受，说明 SQL 语法正确且无错）
    return "PASS", f"row_count={out.get('row_count', 0)}"


# ── 单题渲染 ────────────────────────────────────────────────────────────────

def render_one(test: dict, out: dict, status: str, reason: str, elapsed: float) -> None:
    """打印单题报告。"""
    print(f"[{test['id']}/8] {test['question']}")
    print(f"  场景: {test['scenario']}")
    print(f"  耗时: {elapsed:.2f}s")

    sql = (out.get("sql") or "").strip()
    raw_sql = (out.get("raw_sql") or "").strip()
    error = out.get("error")

    if status == "PASS" and test.get("is_cross_system") and is_cross_system_error(error):
        # 跨系统题特殊输出
        print(f"  SQL/ERROR: {error}")
    elif sql:
        print("  SQL:")
        for line in sql.splitlines():
            print(f"    {line}")
    elif raw_sql:
        print("  原始 SQL（未执行）:")
        for line in raw_sql.splitlines():
            print(f"    {line}")
    else:
        print(f"  SQL/ERROR: {error or '(空)'}")

    # 结果
    result = out.get("result")
    if result:
        rc = result.get("row_count", 0)
        rows = result.get("rows") or []
        print(f"  结果 ({rc} 行):")
        if rows:
            # 限制只打印前 5 行
            preview = {
                "columns": result.get("columns") or [],
                "rows": rows[:5],
                "row_count": min(rc, 5),
                "truncated": rc > 5,
            }
            for line in format_result_table(preview).splitlines():
                print(f"    {line}")
            if rc > 5:
                print(f"    ... (还有 {rc - 5} 行)")
        else:
            print("    (空结果集)")
    else:
        print("  结果: (无执行结果)")

    # 血缘
    lineage = out.get("lineage_explanation") or []
    if lineage:
        print("  血缘:")
        for line in lineage[:3]:
            print(f"    {line}")
        if len(lineage) > 3:
            print(f"    ... (还有 {len(lineage) - 3} 条血缘)")

    # 状态
    icon = "✅" if status == "PASS" else "❌"
    print(f"  状态: {icon} {status} ({reason})")
    print()


# ── 主流程 ──────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 70)
    print("NL2SQL 端到端测试报告")
    print("=" * 70)
    print()

    engine = NL2SQLEngine()

    passed: list[int] = []
    failed: list[tuple[int, str]] = []
    total_start = time.time()

    for test in TEST_QUESTIONS:
        q = test["question"]
        t0 = time.time()
        out: dict[str, Any] = {
            "question": q,
            "sql": "",
            "raw_sql": "",
            "result": None,
            "row_count": 0,
            "lineage_explanation": [],
            "success": False,
            "error": None,
        }
        try:
            out = engine.ask(q)
        except KeyboardInterrupt:
            print(f"[{test['id']}/8] 中断")
            failed.append((test["id"], "KeyboardInterrupt"))
            break
        except Exception as e:  # noqa: BLE001
            tb = traceback.format_exc()
            out["error"] = f"{type(e).__name__}: {e}; traceback={tb.splitlines()[-1]}"
            out["success"] = False

        elapsed = time.time() - t0
        status, reason = judge(test, out)
        render_one(test, out, status, reason, elapsed)

        if status == "PASS":
            passed.append(test["id"])
        else:
            failed.append((test["id"], reason))

    total_elapsed = time.time() - total_start

    # ── 汇总 ──
    print("=" * 70)
    print("汇总")
    print("=" * 70)
    total = len(TEST_QUESTIONS)
    print(f"通过: {len(passed)}/{total} (题号: {passed or '无'})")
    if failed:
        print(f"失败: {len(failed)}/{total} (题号: [失败])")
        for tid, reason in failed:
            print(f"  [{tid}] {reason}")
    print(f"总耗时: {total_elapsed:.2f}s")
    print()

    # 验收门槛
    if len(passed) >= 5:
        print(f"✅ 验收通过（{len(passed)}/8 >= 5/8）")
    else:
        print(f"❌ 验收未通过（{len(passed)}/8 < 5/8）")
    print()

    # 始终退出 0（单题失败不中断）
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
