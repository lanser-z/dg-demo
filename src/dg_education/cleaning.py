"""数据清洗 API（模块四）。

从 ingest_to_deltalake.py 的 _clean() 抽出基础清洗（去空/去重/规范化），
新增 3 类智能修复（VBAP 关联标记 / PI 异常插值 / LIMS 灰分夹逼），
并提供 Delta Lake 落库与 Time Travel 查询封装供 notebook 一行调用。

设计原则（见 openspec/changes/module4-data-cleaning/design.md）：
- 基础清洗 = 删行（去空/去重）
- 智能修复 = 改值/加列，不删行（与基础清洗互补，形成 4 类清洗）
- 智能修复仅返回临时 df，不落 lakehouse（修复是近似值，落库需源头改单）
- 复用 dg_education.quality.AD_RANGES_BY_COAL_TYPE 常量，不重复定义
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from deltalake import DeltaTable
from deltalake.writer import write_deltalake

from .quality import AD_RANGES_BY_COAL_TYPE

# Lakehouse 根目录（与 ingest_to_deltalake.py 一致）
LAKEHOUSE_ROOT = Path(__file__).resolve().parents[2] / "data" / "lakehouse"
# 历史数据根目录
DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "historical"


# ============================================================
# 基础清洗（从 ingest_to_deltalake.py:_clean() 抽出，逐行等价）
# ============================================================
def clean_basic(source: str, df: pd.DataFrame) -> pd.DataFrame:
    """应用 DWD 基础清洗规则（去空/去重/规范化）。

    与 scripts/ingest_to_deltalake.py:_clean() 逻辑完全一致（单一真相源）。
    source 形如 'sap_erp/vbak'。
    """
    df = df.copy()
    if source == "sap_erp/vbak":
        df = df.dropna(subset=["NETWR", "ERNAM", "VBELN"])
        df = df.drop_duplicates(subset=["VBELN"], keep="first")
        df["NETWR"] = df["NETWR"].astype(float).round(2)
    elif source == "sap_erp/vbap":
        df = df.dropna(subset=["MATNR", "VBELN"])
        df = df[df["NETWR"] > 0]
        df = df.drop_duplicates(subset=["VBELN", "POSNR"], keep="first")
    elif source == "sap_erp/kna1":
        df = df.dropna(subset=["NAME1", "STCD1", "KUNNR"])
        df["KUNNR"] = df["KUNNR"].astype(str).str.zfill(10)
    elif source == "pi_system/tags":
        df = df.dropna(subset=["tag", "value"])
        df = df[df["status"] != -1]
        df = df[(df["value"] >= 0) & (df["value"] <= 10000)]
    elif source == "lims/samples":
        df = df.dropna(subset=["SAMPLE_ID", "AD"])
        df = df[df["AD"] >= 0]
    elif source == "oa/doc_flow":
        df = df.dropna(subset=["FLOW_TYPE", "APPLY_DATE"])
    return df


def cleaning_stats(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, Any]:
    """清洗前后统计：剔除行数/比例。"""
    dropped = len(before) - len(after)
    pct = dropped / len(before) * 100 if len(before) > 0 else 0.0
    return {
        "before": int(len(before)),
        "after": int(len(after)),
        "dropped": int(dropped),
        "dropped_pct": round(pct, 2),
    }


# ============================================================
# 智能修复 1：VBAP 关联失效标记（改值/加列，不删行）
# ============================================================
def mark_vbap_valid_link(vbap: pd.DataFrame, vbak: pd.DataFrame) -> pd.DataFrame:
    """为 vbap 加 IS_VALID_LINK 布尔列：VBELN 是否存在于 vbak.VBELN 集合。

    孤儿行（VBELN=0000000000 等）标记为 False，但不删除（下游可自行决策）。
    """
    df = vbap.copy()
    valid_vbeln = set(vbak["VBELN"].dropna().astype(str))
    df["IS_VALID_LINK"] = df["VBELN"].astype(str).isin(valid_vbeln)
    return df


# ============================================================
# 智能修复 2：PI 异常值线性插值（改值，不删行）
# ============================================================
def repair_pi_anomalies(pi_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """对超 3x 中位数的 value 用线性插值替代（复用模块二阈值逻辑）。

    先 sort_values(timestamp) + groupby(tag) 再 interpolate，避免乱序插值。
    返回 (修复后 df, 修复行数)。不删行。
    """
    df = pi_df.copy()
    df = df.sort_values("timestamp")
    median_v = df["value"].median()
    if pd.isna(median_v) or median_v <= 0:
        return df, 0
    threshold = median_v * 3
    anomaly_mask = df["value"] > threshold
    n_fixed = int(anomaly_mask.sum())
    if n_fixed == 0:
        return df, 0
    # 把异常值置 NaN，再按 tag 分组线性插值
    df.loc[anomaly_mask, "value"] = pd.NA
    df["value"] = df.groupby("tag")["value"].transform(
        lambda s: s.interpolate(method="linear", limit_direction="both")
    )
    return df, n_fixed


# ============================================================
# 智能修复 3：LIMS 灰分夹逼修正（改值，不删行）
# ============================================================
def repair_lims_ad(lims_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """对超煤种区间的 AD 夹逼到 [lo, hi] 边界（超上限→hi，超下限→lo）。

    复用 dg_education.quality.AD_RANGES_BY_COAL_TYPE 常量，不重复定义。
    返回 (修复后 df, 修复行数)。不删行。
    """
    df = lims_df.copy()
    n_fixed = 0
    for stype, (lo, hi) in AD_RANGES_BY_COAL_TYPE.items():
        mask = df["SAMPLE_TYPE"] == stype
        if not mask.any():
            continue
        ad = df.loc[mask, "AD"]
        too_high = ad > hi
        too_low = ad < lo
        df.loc[mask & too_high, "AD"] = hi
        df.loc[mask & too_low, "AD"] = lo
        n_fixed += int(too_high.sum() + too_low.sum())
    return df, n_fixed


# ============================================================
# Delta Lake 封装（基础清洗落库 + Time Travel 查询）
# ============================================================
def clean_and_write_dwd(table_key: str) -> dict[str, Any]:
    """基础清洗 + 落 Delta Lake，返回 before/after 行数与存储统计。

    table_key 形如 'sap_erp/vbak'。读 ODS 原始 Parquet，clean_basic 清洗，
    write_deltalake 覆盖写到 data/lakehouse/dwd/{table_key}/。
    智能修复不在此函数（不落库）。
    """
    # 读 ODS 原始 Parquet
    source_path = DATA_ROOT / f"{table_key}.parquet"
    if not source_path.exists():
        # 处理 year= 分区路径（如 vbak_year=2022.parquet）
        import glob
        candidates = glob.glob(str(DATA_ROOT / table_key.replace("/", "/") + "_year=*.parquet"))
        if not candidates:
            raise FileNotFoundError(f"ODS 源文件不存在: {source_path}")
        source_path = Path(sorted(candidates)[0])
    before_df = pd.read_parquet(source_path)
    after_df = clean_basic(table_key, before_df)

    table_uri = str(LAKEHOUSE_ROOT / "dwd" / table_key)
    os.makedirs(os.path.dirname(table_uri), exist_ok=True)
    write_deltalake(table_uri, after_df, mode="overwrite")

    return {
        "table": table_key,
        **cleaning_stats(before_df, after_df),
        "delta_path": table_uri,
    }


def show_delta_history(table_key: str) -> list[dict[str, Any]]:
    """读 Delta Lake _delta_log，返回版本历史（版本号 + 操作时间 + 操作类型）。

    供 notebook 演示 Time Travel。
    """
    table_uri = str(LAKEHOUSE_ROOT / "dwd" / table_key)
    dt = DeltaTable(table_uri)
    history = dt.history()
    out = []
    for h in history:
        out.append({
            "version": h.get("version"),
            "timestamp": h.get("timestamp"),
            "operation": h.get("operation"),
        })
    return out
