"""Educational module for the data governance Demo teaching notebook.

Public API:
  - check_sap_quality / check_pi_quality / check_lims_quality / check_oa_quality
  - calc_quality_score
  - build_asset_catalog / SYSTEM_INFO / all_datasets
  - plot_storage_distribution / plot_quality_scorecard / plot_security_levels / plot_business_impact
  - estimate_annual_cost / format_business_impact_line / COST_TABLE

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
from .quality import (
    DIMENSION_WEIGHTS,
    calc_quality_score,
    check_lims_quality,
    check_oa_quality,
    check_pi_quality,
    check_sap_quality,
)
from .visualization import (
    SYSTEM_COLORS,
    plot_business_impact,
    plot_quality_scorecard,
    plot_security_levels,
    plot_storage_distribution,
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
    # visualization
    "SYSTEM_COLORS",
    "plot_business_impact",
    "plot_quality_scorecard",
    "plot_security_levels",
    "plot_storage_distribution",
]
