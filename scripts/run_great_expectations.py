"""
数据质量检测脚本 — GE 风格规则，pandas 执行引擎。
规则定义与 Great Expectations 规范一致，但执行层轻量化，适合演示。

用法：
    uv run python scripts/run_great_expectations.py [--system sap_erp|pi_system|lims|oa|all]
"""
import argparse
import json
import time
from datetime import datetime

import pandas as pd

DATA_ROOT = "/home/szs/Playground/dg-demo/data/historical"

SYSTEMS = {
    "sap_erp": {
        "vbak": f"{DATA_ROOT}/sap_erp/vbak_year=2022.parquet",
        "vbap": f"{DATA_ROOT}/sap_erp/vbap_year=2022.parquet",
        "kna1": f"{DATA_ROOT}/sap_erp/kna1.parquet",
    },
    "pi_system": {
        "tags": f"{DATA_ROOT}/pi_system/tags_year=2022_month=01.parquet",
    },
    "lims": {
        "samples": f"{DATA_ROOT}/lims/samples_year=2022.parquet",
    },
    "oa": {
        "doc_flow": f"{DATA_ROOT}/oa/doc_flow_year=2022.parquet",
    },
}


# ============================================================
# GE 风格规则定义（与 Great Expectations v1.x 规范一致）
# ============================================================
# 每个规则：("expectation_type", {kwargs})
# 执行引擎：pandas（本演示用，生产环境替换为 GE 执行引擎）

RULES = {
    "sap_erp": {
        "vbak": [
            ("expect_column_values_to_not_be_null",   {"column": "VBELN"}),
            ("expect_column_values_to_not_be_null",   {"column": "NETWR"}),
            ("expect_column_values_to_not_be_null",   {"column": "ERNAM"}),
            ("expect_column_values_to_not_be_null",   {"column": "KUNNR"}),
            ("expect_column_values_to_be_unique",     {"column": "VBELN"}),
            ("expect_column_values_to_be_between",   {"column": "NETWR", "min_value": 0}),
        ],
        "vbap": [
            ("expect_column_values_to_not_be_null",   {"column": "VBELN"}),
            ("expect_column_values_to_not_be_null",   {"column": "MATNR"}),
            ("expect_column_values_to_be_unique",     {"column": ("VBELN", "POSNR")}),
            ("expect_column_values_to_be_between",   {"column": "NETWR", "min_value": 0}),
        ],
        "kna1": [
            ("expect_column_values_to_not_be_null",   {"column": "KUNNR"}),
            ("expect_column_values_to_not_be_null",   {"column": "NAME1"}),
            ("expect_column_values_to_not_be_null",   {"column": "STCD1"}),
            ("expect_column_values_to_be_unique",     {"column": "KUNNR"}),
            ("expect_column_value_lengths_to_be_between", {"column": "STCD1", "min_value": 17, "max_value": 20}),
        ],
    },
    "pi_system": {
        "tags": [
            ("expect_column_values_to_not_be_null",   {"column": "tag"}),
            ("expect_column_values_to_not_be_null",   {"column": "value"}),
            ("expect_column_values_to_not_be_null",   {"column": "timestamp"}),
            ("expect_column_values_to_be_between",   {"column": "status", "min_value": 0}),
            ("expect_column_values_to_be_between",   {"column": "value", "min_value": 0, "max_value": 10000}),
        ],
    },
    "lims": {
        "samples": [
            ("expect_column_values_to_not_be_null",   {"column": "SAMPLE_ID"}),
            ("expect_column_values_to_not_be_null",   {"column": "AD"}),
            ("expect_column_values_to_not_be_null",   {"column": "VD"}),
            ("expect_column_values_to_not_be_null",   {"column": "全硫St"}),
            ("expect_column_values_to_be_unique",     {"column": "SAMPLE_ID"}),
            ("expect_column_values_to_be_between",   {"column": "AD", "min_value": 0, "max_value": 100}),
            ("expect_column_values_to_be_between",   {"column": "全硫St", "min_value": 0, "max_value": 10}),
        ],
    },
    "oa": {
        "doc_flow": [
            ("expect_column_values_to_not_be_null",   {"column": "FLOW_ID"}),
            ("expect_column_values_to_not_be_null",   {"column": "FLOW_TYPE"}),
            ("expect_column_values_to_not_be_null",   {"column": "INITIATOR"}),
            ("expect_column_values_to_be_between",   {"column": "AMOUNT", "min_value": 0}),
        ],
    },
}


