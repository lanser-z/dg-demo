"""Data asset catalog for the 5 simulated systems (A 公司煤炭数据治理 Demo).

Single source of truth for the 12 datasets, their Chinese names, owners,
and security classification. Imported by both the teaching notebook
(module1.ipynb) and the screenshot script.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

# 5 系统 / 12 表的中文名 / Owner / 安全级别
# 注：这是教学用元数据，与 Background.md 中的业务场景对齐
SYSTEM_INFO: dict[str, dict[str, Any]] = {
    "lims": {
        "tables": {"samples": "煤质化验样品"},
        "owner_id": "coal_quality_team",
        "owner_name": "煤质中心",
        "security": "重要资产",
        "sla": "T+1 增量",
    },
    "sap_erp": {
        "tables": {
            "kna1": "客户主数据",
            "vbak": "销售订单抬头",
            "vbap": "销售订单行项目",
            "likp": "交货单抬头",
            "lips": "交货单行项目",
            "mara": "物料主数据",
        },
        "owner_id": "sales_dept",
        "owner_name": "销售部",
        "security": "重要资产",
        "sla": "T+1 全量",
    },
    "pi_system": {
        "tables": {"tags": "PI 时序标签数据"},
        "owner_id": "safety_dept",
        "owner_name": "安全部",
        "security": "核心资产",
        "sla": "准实时（Kafka 流）",
    },
    "oa": {
        "tables": {
            "doc_flow": "文档流转记录",
            "contract": "合同记录",
            "meeting": "会议记录",
        },
        "owner_id": "admin_dept",
        "owner_name": "综合管理部",
        "security": "一般资产",
        "sla": "T+1 增量",
    },
    "scada": {
        "tables": {"equipment_status": "设备状态"},
        "owner_id": "safety_dept",
        "owner_name": "安全部",
        "security": "核心资产",
        "sla": "准实时（OPC-UA/Kafka）",
    },
}


def all_datasets() -> list[tuple[str, str, str]]:
    """返回 (platform, table, 中文名) 元组列表，按系统内表名字典序排序。"""
    out = []
    for platform, info in SYSTEM_INFO.items():
        for table, zh_name in sorted(info["tables"].items()):
            out.append((platform, table, zh_name))
    return out


def build_asset_catalog(data_root: str | Path) -> pd.DataFrame:
    """扫描 data_root 下的 Parquet，构建资产目录 DataFrame。

    Args:
        data_root: 包含 `{system}/**/*.parquet` 的根目录。

    Returns:
        DataFrame，列：系统、表/数据集、记录数、存储大小(MB)、说明、Owner。
    """
    data_root = Path(data_root)
    rows: list[dict[str, Any]] = []
    for platform, info in SYSTEM_INFO.items():
        platform_dir = data_root / platform
        if not platform_dir.exists():
            continue
        parquet_files = sorted(platform_dir.rglob("*.parquet"))
        if not parquet_files:
            continue
        total_rows = 0
        total_size_mb = 0.0
        for f in parquet_files:
            total_size_mb += f.stat().st_size / 1024 / 1024
            try:
                total_rows += len(pd.read_parquet(f))
            except Exception:
                pass
        table_names = "/".join(sorted(info["tables"].keys()))
        zh_summary = "、".join(info["tables"].values())
        rows.append(
            {
                "系统": platform,
                "表/数据集": table_names,
                "记录数": total_rows,
                "存储大小(MB)": round(total_size_mb, 1),
                "说明": zh_summary,
                "Owner": info["owner_name"],
                "安全级别": info["security"],
            }
        )
    return pd.DataFrame(rows)
