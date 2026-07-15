"""
QualityCheckpoint — Background §6.10 升级抽象

封装 `scripts/run_great_expectations.py` 的 GE 风格规则，输出结构化
``CheckpointResult`` 供调度器 + SQLite + 趋势图 + 告警直接消费。

复用 ``RULES`` 与 ``expect_*`` 函数，不重写规则引擎。
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from run_great_expectations import RULES, GE_FUNCTIONS, DATA_ROOT as _GE_DATA_ROOT  # noqa: E402


GRADE_THRESHOLDS: Tuple[Tuple[float, str], ...] = (
    (90.0, "A"),
    (80.0, "B"),
    (70.0, "C"),
    (0.0, "D"),
)


SYSTEM_TABLE_PATHS: Dict[str, Dict[str, str]] = {
    "sap_erp": {
        "vbak": "sap_erp/vbak_year=2022.parquet",
        "vbap": "sap_erp/vbap_year=2022.parquet",
        "kna1": "sap_erp/kna1.parquet",
    },
    "pi_system": {
        "tags": "pi_system/tags_year=2022_month=01.parquet",
    },
    "lims": {
        "samples": "lims/samples_year=2022.parquet",
    },
    "oa": {
        "doc_flow": "oa/doc_flow_year=2022.parquet",
    },
}


def _grade_for(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "D"


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@dataclass
class CheckpointResult:
    system: str
    table: str
    score: float
    grade: str
    passed: int
    failed: int
    duration_s: float
    report_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QualityCheckpoint:
    """对单 system × 单 table 跑一次 GE 风格规则集，输出 CheckpointResult。

    Parameters
    ----------
    system : str
        系统名，如 ``"sap_erp"``
    table : str
        表名，如 ``"vbak"``
    data_root : path-like, optional
        历史数据根目录；默认从 ``run_great_expectations.DATA_ROOT`` 继承
    report_dir : path-like, optional
        单表 JSON 报告目录；默认 ``data/quality_reports/``
    """

    _TABLE_PATHS: Dict[str, Dict[str, str]] = SYSTEM_TABLE_PATHS

    def __init__(
        self,
        system: str,
        table: str,
        data_root: Optional[str | Path] = None,
        report_dir: Optional[str | Path] = None,
    ) -> None:
        self.system = system
        self.table = table
        self.data_root = Path(data_root) if data_root is not None else Path(_GE_DATA_ROOT)
        self.report_dir = Path(report_dir) if report_dir is not None else Path("data/quality_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self) -> Path:
        rel = self._TABLE_PATHS.get(self.system, {}).get(self.table)
        if rel is None:
            raise FileNotFoundError(
                f"unknown system/table pair: {self.system}.{self.table}"
            )
        return self.data_root / rel

    def _run_pandas(self, filepath: Path) -> Tuple[int, int, List[Dict[str, Any]]]:
        rules = RULES.get(self.system, {}).get(self.table, [])
        if not rules:
            return 0, 0, []

        MAX = 500_000
        df = pd.read_parquet(filepath)
        df_sample = df.sample(n=min(len(df), MAX), random_state=42)

        details: List[Dict[str, Any]] = []
        passed = 0
        failed = 0
        for exp_type, kwargs in rules:
            fn = GE_FUNCTIONS.get(exp_type)
            entry: Dict[str, Any] = {
                "expectation_type": exp_type,
                "column": str(kwargs.get("column", kwargs.get("columns", "-"))),
            }
            if fn is None:
                entry.update(
                    success=False,
                    unexpected_count=-1,
                    unexpected_percent=-1.0,
                    error=f"unknown expectation: {exp_type}",
                )
                failed += 1
                details.append(entry)
                continue
            try:
                result = fn(df_sample, **kwargs)
                entry.update(
                    success=bool(result.get("success")),
                    unexpected_count=result.get("unexpected_count", -1),
                    unexpected_percent=round(result.get("unexpected_percent", -1.0), 3),
                )
                if entry["success"]:
                    passed += 1
                else:
                    failed += 1
            except Exception as exc:
                entry.update(
                    success=False,
                    unexpected_count=-1,
                    unexpected_percent=-1.0,
                    error=str(exc),
                )
                failed += 1
            details.append(entry)
        return passed, failed, details

    def run(self) -> CheckpointResult:
        t0 = time.time()
        try:
            filepath = self._resolve_path()
        except FileNotFoundError:
            return CheckpointResult(
                system=self.system,
                table=self.table,
                score=0.0,
                grade="D",
                passed=0,
                failed=0,
                duration_s=round(time.time() - t0, 3),
                report_path="",
            )

        try:
            passed, failed, details = self._run_pandas(filepath)
        except FileNotFoundError:
            return CheckpointResult(
                system=self.system,
                table=self.table,
                score=0.0,
                grade="D",
                passed=0,
                failed=0,
                duration_s=round(time.time() - t0, 3),
                report_path="",
            )
        except Exception:
            return CheckpointResult(
                system=self.system,
                table=self.table,
                score=0.0,
                grade="D",
                passed=0,
                failed=0,
                duration_s=round(time.time() - t0, 3),
                report_path="",
            )

        total = passed + failed
        score = (passed / total * 100) if total > 0 else 0.0
        grade = _grade_for(score)
        duration = time.time() - t0

        report_path = self.report_dir / f"{self.system}__{self.table}.json"
        report = {
            "system": self.system,
            "table": self.table,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "score": round(float(score), 2),
            "grade": grade,
            "passed": int(passed),
            "failed": int(failed),
            "total": int(total),
            "duration_s": round(float(duration), 3),
            "details": details,
        }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )

        return CheckpointResult(
            system=self.system,
            table=self.table,
            score=round(score, 2),
            grade=grade,
            passed=passed,
            failed=failed,
            duration_s=round(duration, 3),
            report_path=str(report_path),
        )
