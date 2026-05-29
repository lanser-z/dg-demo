"""
dg_platform — 数据治理平台核心模块

模块一：数据资产可视化
"""
from dg_platform.asset_visualizer import (
    get_system_status,
    get_asset_catalog,
    get_quality_score_card,
    get_security_classification,
)
from dg_platform.data_profiler import (
    profile_parquet,
    discover_partitions,
    count_rows,
)

__all__ = [
    "get_system_status",
    "get_asset_catalog",
    "get_quality_score_card",
    "get_security_classification",
    "profile_parquet",
    "discover_partitions",
    "count_rows",
]
