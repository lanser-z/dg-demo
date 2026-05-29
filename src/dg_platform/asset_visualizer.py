"""
asset_visualizer — 数据资产可视化模块

模块一核心功能：
1. get_system_status():  5个系统接入状态
2. get_asset_catalog(): 资产目录（元数据清单）
3. get_quality_score_card(): 质量评分卡
4. get_security_classification(): 安全分级
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pandas as pd

from dg_platform.data_profiler import count_rows, count_size_mb


# ── 系统定义 ────────────────────────────────────────────────────────────────

SYSTEMS = [
    {
        "name": "SAP-ERP",
        "display_name": "SAP企业资源计划",
        "data_dir": "sap_erp",
        "owner": "销售部",
        "tables": [
            {"table_name": "VBAK", "chinese_name": "销售订单抬头", "partition_field": "year"},
            {"table_name": "VBAP", "chinese_name": "销售订单行项目", "partition_field": "year"},
            {"table_name": "KNA1", "chinese_name": "客户主数据", "partition_field": ""},
            {"table_name": "MARA", "chinese_name": "物料主数据", "partition_field": ""},
            {"table_name": "LIKP", "chinese_name": "交货单抬头", "partition_field": "year"},
            {"table_name": "LIPS", "chinese_name": "交货单行项目", "partition_field": "year"},
        ],
        "security_level": "重要资产",
    },
    {
        "name": "PI-System",
        "display_name": "PI实时数据系统",
        "data_dir": "pi_system",
        "owner": "安全部",
        "tables": [
            {"table_name": "TAGS", "chinese_name": "实时传感器标签", "partition_field": "year,month"},
        ],
        "security_level": "核心资产",
    },
    {
        "name": "SCADA",
        "display_name": "SCADA数据采集系统",
        "data_dir": "scada",
        "owner": "调度中心",
        "tables": [
            {"table_name": "EQUIPMENT_STATUS", "chinese_name": "设备状态", "partition_field": ""},
        ],
        "security_level": "核心资产",
    },
    {
        "name": "LIMS",
        "display_name": "实验室信息管理系统",
        "data_dir": "lims",
        "owner": "煤质中心",
        "tables": [
            {"table_name": "SAMPLES", "chinese_name": "煤质检测样品", "partition_field": "year"},
        ],
        "security_level": "重要资产",
    },
    {
        "name": "OA",
        "display_name": "办公自动化系统",
        "data_dir": "oa",
        "owner": "综合管理部",
        "tables": [
            {"table_name": "DOC_FLOW", "chinese_name": "审批流程记录", "partition_field": "year"},
            {"table_name": "CONTRACT", "chinese_name": "合同台账", "partition_field": ""},
            {"table_name": "MEETING", "chinese_name": "会议纪要", "partition_field": ""},
        ],
        "security_level": "一般资产",
    },
]

# 历史数据根目录（相对于项目根）
HISTORICAL_ROOT = Path(__file__).parent.parent.parent / "data" / "historical"


# ── 核心函数 ────────────────────────────────────────────────────────────────

def get_system_status() -> list[dict]:
    """
    返回5个系统的接入状态。

    Returns:
        list[dict] — 每系统包含:
            name, display_name, status, record_count, size_mb, owner
    """
    results = []
    for sys_def in SYSTEMS:
        data_dir = HISTORICAL_ROOT / sys_def["data_dir"]
        if data_dir.exists():
            record_count = count_rows(data_dir)
            size_mb = count_size_mb(data_dir)
            status = "connected" if record_count > 0 else "disconnected"
        else:
            record_count = 0
            size_mb = 0.0
            status = "unknown"

        results.append({
            "name": sys_def["name"],
            "display_name": sys_def["display_name"],
            "status": status,
            "record_count": record_count,
            "size_mb": size_mb,
            "owner": sys_def["owner"],
        })
    return results


def get_asset_catalog() -> pd.DataFrame:
    """
    返回资产目录 DataFrame，字段：
        table_name, chinese_name, owner, row_count, size_mb,
        partition_field, system, security_level
    """
    rows = []
    for sys_def in SYSTEMS:
        data_dir = HISTORICAL_ROOT / sys_def["data_dir"]
        if data_dir.exists():
            total_rows = count_rows(data_dir)
            total_size = count_size_mb(data_dir)
        else:
            # SCADA 等实时系统无历史文件，仍列出（row_count=0）
            total_rows = 0
            total_size = 0.0

        for table_def in sys_def["tables"]:
            rows.append({
                "table_name": table_def["table_name"],
                "chinese_name": table_def["chinese_name"],
                "owner": sys_def["owner"],
                "row_count": total_rows,
                "size_mb": total_size,
                "partition_field": table_def["partition_field"],
                "system": sys_def["name"],
                "security_level": sys_def["security_level"],
            })

    return pd.DataFrame(rows)


def get_quality_score_card() -> pd.DataFrame:
    """
    返回质量评分卡 DataFrame。

    评分基于 Background.md 中各系统的质量问题注入比例，
    模拟计算综合评分（模拟值，非实际检测）。

    评分维度：
        completeness 完整性（100% - null_rate）
        consistency  一致性（基于跨系统关联成功率）
        timeliness   时效性（T+1 到达率）
        accuracy     准确性（异常值比例）
    """
    # 质量问题注入比例 -> 模拟质量评分
    quality_map = {
        "SAP-ERP": {
            "completeness": 97.2,
            "consistency": 91.5,
            "timeliness": 99.8,
            "accuracy": 95.1,
        },
        "PI-System": {
            "completeness": 98.1,
            "consistency": 93.8,
            "timeliness": 99.5,
            "accuracy": 89.2,
        },
        "SCADA": {
            "completeness": 95.0,
            "consistency": 90.0,
            "timeliness": 99.0,
            "accuracy": 88.0,
        },
        "LIMS": {
            "completeness": 94.6,
            "consistency": 88.3,
            "timeliness": 96.2,
            "accuracy": 91.7,
        },
        "OA": {
            "completeness": 92.1,
            "consistency": 85.0,
            "timeliness": 94.8,
            "accuracy": 90.5,
        },
    }

    rows = []
    for sys_def in SYSTEMS:
        name = sys_def["name"]
        scores = quality_map.get(name, {
            "completeness": 90.0,
            "consistency": 90.0,
            "timeliness": 90.0,
            "accuracy": 90.0,
        })

        overall = (
            scores["completeness"] * 0.30
            + scores["consistency"] * 0.30
            + scores["timeliness"] * 0.20
            + scores["accuracy"] * 0.20
        )

        rows.append({
            "system": name,
            "completeness": scores["completeness"],
            "consistency": scores["consistency"],
            "timeliness": scores["timeliness"],
            "accuracy": scores["accuracy"],
            "overall_score": round(overall, 1),
        })

    return pd.DataFrame(rows)


def get_security_classification() -> pd.DataFrame:
    """
    返回安全分级 DataFrame。
    字段：system, table_name, security_level
    """
    rows = []
    for sys_def in SYSTEMS:
        for table_def in sys_def["tables"]:
            rows.append({
                "system": sys_def["name"],
                "table_name": table_def["table_name"],
                "security_level": sys_def["security_level"],
            })
    return pd.DataFrame(rows)
