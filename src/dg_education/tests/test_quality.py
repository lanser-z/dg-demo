"""Sanity tests for the educational quality-check functions."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dg_education.quality import (
    calc_quality_score,
    check_lims_quality,
    check_oa_quality,
    check_pi_quality,
    check_sap_quality,
)


@pytest.fixture
def sample_vbak() -> pd.DataFrame:
    """100 rows of VBAK with 5 null KUNNR and 2 duplicates."""
    n = 100
    return pd.DataFrame({
        "NETWR": [100.0] * n,
        "ERZET": ["08:00:00"] * n,
        "ERNAM": ["USER01"] * n,
        "KUNNR": [None if i < 5 else f"K{i:010d}" for i in range(n)],
    }).pipe(lambda df: pd.concat([df, df.head(2)], ignore_index=True))


@pytest.fixture
def sample_vbap() -> pd.DataFrame:
    """50 rows of VBAP with 1 orphan (VBELN='0000000000')."""
    return pd.DataFrame({
        "VBELN": ["0000000001"] * 49 + ["0000000000"],
    })


@pytest.fixture
def sample_kna1() -> pd.DataFrame:
    return pd.DataFrame({"KUNNR": [f"K{i:010d}" for i in range(10)]})


def test_check_sap_quality_keys(sample_vbak, sample_vbap, sample_kna1):
    q = check_sap_quality(sample_vbak, sample_vbap, sample_kna1)
    assert "null_NETWR" in q
    assert "dup_vbak" in q
    assert "invalid_link_pct" in q
    assert all(0 <= v <= 100 for v in q.values())


def test_check_sap_quality_detects_null(sample_vbak, sample_vbap, sample_kna1):
    q = check_sap_quality(sample_vbak, sample_vbap, sample_kna1)
    # 5 nulls in original 100 rows = ~4.9% (slightly diluted by duplicates)
    assert q["null_KUNNR"] > 0


def test_check_sap_quality_detects_orphan(sample_vbak, sample_vbap, sample_kna1):
    q = check_sap_quality(sample_vbak, sample_vbap, sample_kna1)
    # 1 orphan out of 50 = 2%
    assert 1.5 < q["invalid_link_pct"] < 2.5


def test_check_pi_quality_missing_and_wagas():
    n = 200
    df = pd.DataFrame({
        "tag": ["M001_WAGAS"] * 100 + ["M001_TEMP"] * 100,
        "value": list(np.linspace(0.1, 0.5, 100)) + [25.0] * 100,
        "status": [-1] * 5 + [0] * 195,
    })
    q = check_pi_quality(df)
    assert "missing_pct" in q
    assert "wagas_danger_pct" in q
    assert q["missing_pct"] > 0


def test_check_lims_quality_ad_outlier():
    n = 100
    df = pd.DataFrame({
        "SAMPLE_TYPE": ["原煤"] * n,
        "AD": [100.0] * n,  # all outliers (合理区间 10-50)
        "VD": [0.5] * n,
        "全硫St": [0.3] * n,
    })
    q = check_lims_quality(df)
    assert q["ad_outlier_pct"] == pytest.approx(100.0, abs=0.1)


def test_check_oa_quality_dup():
    df = pd.DataFrame({
        "FLOW_TYPE": ["审批"] * 10,
        "STATUS": ["完成"] * 10,
    })
    df = pd.concat([df, df.head(2)], ignore_index=True)
    q = check_oa_quality(df)
    assert q["dup_pct"] > 0


def test_calc_quality_score_composite_in_range():
    sys_scores = {
        "SYS_A": {"完整性": 90, "一致性": 88, "准确性": 92, "唯一性": 95},
        "SYS_B": {"完整性": 95, "一致性": 90, "准确性": 89, "唯一性": 91},
    }
    df = calc_quality_score(sys_scores)
    assert "综合得分" in df.columns
    assert 85 <= df.loc["SYS_A", "综合得分"] <= 95
    assert 85 <= df.loc["SYS_B", "综合得分"] <= 95
