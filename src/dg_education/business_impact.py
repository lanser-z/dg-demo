"""Translate data quality alerts into business impact (cost / risk).

This is a *teaching* simplification. The unit costs are publicly
known industry reference values (煤价 800 元/吨, 财务对账 5 分钟/单,
工时 50 元/h) — NOT precise business numbers. The notebook
explicitly labels these as 教学参考值.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostReference:
    """A single alert's unit cost + narrative hint.

    All unit costs are industry reference values for teaching only.
    See `docs/Background.md` for the source of the numbers.
    """

    alert_key: str            # matches keys returned by check_*_quality()
    label: str                # human-readable name
    unit: str                 # e.g. "元/条" / "元/起"
    unit_cost: float          # 元
    narrative: str            # 1 sentence business impact
    reference: str            # source of the unit cost (e.g. "Background.md 行业参考")


# 教学参考值（与 docs/Background.md 业务场景对齐，非精确业务数字）
COST_TABLE: dict[str, CostReference] = {
    "SAP.dup_vbak": CostReference(
        alert_key="SAP.dup_vbak",
        label="VBAK 销售订单重复",
        unit="元/条",
        unit_cost=8.0,
        narrative="财务对账每条花 5 分钟 + 工时 50 元/h",
        reference="Background.md 业务场景：销售订单对账",
    ),
    "SAP.invalid_link_pct": CostReference(
        alert_key="SAP.invalid_link_pct",
        label="VBAP 关联失效（孤儿行项目）",
        unit="元/条",
        unit_cost=12.0,
        narrative="行项目挂不到订单 = 库存账实不符，影响 1 周内盘点",
        reference="Background.md 业务场景：库存盘点",
    ),
    "PI.wagas_danger_pct": CostReference(
        alert_key="PI.wagas_danger_pct",
        label="瓦斯浓度超 1% 告警",
        unit="元/起",
        unit_cost=50_000.0,
        narrative="瓦斯超 1% 接近爆炸阈值，漏报 1 起可能引发停产 + 调查成本",
        reference="Background.md 业务场景：煤矿安全规程",
    ),
    "PI.wagas_anomaly_pct": CostReference(
        alert_key="PI.wagas_anomaly_pct",
        label="瓦斯异常突升（> 3x 基线）",
        unit="元/起",
        unit_cost=20_000.0,
        narrative="异常突升意味着传感器异常或地质变化，漏报 1 起需现场排查 1 天",
        reference="Background.md 业务场景：传感器健康",
    ),
    "LIMS.ad_outlier_pct": CostReference(
        alert_key="LIMS.ad_outlier_pct",
        label="煤质灰分超合理区间",
        unit="元/条",
        unit_cost=15.0,
        narrative="灰分异常影响煤价定价（800 元/吨），每条需化验员复检",
        reference="Background.md 业务场景：煤化工单价",
    ),
    "LIMS.dup_pct": CostReference(
        alert_key="LIMS.dup_pct",
        label="LIMS 重复检测批次",
        unit="元/条",
        unit_cost=6.0,
        narrative="重复批次需化验员人工去重 + 追溯，重做一份 200 元 ÷ 30 条",
        reference="Background.md 业务场景：化验流程",
    ),
    "OA.dup_pct": CostReference(
        alert_key="OA.dup_pct",
        label="OA 重复流程记录",
        unit="元/条",
        unit_cost=2.0,
        narrative="重复流程需行政人员清理 1 条 2 元，量级小但累计可观",
        reference="Background.md 业务场景：行政流程",
    ),
}


def estimate_annual_cost(
    alert_key: str,
    total_rows: int,
    injection_rate_pct: float,
) -> dict[str, float | str]:
    """Estimate annual business impact for one alert.

    Args:
        alert_key: e.g. "SAP.dup_vbak", must be in COST_TABLE.
        total_rows: number of rows in the source table (年发生量的基数).
        injection_rate_pct: 注入率 0-100 (e.g. 0.498 表示 0.498%).

    Returns:
        dict with: events_per_year, unit_cost, total_yuan, narrative, unit, label
    """
    ref = COST_TABLE.get(alert_key)
    if ref is None:
        raise KeyError(f"Unknown alert_key {alert_key!r}. Known: {list(COST_TABLE)}")
    events_per_year = int(total_rows * injection_rate_pct / 100)
    total_yuan = events_per_year * ref.unit_cost
    return {
        "alert_key": alert_key,
        "label": ref.label,
        "unit": ref.unit,
        "unit_cost": ref.unit_cost,
        "events_per_year": events_per_year,
        "total_yuan": round(total_yuan, 2),
        "narrative": ref.narrative,
        "reference": ref.reference,
    }


def format_business_impact_line(
    alert_key: str,
    total_rows: int,
    injection_rate_pct: float,
) -> str:
    """Format a single-line `[业务影响] ...` annotation for notebook printing.

    Output looks like:
      [业务影响] VBAK 销售订单重复：18.1M 行 × 0.498% ≈ 9.0 万条/年
              × 8.0 元/条 = 72.0 万元成本/年
              （行数取自 data/historical/ 实际数据，单位成本为教学参考值）
    """
    est = estimate_annual_cost(alert_key, total_rows, injection_rate_pct)
    rows_pretty = f"{total_rows / 1_000_000:.1f}M" if total_rows >= 1_000_000 else f"{total_rows:,}"
    rate_pretty = f"{injection_rate_pct:.3f}%"
    cost_pretty = f"{est['total_yuan']:,.0f} 元"
    events_pretty = f"{est['events_per_year']:,}"
    return (
        f"[业务影响] {est['label']}：{rows_pretty} 行 × {rate_pretty} ≈ "
        f"{events_pretty} 条/年 × {est['unit_cost']:.1f} {est['unit']} "
        f"= {cost_pretty}/年\n"
        f"  解释：{est['narrative']}\n"
        f"  来源：行数取自 data/historical/ 实际数据，单位成本为教学参考值 "
        f"（{est['reference']}）"
    )
