"""Great Expectations scan wrapper for the educational notebook.

Wraps `scripts/run_great_expectations.py` as a Python API that returns
a parsed JSON dict. The notebook uses this instead of spawning shell
commands directly, so 小白 can `run_ge_scan()` and get a structured
result.

Why in-process import instead of subprocess?
- The CLI script uses numpy bool_/int64/float64 which fail to serialize
  with stdlib json.dump; doing the work in-process lets us normalize
  types after running rules.
- Avoids 2-3s subprocess startup overhead per scan.
- The CLI's RULES dict remains the single source of truth (we import it).
"""
from __future__ import annotations

import importlib.util
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Path to the CLI script (relative to this file)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CLI_SCRIPT = _REPO_ROOT / "scripts" / "run_great_expectations.py"

# Valid system names matching the CLI choices
VALID_SYSTEMS: tuple[str, ...] = ("sap_erp", "pi_system", "lims", "oa", "all")

# Lazy-loaded CLI module handle
_cli_module = None


def _load_cli_module():
    """Import the CLI script as a module (one-time)."""
    global _cli_module
    if _cli_module is not None:
        return _cli_module
    spec = importlib.util.spec_from_file_location("_ge_cli", str(_CLI_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _cli_module = mod
    return mod


def run_ge_scan(
    systems: list[str] | None = None,
    output_json: str | Path | None = None,
) -> dict[str, Any]:
    """Run the Great Expectations rules and return parsed JSON report.

    Args:
        systems: List of system names to scan (e.g. ['sap_erp', 'pi_system']).
            If None, scans all 4 systems. Currently only single-system or all
            are supported (matches CLI behavior).
        output_json: Optional path to write JSON report; if provided, the
            file is also created.

    Returns:
        Parsed dict with keys: timestamp, overall_avg_score, results, summary.

    Raises:
        FileNotFoundError: If the CLI script is not found.
        ValueError: If multiple specific systems are passed.
    """
    if not _CLI_SCRIPT.exists():
        raise FileNotFoundError(
            f"CLI script not found at {_CLI_SCRIPT}. "
            "Make sure you're running from the dg-demo repo root."
        )

    if systems is None or "all" in systems:
        system_arg = "all"
    elif len(systems) == 1:
        system_arg = systems[0]
    else:
        raise ValueError(
            f"CLI only supports single-system or all. Got: {systems}. "
            "Run multiple times if you need per-system reports."
        )

    cli = _load_cli_module()
    systems_to_scan = cli.SYSTEMS if system_arg == "all" else {system_arg: cli.SYSTEMS[system_arg]}

    t0 = time.time()
    all_results: dict[str, list[dict[str, Any]]] = {}
    for sys_name, tables in systems_to_scan.items():
        sys_results = []
        for table, filepath in tables.items():
            try:
                res = cli.run_check(sys_name, table, filepath)
                sys_results.append(_normalize_result(res))
            except Exception as e:
                sys_results.append({
                    "table": table,
                    "error": str(e),
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "pass_rate": 0,
                    "score": 0,
                    "grade": "?",
                    "sample_note": "",
                    "details": [],
                })
        all_results[sys_name] = sys_results

    summary = []
    for sys_name, sys_results in all_results.items():
        total_p = sum(r.get("passed", 0) for r in sys_results)
        total_f = sum(r.get("failed", 0) for r in sys_results)
        total = total_p + total_f
        rate = total_p / total * 100 if total > 0 else 0
        grade = "A" if rate >= 95 else "B" if rate >= 85 else "C" if rate >= 70 else "D"
        summary.append({
            "system": sys_name,
            "score": round(rate, 1),
            "grade": grade,
            "pass_rate": round(rate, 1),
            "failed": int(total_f),
        })

    avg = sum(s["score"] for s in summary) / len(summary) if summary else 0
    elapsed = round(time.time() - t0, 1)

    report = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "overall_avg_score": round(avg, 1),
        "results": all_results,
        "summary": summary,
    }

    if output_json is not None:
        import json
        json_path = Path(output_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def parse_ge_report(json_path: str | Path) -> dict[str, Any]:
    """Parse a GE scan JSON report from disk.

    Args:
        json_path: Path to JSON file produced by `run_ge_scan(output_json=...)`.

    Returns:
        Parsed dict with structure:
        {
            "timestamp": str,
            "overall_avg_score": float,
            "results": {system: [table_results]},
            "summary": [{system, score, grade, pass_rate, failed}]
        }
    """
    import json
    json_path = Path(json_path)
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_result(res: dict[str, Any]) -> dict[str, Any]:
    """Convert numpy/pandas scalars in a run_check result to native Python types."""
    out: dict[str, Any] = {}
    for k, v in res.items():
        out[k] = _to_native(v)
    return out


def _to_native(obj: Any) -> Any:
    """Recursively convert numpy/pandas scalars and Timestamps to native types."""
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    return obj
