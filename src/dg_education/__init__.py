"""Educational module for the data governance Demo teaching notebook.

Public API:
  - check_sap_quality / check_pi_quality / check_lims_quality / check_oa_quality
  - calc_quality_score
  - build_asset_catalog / SYSTEM_INFO / all_datasets
  - plot_storage_distribution / plot_quality_scorecard / plot_security_levels / plot_business_impact
  - estimate_annual_cost / format_business_impact_line / COST_TABLE
  - run_ge_scan (模块二)
  - analyze_vbap_invalid_links / analyze_pi_missing_tags / analyze_pi_anomalies / analyze_lims_ad_outliers (模块二)
  - plot_root_cause_distribution / plot_alert_heatmap / plot_system_alert_summary (模块二)

The notebook module1.ipynb imports from this module instead of defining
inline functions, so 小白 can focus on concepts and visualizations
rather than the mechanics of data analysis.
"""
from .business_impact import (
    COST_TABLE,
    CostReference,
    estimate_annual_cost,
    format_business_impact_line,
)
from .catalog import SYSTEM_INFO, all_datasets, build_asset_catalog
from .ge_scan import run_ge_scan
from .quality import (
    DIMENSION_WEIGHTS,
    analyze_lims_ad_outliers,
    analyze_pi_anomalies,
    analyze_pi_missing_tags,
    analyze_vbap_invalid_links,
    calc_quality_score,
    check_lims_quality,
    check_oa_quality,
    check_pi_quality,
    check_sap_quality,
)
from .visualization import (
    SYSTEM_COLORS,
    plot_alert_heatmap,
    plot_business_impact,
    plot_quality_scorecard,
    plot_root_cause_distribution,
    plot_security_levels,
    plot_storage_distribution,
    plot_system_alert_summary,
)

__all__ = [
    # business impact
    "COST_TABLE",
    "CostReference",
    "estimate_annual_cost",
    "format_business_impact_line",
    # catalog
    "SYSTEM_INFO",
    "all_datasets",
    "build_asset_catalog",
    # quality
    "DIMENSION_WEIGHTS",
    "calc_quality_score",
    "check_lims_quality",
    "check_oa_quality",
    "check_pi_quality",
    "check_sap_quality",
    # root cause analysis (模块二)
    "analyze_lims_ad_outliers",
    "analyze_pi_anomalies",
    "analyze_pi_missing_tags",
    "analyze_vbap_invalid_links",
    # GE scan (模块二)
    "run_ge_scan",
    # visualization
    "SYSTEM_COLORS",
    "plot_business_impact",
    "plot_quality_scorecard",
    "plot_security_levels",
    "plot_storage_distribution",
    # root cause / alert viz (模块二)
    "plot_alert_heatmap",
    "plot_root_cause_distribution",
    "plot_system_alert_summary",
]
