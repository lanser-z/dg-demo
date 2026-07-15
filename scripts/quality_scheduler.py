"""
定时质量监控调度器 — Background §6.10 升级入口

- 默认守护模式：APScheduler `BlockingScheduler` + `CronTrigger(hour=8, minute=30)` 每日跑
- `--run-once` 模式：单次执行后退出
- 写 SQLite `data/quality_scores.db` 时序表
- 阈值 < 70 触发 `data/quality_alerts.json` + console warning
- matplotlib 5 系统折线 → `data/quality_trend.png`
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
for _p in (str(SRC_DIR), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dg_platform.quality_checkpoint import (  # noqa: E402
    QualityCheckpoint,
    CheckpointResult,
    SYSTEM_TABLE_PATHS,
)

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "quality_scores.db"
ALERTS_PATH = DATA_DIR / "quality_alerts.json"
TREND_PNG = DATA_DIR / "quality_trend.png"

ALERT_THRESHOLD = float(os.environ.get("CHECKPOINT_THRESHOLD", "70"))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("quality_scheduler")


def _init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quality_scores (
                run_date   TEXT    NOT NULL,
                system     TEXT    NOT NULL,
                "table"    TEXT    NOT NULL,
                score      REAL    NOT NULL,
                grade      TEXT    NOT NULL,
                passed     INTEGER NOT NULL,
                failed     INTEGER NOT NULL,
                duration_s REAL    NOT NULL,
                PRIMARY KEY (run_date, system, "table")
            )
            """
        )
        conn.commit()


def _write_scores(db_path: Path, results: List[CheckpointResult], run_date: str) -> int:
    rows = [
        (
            run_date,
            r.system,
            r.table,
            float(r.score),
            r.grade,
            int(r.passed),
            int(r.failed),
            float(r.duration_s),
        )
        for r in results
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO quality_scores
                (run_date, system, "table", score, grade, passed, failed, duration_s)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    return len(rows)


def _write_alert(alerts_path: Path, system: str, score: float, grade: str) -> None:
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    alerts: list = []
    if alerts_path.exists():
        try:
            alerts = json.loads(alerts_path.read_text(encoding="utf-8") or "[]")
        except (json.JSONDecodeError, OSError):
            alerts = []
    alerts.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "system": system,
            "score": float(score),
            "grade": grade,
        }
    )
    alerts_path.write_text(
        json.dumps(alerts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _maybe_alert(result: CheckpointResult) -> bool:
    if result.score < ALERT_THRESHOLD:
        log.warning(
            "quality_alert system=%s table=%s score=%.1f grade=%s",
            result.system, result.table, result.score, result.grade,
        )
        _write_alert(ALERTS_PATH, result.system, result.score, result.grade)
        return True
    return False


def query_history(days: int = 30) -> pd.DataFrame:
    """Read recent ``days`` of history from SQLite, return DataFrame.

    Columns: ``run_date, system, table, score, grade, passed, failed, duration_s``.
    Empty DataFrame (with correct columns) if no data.
    """
    if not DB_PATH.exists():
        return pd.DataFrame(
            columns=["run_date", "system", "table", "score", "grade", "passed", "failed", "duration_s"]
        )
    cutoff = (
        datetime.now() - pd.Timedelta(days=days)
    ).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(
            'SELECT run_date, system, "table", score, grade, passed, failed, duration_s '
            'FROM quality_scores WHERE run_date >= ? ORDER BY run_date, system, "table"',
            conn,
            params=(cutoff,),
        )


def plot_trend_lines(days: int = 30, out_path: Optional[Path] = None) -> Optional[Path]:
    """Render a 5-system trend line chart, save PNG, return path.

    Returns ``None`` if history is empty (skips plot).
    """
    out_path = Path(out_path) if out_path is not None else TREND_PNG

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    df = query_history(days=days)
    if df.empty:
        log.info("quality_trend: no history yet, skipping")
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    for system, group in df.groupby("system"):
        ts = pd.to_datetime(group["run_date"])
        ax.plot(ts, group["score"], marker="o", label=system)
    ax.set_ylim(0, 100)
    ax.axhline(ALERT_THRESHOLD, color="red", linestyle="--", linewidth=1, label=f"threshold={ALERT_THRESHOLD}")
    ax.set_xlabel("date")
    ax.set_ylabel("quality score")
    ax.set_title(f"Quality Score Trend (last {days} days)")
    ax.legend(loc="lower left")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    log.info("quality_trend: saved %s (%d rows)", out_path, len(df))
    return out_path


def run_all_systems(
    db_path: Path = DB_PATH,
    alerts_path: Path = ALERTS_PATH,
) -> List[CheckpointResult]:
    """Iterate 5 systems × N tables, run Checkpoint, write DB, trigger alerts."""
    t0 = time.time()
    run_date = datetime.now().strftime("%Y-%m-%d")
    _init_db(db_path)
    results: List[CheckpointResult] = []
    for system, tables in SYSTEM_TABLE_PATHS.items():
        for table in tables:
            log.info("checkpoint: %s.%s", system, table)
            try:
                r = QualityCheckpoint(system, table).run()
            except Exception as exc:
                log.exception("checkpoint crashed: %s.%s: %s", system, table, exc)
                continue
            results.append(r)
            _maybe_alert(r)
    written = _write_scores(db_path, results, run_date)
    log.info(
        "✅ quality check done: %d systems checked, %d rows in %ss",
        len(SYSTEM_TABLE_PATHS), written, round(time.time() - t0, 1),
    )
    return results


def _daemon() -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        run_all_systems,
        trigger=CronTrigger(hour=8, minute=30),
        id="quality_daily",
        name="quality_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    def _handle_sigint(signum, frame):
        log.info("SIGINT received, shutting down")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    log.info("scheduler started: quality_daily @ 08:30 Asia/Shanghai")
    print("scheduler started, next run: 08:30 (Ctrl+C to exit)", flush=True)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality monitoring scheduler (Background §6.10)")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    if args.run_once:
        results = run_all_systems()
        png = plot_trend_lines()
        if png is not None:
            print(f"trend chart: {png}")
        return 0

    _daemon()
    return 0


if __name__ == "__main__":
    sys.exit(main())
