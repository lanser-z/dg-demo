"""Sanity tests for the business-impact translator."""
from __future__ import annotations

import pytest

from dg_education.business_impact import (
    COST_TABLE,
    estimate_annual_cost,
    format_business_impact_line,
)


def test_cost_table_has_expected_keys():
    for k in (
        "SAP.dup_vbak",
        "SAP.invalid_link_pct",
        "PI.wagas_danger_pct",
        "PI.wagas_anomaly_pct",
        "LIMS.ad_outlier_pct",
        "LIMS.dup_pct",
        "OA.dup_pct",
    ):
        assert k in COST_TABLE, f"missing cost reference: {k}"


def test_estimate_annual_cost_basic():
    est = estimate_annual_cost("SAP.dup_vbak", total_rows=18_105_000, injection_rate_pct=0.498)
    assert est["events_per_year"] == 90_162  # 18_105_000 * 0.498 / 100
    assert est["total_yuan"] == pytest.approx(721_296.0, abs=1.0)


def test_estimate_annual_cost_zero_rate():
    est = estimate_annual_cost("LIMS.dup_pct", total_rows=2_010_000, injection_rate_pct=0.0)
    assert est["events_per_year"] == 0
    assert est["total_yuan"] == 0.0


def test_estimate_annual_cost_unknown_key_raises():
    with pytest.raises(KeyError):
        estimate_annual_cost("nonexistent.alert", 1_000_000, 1.0)


def test_format_business_impact_line_contains_required_parts():
    line = format_business_impact_line("PI.wagas_danger_pct", 78_624_000, 0.281)
    assert "[业务影响]" in line
    assert "78.6M" in line or "78M" in line  # large numbers formatted as M
    assert "0.281%" in line
    assert "条/年" in line
    assert "教学参考值" in line
    assert "data/historical/" in line


def test_format_business_impact_line_multi_line():
    line = format_business_impact_line("OA.dup_pct", 5_025_000, 0.497)
    # multi-line output with 解释 + 来源
    assert "\n" in line
    assert "解释：" in line
    assert "来源：" in line
