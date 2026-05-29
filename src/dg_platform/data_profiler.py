"""
data_profiler — Parquet 数据探查模块

提供：
- profile_parquet(path): 单文件元数据（行数、列名、类型、大小）
- discover_partitions(path): 发现分区目录结构
- count_rows(path): 跨分区汇总行数
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


def profile_parquet(file_path: Path | str) -> dict:
    """
    探查单个 Parquet 文件，返回元数据字典。

    Returns:
        {
            "row_count": int,
            "column_names": list[str],
            "column_types": list[str],
            "file_size_mb": float,
            "file_path": str,
        }
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    pf = pq.ParquetFile(str(path))
    schema = pf.schema_arrow

    row_count = pf.metadata.num_rows
    column_names = [field.name for field in schema]
    column_types = [str(field.type) for field in schema]
    file_size_mb = path.stat().st_size / (1024 * 1024)

    return {
        "row_count": row_count,
        "column_names": column_names,
        "column_types": column_types,
        "file_size_mb": round(file_size_mb, 3),
        "file_path": str(path),
    }


def discover_partitions(base_path: Path | str) -> list[dict]:
    """
    发现目录下的分区结构。

    Parquet 分区格式示例：
        sap_erp/vbak_year=2022.parquet
        pi_system/tags_year=2023_month=06.parquet

    Returns:
        [
            {"partition_field": "year", "partition_value": "2022",
             "file_path": "...", "row_count": N, "size_mb": M},
            ...
        ]
    """
    path = Path(base_path)
    if not path.exists():
        raise FileNotFoundError(f"目录不存在: {path}")

    results = []
    for f in sorted(path.rglob("*.parquet")):
        parts = f.relative_to(path).parts[:-1]  # 去掉文件名，取分区目录
        row_count = pq.ParquetFile(str(f)).metadata.num_rows
        size_mb = f.stat().st_size / (1024 * 1024)

        if parts:
            # 解析分区字段，如 "year=2022" -> ("year", "2022")
            for part in parts:
                if "=" in part:
                    field, value = part.split("=", 1)
                    results.append({
                        "partition_field": field,
                        "partition_value": value,
                        "file_path": str(f),
                        "row_count": row_count,
                        "size_mb": round(size_mb, 3),
                    })
        else:
            # 非分区文件
            results.append({
                "partition_field": "",
                "partition_value": "",
                "file_path": str(f),
                "row_count": row_count,
                "size_mb": round(size_mb, 3),
            })

    return results


def count_rows(base_path: Path | str) -> int:
    """
    递归统计目录下所有 Parquet 文件的行数。
    """
    path = Path(base_path)
    total = 0
    for f in path.rglob("*.parquet"):
        total += pq.ParquetFile(str(f)).metadata.num_rows
    return total


def count_size_mb(base_path: Path | str) -> float:
    """
    递归统计目录下所有 Parquet 文件的总大小（MB）。
    """
    path = Path(base_path)
    total_bytes = 0
    for f in path.rglob("*.parquet"):
        total_bytes += f.stat().st_size
    return round(total_bytes / (1024 * 1024), 2)
