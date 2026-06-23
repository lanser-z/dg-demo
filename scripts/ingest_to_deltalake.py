"""
Parquet 数据入湖到 Delta Lake。
按数据域和层次组织：ods / dwd / dwa

Delta Lake 表存储在本地 data/lakehouse/，通过 mc 同步到 MinIO。

用法：
    uv run python scripts/ingest_to_deltalake.py [--layer ods|dwd|dwa|all]
"""
import argparse
import glob
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from deltalake.writer import write_deltalake
from deltalake import DeltaTable

# 基础清洗逻辑委托给 dg_education.cleaning（单一真相源，notebook 与 CLI 共享）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from dg_education.cleaning import clean_basic  # noqa: E402

# 本地 Lakehouse 根目录（Delta Lake 原生支持本地文件系统）
LAKEHOUSE_ROOT = "/home/szs/Playground/dg-demo/data/lakehouse"
# 模拟数据根目录
DATA_ROOT = "/home/szs/Playground/dg-demo/data/historical"


# ============================================================
# ODS 层定义
# ============================================================
ODS_TABLES = {
    "sap_erp/kna1": {
        "files": f"{DATA_ROOT}/sap_erp/kna1.parquet",
        "partition_by": [],
    },
    "sap_erp/vbak": {
        "files": f"{DATA_ROOT}/sap_erp/vbak_year=*.parquet",
        "partition_by": ["year"],
    },
    "sap_erp/vbap": {
        "files": f"{DATA_ROOT}/sap_erp/vbap_year=*.parquet",
        "partition_by": ["year"],
    },
    "pi_system/tags": {
        "files": f"{DATA_ROOT}/pi_system/tags_year=*_month=*.parquet",
        "partition_by": ["year", "month"],
    },
    "lims/samples": {
        "files": f"{DATA_ROOT}/lims/samples_year=*.parquet",
        "partition_by": ["year"],
    },
    "oa/doc_flow": {
        "files": f"{DATA_ROOT}/oa/doc_flow_year=*.parquet",
        "partition_by": ["year"],
    },
}


# ============================================================
# DWD 层定义（清洗规则）
# ============================================================
DWD_TABLES = {
    "sap_erp/dwd_vbak": {
        "source": "sap_erp/vbak",
        "description": "销售订单清洗：去空值、去重复、NETWR标准化",
    },
    "sap_erp/dwd_vbap": {
        "source": "sap_erp/vbap",
        "description": "行项清洗：过滤 MATNR 为空、NETWR≤0",
    },
    "sap_erp/dwd_kna1": {
        "source": "sap_erp/kna1",
        "description": "客户主数据：过滤 NAME1/STCD1 为空，KUNNR 补零至10位",
    },
    "pi_system/dwd_tags": {
        "source": "pi_system/tags",
        "description": "PI数据：过滤 status=-1、value 超 [0,10000] 范围",
    },
    "lims/dwd_samples": {
        "source": "lims/samples",
        "description": "LIMS：过滤 SAMPLE_ID/AD 为空、AD<0",
    },
    "oa/dwd_doc_flow": {
        "source": "oa/doc_flow",
        "description": "OA流：过滤 FLOW_TYPE/APPLY_DATE 为空",
    },
}


# ============================================================
# 工具函数
# ============================================================

def extract_partitions(path: str) -> dict:
    """从文件路径中提取 year/month 分区字段"""
    parts = {}
    for m in re.finditer(r"(year|month)=(\d+)", path):
        parts[m.group(1)] = int(m.group(2))
    return parts


def read_parquet_with_partitions(path: str) -> pd.DataFrame:
    """读取 parquet 并补充分区列"""
    parts = extract_partitions(path)
    df = pq.read_table(path).to_pandas()
    for col, val in parts.items():
        if col not in df.columns:
            df[col] = val
    return df


def write_delta(table_key: str, df: pd.DataFrame, partition_by: list):
    """写入 Delta Lake 表（本地文件系统）"""
    table_uri = os.path.join(LAKEHOUSE_ROOT, table_key)
    os.makedirs(os.path.dirname(table_uri), exist_ok=True)
    df = df.where(pd.notnull(df), None)
    write_deltalake(
        table_uri,
        df,
        partition_by=partition_by if partition_by else None,
        mode="overwrite",
    )


def read_delta(table_key: str) -> pd.DataFrame:
    """读取 Delta Lake 表"""
    table_uri = os.path.join(LAKEHOUSE_ROOT, table_key)
    dt = DeltaTable(table_uri)
    return dt.to_pandas()


