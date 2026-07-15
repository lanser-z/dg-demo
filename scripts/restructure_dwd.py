"""
restructure_dwd.py — Phase 2 / Background §6.11 主题域 DWD 重组

把 `data/lakehouse/dwd/{system}/`（system-分区）dual-write 到
`data/lakehouse/dwd/{subject}/`（subject-分区），保留旧 system-分区不变。

表-主题映射 (canonical)：
    sap_erp/dwd_vbak     -> sales/dwd_vbak
    sap_erp/dwd_vbap     -> sales/dwd_vbap
    sap_erp/dwd_kna1     -> sales/dwd_kna1
    pi_system/dwd_tags   -> production/dwd_tags
    lims/dwd_samples     -> coal_quality/dwd_samples
    oa/dwd_doc_flow      -> finance/dwd_doc_flow

维度表 `dwd/_dimensions/{dim_mine,dim_customer,dim_material}` 不动（共享维度全局可用）。

CLI：
    uv run python scripts/restructure_dwd.py             # 默认 dual 模式
    uv run python scripts/restructure_dwd.py --dry-run   # 仅打印计划
    uv run python scripts/restructure_dwd.py --mode=replace  # 删旧目录（演示阶段不用）

输出：
    4 个新主题目录，6 张 Delta Lake 表，与旧 system-分区数据完全一致。
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

import pandas as pd
from deltalake import DeltaTable
from deltalake.writer import write_deltalake

LAKEHOUSE_ROOT = Path("/home/szs/Playground/dg-demo/data/lakehouse")
DWD_ROOT = LAKEHOUSE_ROOT / "dwd"

# ── 表-主题映射（6 张 DWD 表 → 4 个主题目录） ─────────────────────────
SUBJECT_MAP: dict[str, str] = {
    "sap_erp/dwd_vbak": "sales/dwd_vbak",
    "sap_erp/dwd_vbap": "sales/dwd_vbap",
    "sap_erp/dwd_kna1": "sales/dwd_kna1",
    "pi_system/dwd_tags": "production/dwd_tags",
    "lims/dwd_samples": "coal_quality/dwd_samples",
    "oa/dwd_doc_flow": "finance/dwd_doc_flow",
}

SUBJECT_DESCRIPTIONS: dict[str, str] = {
    "sales/dwd_vbak": "SAP 销售订单抬头清洗表（主题：销售）",
    "sales/dwd_vbap": "SAP 销售订单行项目清洗表（主题：销售）",
    "sales/dwd_kna1": "SAP 客户主数据清洗表（主题：销售）",
    "production/dwd_tags": "PI System 时序标签清洗表（主题：生产）",
    "coal_quality/dwd_samples": "LIMS 样品化验清洗表（主题：煤质）",
    "finance/dwd_doc_flow": "OA 文档流清洗表（主题：财务）",
}

log = logging.getLogger("restructure_dwd")


def _read_old_delta(src_path: Path) -> pd.DataFrame:
    """从旧 system-分区读 Delta Lake 表 → DataFrame。"""
    if not src_path.is_dir():
        raise FileNotFoundError(f"旧 DWD 表不存在: {src_path}")
    dt = DeltaTable(str(src_path))
    return dt.to_pandas()


def dual_write(src_key: str, dst_key: str, *, dry_run: bool = False) -> int:
    """
    把 src_key 指向的旧 DWD 表写到 dst_key 指向的新主题目录。
    返回写入行数；dry_run 时返回 0。
    """
    src_path = DWD_ROOT / src_key
    dst_path = DWD_ROOT / dst_key
    log.info("▶ %s  →  %s", src_key, dst_key)

    if dry_run:
        try:
            df_peek = _read_old_delta(src_path)
            n_rows = len(df_peek)
        except Exception as e:
            n_rows = -1
            log.warning("  dry-run 无法读取源表: %s", e)
        print(f"  [DRY-RUN] 将写入 {n_rows:,} 行到 {dst_path}")
        return 0

    df = _read_old_delta(src_path)
    n_rows = len(df)
    write_deltalake(
        str(dst_path),
        df,
        mode="overwrite",
    )
    cnt, size_mb = _delta_stats(dst_path)
    log.info("  ✅ %d 行, %d parquet files, %.1f MB", n_rows, cnt, size_mb)
    print(f"  ✅ {n_rows:,} 行, {cnt} parquet files, {size_mb:.1f} MB")
    return n_rows


def _delta_stats(table_path: Path) -> tuple[int, float]:
    """统计 Delta Lake 表的 parquet 文件数 + 总大小 (MB)。"""
    parquet_files = [
        str(p) for p in table_path.rglob("*.parquet")
    ]
    total = sum(Path(p).stat().st_size for p in parquet_files)
    return len(parquet_files), total / 1024 / 1024


def replace_old(new_key: str, old_key: str) -> None:
    """演示阶段不用。`--mode=replace` 时把旧 system-分区替换为新主题目录（6.12 才用）。"""
    new_path = DWD_ROOT / new_key
    old_path = DWD_ROOT / old_key
    if old_path.exists():
        shutil.rmtree(old_path)
    new_path.rename(old_path)
    log.info("REPLACE: %s → %s", new_path, old_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2 / 6.11 — DWD 主题域重组 (dual-write 模式)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印计划，不实际写文件",
    )
    parser.add_argument(
        "--mode",
        choices=["dual", "replace"],
        default="dual",
        help="dual: 保留旧 system-分区, 仅写新主题目录 (默认); "
             "replace: 删旧 system-分区, 新主题目录改名 (6.12 才用)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    log.info("lakehouse root: %s", LAKEHOUSE_ROOT)
    log.info("mode: %s%s", args.mode, " (DRY-RUN)" if args.dry_run else "")

    if not DWD_ROOT.is_dir():
        log.error("DWD 目录不存在: %s", DWD_ROOT)
        return 1

    print()
    print("=" * 60)
    print("🚀 DWD 主题域重组 (Phase 2 / 6.11)")
    print("=" * 60)

    total_rows = 0
    failed: list[str] = []
    for src_key, dst_key in SUBJECT_MAP.items():
        try:
            n = dual_write(src_key, dst_key, dry_run=args.dry_run)
            total_rows += n
        except Exception as e:
            log.exception("❌ %s → %s 失败: %s", src_key, dst_key, e)
            failed.append(src_key)
            print(f"  ❌ 失败: {e}")

    if args.mode == "replace" and not args.dry_run:
        log.warning("--mode=replace: 删旧 system-分区并将新主题目录改名")
        reverse = {v: k for k, v in SUBJECT_MAP.items()}
        for new_key, old_key in reverse.items():
            replace_old(new_key, old_key)
        print("REPLACE 完成：旧 system-分区已被新主题目录覆盖")

    print()
    print("=" * 60)
    print("✅ 重组汇总")
    print("=" * 60)
    print(f"  表数: {len(SUBJECT_MAP) - len(failed)}/{len(SUBJECT_MAP)}")
    if not args.dry_run:
        print(f"  写入行数: {total_rows:,}")
    print(f"  失败: {len(failed)}")
    for f in failed:
        print(f"    - {f}")

    dim_root = DWD_ROOT / "_dimensions"
    if dim_root.is_dir():
        dim_tables = sorted(p.name for p in dim_root.iterdir() if p.is_dir())
        print(f"  _dimensions 保留: {dim_tables}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
