#!/usr/bin/env python3
"""
Build dimension tables (dim_mine, dim_customer, dim_material) from DWD sources.
Writes to data/lakehouse/dwd/_dimensions/ as Delta Lake.
"""
import argparse
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from deltalake import DeltaTable
from deltalake.writer import write_deltalake

ROOT = Path(__file__).parent.parent
DIM_ROOT = ROOT / "data" / "lakehouse" / "dwd" / "_dimensions"

# DWD subject-分区路径（Delta Lake），与 ingest_to_deltalake.py --layer dwd 输出路径一致
DWD_SOURCE = {
    "production": ROOT / "data" / "lakehouse" / "dwd" / "production" / "dwd_tags",
    "coal_quality": ROOT / "data" / "lakehouse" / "dwd" / "coal_quality" / "dwd_samples",
    "sales_kna1": ROOT / "data" / "lakehouse" / "dwd" / "sales" / "dwd_kna1",
    "sales_vbap": ROOT / "data" / "lakehouse" / "dwd" / "sales" / "dwd_vbap",
}


def _read_dwd(path: Path) -> pd.DataFrame:
    """从 Delta Lake 目录读取 DataFrame（降级为 read_parquet 以兼容无 _delta_log 的情况）。"""
    try:
        dt = DeltaTable(str(path))
        return dt.to_pandas()
    except Exception:
        files = list(path.glob("*.parquet"))
        if files:
            return pq.read_table(str(files[0])).to_pandas()
        raise FileNotFoundError(f"DWD source not found: {path}")


def _write_delta(df: pd.DataFrame, path: Path):
    """Write a DataFrame as Delta Lake, overwriting existing data."""
    path.mkdir(parents=True, exist_ok=True)
    write_deltalake(
        str(path),
        df,
        mode="overwrite",
        partition_by=None,
    )
    print(f"  -> {path} ({len(df)} rows)")


def build_dim_mine():
    """Build dim_mine from PI dwd_tags and LIMS dwd_samples."""
    print("Building dim_mine...")

    # Read PI dwd_tags
    pi_df = _read_dwd(DWD_SOURCE["production"])
    pi_mines = (
        pi_df[["mine"]]
        .dropna(subset=["mine"])
        .drop_duplicates(subset=["mine"])
        .rename(columns={"mine": "mine_code"})
    )
    pi_mines["pi_mine_field"] = pi_mines["mine_code"]

    # Read LIMS dwd_samples
    lims_df = _read_dwd(DWD_SOURCE["coal_quality"])
    lims_mines = (
        lims_df[["MINE_CODE", "MINE_NAME"]]
        .dropna(subset=["MINE_CODE"])
        .drop_duplicates(subset=["MINE_CODE"])
        .rename(columns={"MINE_CODE": "mine_code", "MINE_NAME": "mine_name"})
    )
    lims_mines["lims_mine_field"] = lims_mines["mine_code"]

    # Merge PI and LIMS on mine_code
    merged = pi_mines.merge(lims_mines, on="mine_code", how="outer")
    merged["mine_name"] = merged["mine_name"].fillna(merged["mine_code"])
    merged["mine_type"] = "生产矿井"  # placeholder classification
    merged["sap_mine_field"] = merged["mine_code"]  # SAP mine field is the same code
    merged["pi_mine_field"] = merged["pi_mine_field"].fillna(merged["mine_code"])
    merged["lims_mine_field"] = merged["lims_mine_field"].fillna(merged["mine_code"])

    # Select and order final columns
    dim_mine = merged[[
        "mine_code", "mine_name", "mine_type",
        "sap_mine_field", "pi_mine_field", "lims_mine_field"
    ]].drop_duplicates(subset=["mine_code"]).sort_values("mine_code").reset_index(drop=True)

    _write_delta(dim_mine, DIM_ROOT / "dim_mine")


def build_dim_customer():
    """Build dim_customer from SAP KNA1."""
    print("Building dim_customer...")

    df = _read_dwd(DWD_SOURCE["sales_kna1"])

    dim_customer = (
        df[["KUNNR", "NAME1", "ORT01"]]
        .dropna(subset=["KUNNR"])
        .drop_duplicates(subset=["KUNNR"])
        .rename(columns={"KUNNR": "kunnr", "NAME1": "customer_name", "ORT01": "region"})
    )
    dim_customer["credit_level"] = "UNKNOWN"  # KNA1 has no credit_level field

    # Select and order final columns
    dim_customer = dim_customer[[
        "kunnr", "customer_name", "region", "credit_level"
    ]].sort_values("kunnr").reset_index(drop=True)

    _write_delta(dim_customer, DIM_ROOT / "dim_customer")


def build_dim_material():
    """Build dim_material from SAP VBAP MATNR.

    Note: MARA (material master) is not available in this demo environment.
    Using VBAP MATNR as the material source; mat_type and mat_desc are inferred.
    """
    print("Building dim_material...")

    df = _read_dwd(DWD_SOURCE["sales_vbap"])

    dim_material = (
        df[["MATNR"]]
        .dropna(subset=["MATNR"])
        .drop_duplicates(subset=["MATNR"])
        .rename(columns={"MATNR": "matnr"})
    )
    dim_material["mat_desc"] = dim_material["matnr"]  # no description source without MARA
    dim_material["mat_type"] = dim_material["matnr"].apply(
        lambda x: x[0:4] if isinstance(x, str) and len(x) >= 4 else "UNKNOWN"
    )

    dim_material = dim_material[[
        "matnr", "mat_desc", "mat_type"
    ]].sort_values("matnr").reset_index(drop=True)

    _write_delta(dim_material, DIM_ROOT / "dim_material")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build dimension tables")
    parser.add_argument(
        "--dimension",
        choices=["mine", "customer", "material", "all"],
        default="all",
        help="Which dimension to build (default: all)",
    )
    args = parser.parse_args()

    if args.dimension in ("mine", "all"):
        build_dim_mine()
    if args.dimension in ("customer", "all"):
        build_dim_customer()
    if args.dimension in ("material", "all"):
        build_dim_material()