def delta_stats(table_key: str):
    """返回 Delta 表文件数和大小（MB）"""
    table_uri = os.path.join(LAKEHOUSE_ROOT, table_key)
    try:
        # 通过 _delta_log 目录统计
        log_dir = os.path.join(table_uri, "_delta_log")
        parquet_files = []
        for root, _, files in os.walk(table_uri):
            for f in files:
                if f.endswith(".parquet"):
                    parquet_files.append(os.path.join(root, f))
        total_size = sum(os.path.getsize(f) for f in parquet_files)
        return len(parquet_files), total_size / 1024 / 1024
    except Exception:
        return 0, 0


def _clean(source: str, df: pd.DataFrame) -> pd.DataFrame:
    """应用 DWD 清洗规则（委托 dg_education.cleaning.clean_basic，单一真相源）。"""
    return clean_basic(source, df)


# ============================================================
# 入湖函数
# ============================================================

def ingest_ods():
    """ODS 层入湖：原始 Parquet → Delta Lake"""
    print("\n" + "=" * 60)
    print("📥 ODS 层入湖：Parquet → Delta Lake")
    print("=" * 60)

    for table_key, cfg in ODS_TABLES.items():
        files = sorted(glob.glob(cfg["files"]))
        if not files:
            print(f"  ⚠️  未找到: {cfg['files']}")
            continue

        print(f"\n▶ {table_key}")
        print(f"  原始: {len(files)} 个文件")

        # 读取第一个文件（或拼接小表，大表只读一个示意）
        if len(files) == 1:
            df = read_parquet_with_partitions(files[0])
        else:
            # 大数据表只读第一个文件作为示例
            df = read_parquet_with_partitions(files[0])
            print(f"  ⚡ 大数据表，仅读取第一个文件 {os.path.basename(files[0])} 作为示例")

        print(f"  行数: {len(df):,}")

        # 写入 Delta Lake
        write_delta(f"ods/{table_key}", df, cfg["partition_by"])

        cnt, size = delta_stats(f"ods/{table_key}")
        print(f"  ✅ Delta Lake: {cnt} files, {size:.1f} MB")

    print(f"\n✅ ODS 层完成: {LAKEHOUSE_ROOT}/ods/")


def ingest_dwd():
    """DWD 层入湖：清洗后写入"""
    print("\n" + "=" * 60)
    print("🧹 DWD 层入湖：数据清洗")
    print("=" * 60)

    for table_key, cfg in DWD_TABLES.items():
        print(f"\n▶ {table_key}")
        print(f"  规则: {cfg['description']}")

        try:
            src_df = read_delta(f"ods/{cfg['source']}")
        except Exception as e:
            print(f"  ⚠️  跳过（ODS 源表不存在）: {e}")
            continue

        before = len(src_df)
        df = _clean(cfg["source"], src_df)
        after = len(df)
        dropped = before - after
        pct = dropped / before * 100 if before > 0 else 0

        print(f"  {before:,} → {after:,} 行 (剔除 {dropped:,} 行, {pct:.1f}%)")
        write_delta(f"dwd/{table_key}", df, [])
        cnt, size = delta_stats(f"dwd/{table_key}")
        print(f"  ✅ Delta Lake: {cnt} files, {size:.1f} MB")

    print(f"\n✅ DWD 层完成: {LAKEHOUSE_ROOT}/dwd/")


def ingest_dwa():
    """DWA 层入湖：汇总宽表（打印计划，不实际执行）"""
    print("\n" + "=" * 60)
    print("📊 DWA 层入湖：业务汇总宽表")
    print("=" * 60)

    dwa_tables = [
        ("sap_erp/dwa_sales_daily", "每日销售汇总（金额/订单数/客户数）"),
        ("pi_system/dwa_tag_alarm", "传感器告警汇总（按矿井/工作面）"),
        ("lims/dwa_coal_quality",  "煤质月汇总（灰分/硫分/发热量均值）"),
    ]

    for table_key, desc in dwa_tables:
        print(f"\n▶ {table_key}")
        print(f"  描述: {desc}")
        print(f"  ℹ️  需通过 Spark SQL 计算后写入 Delta Lake")
        print(f"  目录: {LAKEHOUSE_ROOT}/dwa/{table_key}/")

    print(f"\n✅ DWA 层规划完成")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Parquet 入湖 Delta Lake")
    parser.add_argument("--layer", default="all",
                        choices=["ods", "dwd", "dwa", "all"])
    args = parser.parse_args()

    t0 = time.time()
    print(f"\n🚀 Delta Lake 入湖开始")
    print(f"   Lakehouse: {LAKEHOUSE_ROOT}")

    if args.layer in ("ods", "all"):
        ingest_ods()
    if args.layer in ("dwd", "all"):
        ingest_dwd()
    if args.layer in ("dwa", "all"):
        ingest_dwa()

    print(f"\n✅ 入湖完成，耗时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
