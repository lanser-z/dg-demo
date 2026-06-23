#!/usr/bin/env python3
"""
Build dimension tables (dim_mine, dim_customer, dim_material) from DWD sources.
Writes to data/lakehouse/dwd/_dimensions/ as Delta Lake.
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from deltalake.writer import write_deltalake

# Project root
ROOT = Path(__file__).parent.parent
DIM_ROOT = ROOT / "data" / "lakehouse" / "dwd" / "_dimensions"


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

    # Read PI tags - mine field
    pi_files = list((ROOT / "data/lakehouse/dwd/pi_system/dwd_tags/").glob("*.parquet"))
    pi_df = pq.read_table(str(pi_files[0])).to_pandas()
    pi_mines = (
        pi_df[["mine"]]
        .dropna(subset=["mine"])
        .drop_duplicates(subset=["mine"])
        .rename(columns={"mine": "mine_code"})
    )
    pi_mines["pi_mine_field"] = pi_mines["mine_code"]

    # Read LIMS samples - MINE_CODE and MINE_NAME
    lims_files = list((ROOT / "data/lakehouse/dwd/lims/dwd_samples/").glob("*.parquet"))
    lims_df = pq.read_table(str(lims_files[0])).to_pandas()
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

    kna1_files = list((ROOT / "data/lakehouse/dwd/sap_erp/dwd_kna1/").glob("*.parquet"))
    df = pq.read_table(str(kna1_files[0])).to_pandas()

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

    vbap_files = list((ROOT / "data/lakehouse/dwd/sap_erp/dwd_vbap/").glob("*.parquet"))
    df = pq.read_table(str(vbap_files[0])).to_pandas()

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
