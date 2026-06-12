"""Data quality check functions for the 5 simulated systems.

Each function returns a dict mapping alert name to percentage (0-100).
Higher = more issues. Combined with `calc_quality_score` to produce
a 4-dimension scorecard for the educational notebook.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

# 4 类根因分析中各煤种的灰分合理区间
AD_RANGES_BY_COAL_TYPE: dict[str, tuple[float, float]] = {
    "原煤": (10, 50),
    "精煤": (5, 15),
    "中煤": (15, 45),
    "矸石": (45, 90),
    "洗煤": (5, 20),
}


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


# ============================================================
# 根因分析函数（模块二）
# ============================================================


def analyze_vbap_invalid_links(vbap: pd.DataFrame) -> dict[str, Any]:
    """分析 SAP VBAP 表中关联到无效订单号的"孤儿行项目"。

    无效订单号定义：VBELN == '0000000000'。
    实际数据中约 1% 的行项目有此问题，导致库存账实不符。

    根因维度：按物料编码 MATNR 前 3 位（前缀代表物料大类）统计，
    定位"哪类物料的订单最容易产生孤儿行"。

    Args:
        vbap: VBAP 行项目 DataFrame（必需列：VBELN, MATNR）

    Returns:
        dict，包含:
          - total_invalid (int): 无效关联行数
          - invalid_pct (float): 无效率（百分比，0-100）
          - by_mat_prefix (pd.DataFrame): 按物料前 3 位分组，列=[物料前缀, 数量, 占比%]
          - sample_vbeln (list[str]): 前 5 个无效行对应的 VBELN 样本
          - top_mat_prefix (str): 出现最多的物料前缀
    """
    total = len(vbap)
    invalid_mask = vbap["VBELN"] == "0000000000"
    total_invalid = int(invalid_mask.sum())
    invalid_pct = round(total_invalid / total * 100, 3) if total > 0 else 0.0

    invalid_mat = vbap.loc[invalid_mask, "MATNR"].astype(str)
    by_mat_prefix = (
        invalid_mat.str[:3]
        .value_counts()
        .head(10)
        .reset_index()
    )
    by_mat_prefix.columns = ["物料前缀", "数量"]
    by_mat_prefix["占比%"] = round(by_mat_prefix["数量"] / max(total_invalid, 1) * 100, 2)

    sample_vbeln = (
        vbap.loc[invalid_mask, "VBELN"].head(5).tolist()
    )

    top_mat_prefix = str(by_mat_prefix.iloc[0]["物料前缀"]) if len(by_mat_prefix) > 0 else "N/A"

    return {
        "total_invalid": total_invalid,
        "invalid_pct": invalid_pct,
        "by_mat_prefix": by_mat_prefix,
        "sample_vbeln": sample_vbeln,
        "top_mat_prefix": top_mat_prefix,
    }


def analyze_pi_missing_tags(pi_df: pd.DataFrame) -> dict[str, Any]:
    """分析 PI-System 中设备掉线（status=-1）的标签分布。

    实际数据中约 0.5% 的点位 status=-1，表现为"设备掉线"。
    需检查传感器网络连接和采集网关状态。

    Args:
        pi_df: PI tags DataFrame（必需列：tag, status, timestamp）

    Returns:
        dict，包含:
          - total_missing (int): status=-1 的行数
          - missing_pct (float): 缺失率（百分比，0-100）
          - by_tag (pd.DataFrame): 按标签分组的缺失数 Top 10，列=[标签, 缺失数]
          - by_hour (pd.DataFrame): 按小时分组的缺失数，列=[小时, 缺失数]
          - top_tag (str): 缺失最多的标签
    """
    total = len(pi_df)
    missing_mask = pi_df["status"] == -1
    total_missing = int(missing_mask.sum())
    missing_pct = round(total_missing / total * 100, 3) if total > 0 else 0.0

    by_tag = (
        pi_df.loc[missing_mask, "tag"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    by_tag.columns = ["标签", "缺失数"]

    by_hour = (
        pi_df.loc[missing_mask]
        .assign(小时=pd.to_datetime(pi_df.loc[missing_mask, "timestamp"]).dt.hour)
        .groupby("小时", as_index=False)
        .size()
        .rename(columns={"size": "缺失数"})
        .sort_values("小时")
    )

    top_tag = str(by_tag.iloc[0]["标签"]) if len(by_tag) > 0 else "N/A"

    return {
        "total_missing": total_missing,
        "missing_pct": missing_pct,
        "by_tag": by_tag,
        "by_hour": by_hour,
        "top_tag": top_tag,
    }


def analyze_pi_anomalies(pi_df: pd.DataFrame) -> dict[str, Any]:
    """分析 PI-System 中 WAGAS 瓦斯异常突升（> 3x 中位数基线）的标签。

    异常突升可能意味着：
    1. 传感器故障/漂移（设备问题）
    2. 真实瓦斯涌出（安全问题）
    需结合煤矿安全规程判断。

    Args:
        pi_df: PI tags DataFrame（必需列：tag, value）

    Returns:
        dict，包含:
          - total_anomalies (int): 异常行数
          - anomaly_pct (float): 异常率（百分比，0-100）
          - median_wagas (float): WAGAS 中位数基线
          - threshold (float): 3x 中位数阈值
          - by_tag (pd.DataFrame): 按标签分组的异常数 Top 10，列=[标签, 异常数]
          - top_tag (str): 异常最多的标签
    """
    total = len(pi_df)
    wagas_mask = pi_df["tag"].astype(str).str.contains("WAGAS", na=False)
    wagas_df = pi_df.loc[wagas_mask]

    if len(wagas_df) == 0:
        return {
            "total_anomalies": 0,
            "anomaly_pct": 0.0,
            "median_wagas": 0.0,
            "threshold": 0.0,
            "by_tag": pd.DataFrame(columns=["标签", "异常数"]),
            "top_tag": "N/A",
        }

    median_wagas = float(wagas_df["value"].median())
    threshold = median_wagas * 3
    anomaly_mask = wagas_df["value"] > threshold
    total_anomalies = int(anomaly_mask.sum())
    anomaly_pct = round(total_anomalies / len(wagas_df) * 100, 3) if len(wagas_df) > 0 else 0.0

    by_tag = (
        wagas_df.loc[anomaly_mask, "tag"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    by_tag.columns = ["标签", "异常数"]

    top_tag = str(by_tag.iloc[0]["标签"]) if len(by_tag) > 0 else "N/A"

    return {
        "total_anomalies": total_anomalies,
        "anomaly_pct": anomaly_pct,
        "median_wagas": round(median_wagas, 4),
        "threshold": round(threshold, 4),
        "by_tag": by_tag,
        "top_tag": top_tag,
    }


def analyze_lims_ad_outliers(lims_df: pd.DataFrame) -> dict[str, Any]:
    """分析 LIMS 煤质化验数据中灰分（AD）超出煤种合理区间的样品。

    灰分异常影响煤价定价（800 元/吨），需化验员复检。

    Args:
        lims_df: LIMS samples DataFrame（必需列：SAMPLE_ID, SAMPLE_TYPE, AD）

    Returns:
        dict，包含:
          - total_outliers (int): 异常样品数
          - outlier_pct (float): 异常率（百分比，0-100）
          - by_sample_type (pd.DataFrame): 按煤种分组的异常数 + 占比，列=[煤种, 异常数, 占比%]
          - top_sample_type (str): 异常最多的煤种
    """
    total = len(lims_df)
    if total == 0:
        return {
            "total_outliers": 0,
            "outlier_pct": 0.0,
            "by_sample_type": pd.DataFrame(columns=["煤种", "异常数", "占比%"]),
            "top_sample_type": "N/A",
        }

    rows = []
    total_outliers = 0
    for stype, (lo, hi) in AD_RANGES_BY_COAL_TYPE.items():
        mask = lims_df["SAMPLE_TYPE"] == stype
        if mask.any():
            ad_vals = lims_df.loc[mask, "AD"].dropna()
            outliers = int(((ad_vals < lo) | (ad_vals > hi)).sum())
            total_outliers += outliers
            if outliers > 0:
                rows.append({"煤种": stype, "异常数": outliers, "占比%": round(outliers / max(total, 1) * 100, 3)})

    by_sample_type = (
        pd.DataFrame(rows).sort_values("异常数", ascending=False).reset_index(drop=True)
        if rows
        else pd.DataFrame(columns=["煤种", "异常数", "占比%"])
    )

    top_sample_type = str(by_sample_type.iloc[0]["煤种"]) if len(by_sample_type) > 0 else "N/A"

    return {
        "total_outliers": total_outliers,
        "outlier_pct": round(total_outliers / total * 100, 3),
        "by_sample_type": by_sample_type,
        "top_sample_type": top_sample_type,
    }