# ============================================================
# GE 风格执行引擎（pandas 实现）
# ============================================================

def expect_column_values_to_not_be_null(df, column):
    total = len(df)
    null_count = df[column].isnull().sum()
    unexpected_pct = null_count / total * 100 if total > 0 else 0
    return {"success": null_count == 0, "unexpected_count": null_count, "unexpected_percent": unexpected_pct}


def expect_column_values_to_be_unique(df, column):
    """支持单列或列元组（组合唯一性）"""
    if isinstance(column, tuple):
        total = len(df)
        dup_count = df.duplicated(subset=list(column)).sum()
    else:
        total = len(df)
        dup_count = df[column].duplicated().sum()
    unexpected_pct = dup_count / total * 100 if total > 0 else 0
    return {"success": dup_count == 0, "unexpected_count": dup_count, "unexpected_percent": unexpected_pct}


def expect_column_values_to_be_between(df, column, min_value=None, max_value=None):
    total = len(df)
    col = df[column]
    mask = True
    if min_value is not None:
        mask = mask & (col >= min_value)
    if max_value is not None:
        mask = mask & (col <= max_value)
    unexpected_count = (~mask).sum()
    unexpected_pct = unexpected_count / total * 100 if total > 0 else 0
    return {"success": unexpected_count == 0, "unexpected_count": unexpected_count, "unexpected_percent": unexpected_pct}


def expect_column_value_lengths_to_be_between(df, column, min_value=None, max_value=None):
    total = len(df)
    col = df[column].astype(str)
    mask = True
    if min_value is not None:
        mask = mask & (col.str.len() >= min_value)
    if max_value is not None:
        mask = mask & (col.str.len() <= max_value)
    unexpected_count = (~mask).sum()
    unexpected_pct = unexpected_count / total * 100 if total > 0 else 0
    return {"success": unexpected_count == 0, "unexpected_count": unexpected_count, "unexpected_percent": unexpected_pct}


# GE 函数映射
GE_FUNCTIONS = {
    "expect_column_values_to_not_be_null": expect_column_values_to_not_be_null,
    "expect_column_values_to_be_unique": expect_column_values_to_be_unique,
    "expect_column_values_to_be_between": expect_column_values_to_be_between,
    "expect_column_value_lengths_to_be_between": expect_column_value_lengths_to_be_between,
}


