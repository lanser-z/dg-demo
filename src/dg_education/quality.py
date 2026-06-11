"""Data quality check functions for the 5 simulated systems.

Each function returns a dict mapping alert name to percentage (0-100).
Higher = more issues. Combined with `calc_quality_score` to produce
a 4-dimension scorecard for the educational notebook.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def check_sap_quality(vbak: pd.DataFrame, vbap: pd.DataFrame, kna1: pd.DataFrame) -> dict[str, float]:
    """SAP-ERP quality check (VBAK / VBAP / KNA1).

    Returns a dict of alert_name -> percentage. Keys:
      - null_NETWR / null_ERZET / null_ERNAM / null_KUNNR: 空值比例
      - dup_vbak / dup_kna1: 重复行比例
      - invalid_link_pct: VBAP.VBELN='0000000000' 的比例
    """
    results: dict[str, float] = {}
    for col in ("NETWR", "ERZET", "ERNAM", "KUNNR"):
        if col in vbak.columns:
            results[f"null_{col}"] = float(vbak[col].isnull().mean() * 100)
    results["dup_vbak"] = float(vbak.duplicated().mean() * 100)
    results["dup_kna1"] = float(kna1.duplicated().mean() * 100)
    valid_vbap = (vbap["VBELN"] != "0000000000").mean() * 100
    results["invalid_link_pct"] = float(100 - valid_vbap)
    return results


def check_pi_quality(df_pi: pd.DataFrame) -> dict[str, float]:
    """PI-System quality check (瓦斯 / 一氧化碳 / 温度 标签).

    Returns:
      - missing_pct: status=-1 的点位比例
      - wagas_danger_pct: WAGAS value > 1.0 的比例
      - wagas_anomaly_pct: WAGAS value > 3x 中位数基线 的比例
    """
    results: dict[str, float] = {}
    results["missing_pct"] = float((df_pi["status"] == -1).mean() * 100)
    wagas = df_pi[df_pi["tag"].str.contains("WAGAS", na=False)]
    if len(wagas) > 0:
        results["wagas_danger_pct"] = float((wagas["value"] > 1.0).mean() * 100)
        median_w = wagas["value"].median()
        anomaly_threshold = median_w * 3
        results["wagas_anomaly_pct"] = float((wagas["value"] > anomaly_threshold).mean() * 100)
    else:
        results["wagas_danger_pct"] = 0.0
        results["wagas_anomaly_pct"] = 0.0
    return results


def check_lims_quality(df_lims: pd.DataFrame) -> dict[str, float]:
    """LIMS quality check (煤质化验样品).

    Returns:
      - null_AD / null_VD / null_QGR_AD / null_全硫St / null_全水分Mt: 关键指标空值
      - ad_outlier_pct: 灰分超出煤种合理区间的比例
      - dup_pct: 重复检测批次比例
    """
    results: dict[str, float] = {}
    for col in ("AD", "VD", "QGR_AD", "全硫St", "全水分Mt"):
        if col in df_lims.columns:
            results[f"null_{col}"] = float(df_lims[col].isnull().mean() * 100)
    ad_ranges = {
        "原煤": (10, 50),
        "精煤": (5, 15),
        "中煤": (15, 45),
        "矸石": (45, 90),
        "洗煤": (5, 20),
    }
    invalid = 0
    for stype, (lo, hi) in ad_ranges.items():
        mask = df_lims["SAMPLE_TYPE"] == stype
        if mask.any():
            vals = df_lims.loc[mask, "AD"].dropna()
            invalid += int(((vals < lo) | (vals > hi)).sum())
    results["ad_outlier_pct"] = float(invalid / len(df_lims) * 100) if len(df_lims) else 0.0
    results["dup_pct"] = float(df_lims.duplicated().mean() * 100)
    return results


def check_oa_quality(df_oa: pd.DataFrame) -> dict[str, float]:
    """OA quality check (文档流转记录).

    Returns:
      - dup_pct: 重复行比例
      - null_FLOW_TYPE / null_STATUS: 关键字段空值
    """
    results: dict[str, float] = {}
    results["dup_pct"] = float(df_oa.duplicated().mean() * 100)
    for col in ("FLOW_TYPE", "STATUS"):
        if col in df_oa.columns:
            results[f"null_{col}"] = float(df_oa[col].isnull().mean() * 100)
    return results


# 4 维质量评分权重
DIMENSION_WEIGHTS = {
    "完整性": 0.3,
    "一致性": 0.3,
    "准确性": 0.2,
    "唯一性": 0.2,
}


def calc_quality_score(system_scores: dict[str, dict[str, float]]) -> pd.DataFrame:
    """根据 4 维分数计算综合得分。

    Args:
        system_scores: {系统: {维度: 0-100}}。维度必须在
            ["完整性", "一致性", "准确性", "唯一性"] 内。

    Returns:
        DataFrame，行=系统，列=4 维 + 综合得分。
    """
    rows = {}
    for sys_name, dims in system_scores.items():
        composite = sum(dims[dim] * w for dim, w in DIMENSION_WEIGHTS.items())
        dims_with_composite = {**dims, "综合得分": round(composite, 2)}
        rows[sys_name] = dims_with_composite
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = "系统"
    cols = list(DIMENSION_WEIGHTS.keys()) + ["综合得分"]
    return df[cols]