def run_check(system: str, table: str, filepath: str):
    """对单表运行 GE 风格规则"""
    rules = RULES.get(system, {}).get(table, [])
    if not rules:
        return {"table": table, "error": "无规则", "passed": 0, "failed": 0,
                "total": 0, "pass_rate": 0, "score": 0, "grade": "?",
                "sample_note": "", "details": []}

    # 读取（采样 50 万行加速）
    MAX = 500_000
    df = pd.read_parquet(filepath)
    total_rows = len(df)
    df_sample = df.sample(n=min(len(df), MAX), random_state=42)
    note = f"（采样 {len(df_sample):,} 行，全量 {total_rows:,} 行）" if total_rows > MAX else f"（全量 {total_rows:,} 行）"

    results = []
    for exp_type, kwargs in rules:
        fn = GE_FUNCTIONS.get(exp_type)
        if not fn:
            results.append({"expectation_type": exp_type, "column": kwargs.get("column", "-"),
                           "success": False, "unexpected_count": -1, "unexpected_pct": -1,
                           "error": f"unknown expectation: {exp_type}"})
            continue
        try:
            result = fn(df_sample, **kwargs)
            results.append({
                "expectation_type": exp_type,
                "column": kwargs.get("column", str(kwargs.get("columns", "-"))),
                "success": result["success"],
                "unexpected_count": result["unexpected_count"],
                "unexpected_pct": round(result["unexpected_percent"], 3),
            })
        except Exception as e:
            results.append({
                "expectation_type": exp_type,
                "column": kwargs.get("column", "-"),
                "success": False,
                "unexpected_count": -1,
                "unexpected_pct": -1,
                "error": str(e),
            })

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    pass_rate = passed / total * 100 if total > 0 else 0

    return {
        "table": table,
        "sample_note": note,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(pass_rate, 1),
        "score": round(pass_rate, 1),
        "grade": "A" if pass_rate >= 95 else "B" if pass_rate >= 85 else "C" if pass_rate >= 70 else "D",
        "details": [r for r in results if not r["success"]],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", default="all",
                        choices=["sap_erp", "pi_system", "lims", "oa", "all"])
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    t0 = time.time()
    systems = SYSTEMS if args.system == "all" else {args.system: SYSTEMS[args.system]}

    all_results = {}

    print(f"\n{'='*60}")
    print(f"🔍 数据质量检测（GE 风格规则 / pandas 执行引擎）")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    for sys_name, tables in systems.items():
        print(f"\n{'='*60}")
        print(f"📦 {sys_name.upper()}")
        print(f"{'='*60}")

        sys_results = []
        for table, filepath in tables.items():
            print(f"\n▶ {table} ...", end=" ", flush=True)
            try:
                res = run_check(sys_name, table, filepath)
                sys_results.append(res)
                icon = {"A": "✅", "B": "🟡", "C": "🟠", "D": "🔴"}.get(res["grade"], "❓")
                print(f"[{res['grade']}] {res['pass_rate']}% "
                      f"({res['passed']}/{res['total']}) {res.get('sample_note', '')}")

                if res.get("details"):
                    for d in res["details"]:
                        uc = d["unexpected_count"]
                        up = d["unexpected_pct"]
                        err = f" → {d.get('error', '')}" if "error" in d else ""
                        print(f"   🔴 FAIL: {d['expectation_type']}({d['column']}) "
                              f"→ {uc:,} 异常 ({up:.2f}%){err}")
            except Exception as e:
                print(f"❌ {e}")
                import traceback; traceback.print_exc()
                sys_results.append({"table": table, "error": str(e), "passed": 0, "failed": 0,
                                   "total": 0, "pass_rate": 0, "score": 0, "grade": "?"})

        all_results[sys_name] = sys_results

    # 汇总
    print(f"\n{'='*60}")
    print(f"📊 全局质量评分汇总")
    print(f"{'='*60}")
    print(f"{'系统':<15} {'评分':>8} {'等级':>6} {'通过率':>10} {'失败':>8}")
    print("-" * 60)

    summary = []
    for sys_name, sys_results in all_results.items():
        total_p = sum(r.get("passed", 0) for r in sys_results)
        total_f = sum(r.get("failed", 0) for r in sys_results)
        total = total_p + total_f
        rate = total_p / total * 100 if total > 0 else 0
        grade = "A" if rate >= 95 else "B" if rate >= 85 else "C" if rate >= 70 else "D"
        summary.append({"system": sys_name, "score": round(rate, 1), "grade": grade,
                        "pass_rate": round(rate, 1), "failed": total_f})
        print(f"{sys_name:<15} {rate:>7.1f} {grade:>6} {rate:>9.1f}% {total_f:>8,}")

    avg = sum(s["score"] for s in summary) / len(summary) if summary else 0
    print("-" * 60)
    print(f"{'平均':<15} {avg:>7.1f}")

    print(f"\n✅ 检测完成，耗时 {time.time()-t0:.1f}s")

    if args.output_json:
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_avg_score": round(avg, 1),
            "results": all_results,
            "summary": summary,
        }
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📄 JSON 报告: {args.output_json}")


if __name__ == "__main__":
    main()
