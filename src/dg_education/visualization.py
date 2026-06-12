"""Matplotlib visualization functions for the educational notebook.

Each `plot_*` function:
  - Takes a DataFrame (or nothing) and optional save_to path
  - Configures matplotlib inline (caller is responsible for %matplotlib inline)
  - Returns the matplotlib Figure (caller can call plt.show() or savefig)

The notebook uses these to keep code cells small (小白 should see at most
5-10 lines of plotting code per cell, not 30 lines of inline matplotlib).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Colors for the 5 systems (consistent across all plots)
SYSTEM_COLORS: dict[str, str] = {
    "SAP-ERP": "#2196F3",
    "PI-System": "#FF5722",
    "LIMS": "#4CAF50",
    "OA": "#FF9800",
    "SCADA": "#9C27B0",
}

# Chinese font configuration
_FONT_FAMILY = "sans-serif"
_FONT_SANS_SERIF = ["Noto Sans CJK JP", "Noto Sans"]


def _ensure_chinese_font() -> None:
    plt.rcParams["font.family"] = _FONT_FAMILY
    plt.rcParams["font.sans-serif"] = _FONT_SANS_SERIF
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 100


def plot_storage_distribution(df: pd.DataFrame, save_to: str | Path | None = None) -> plt.Figure:
    """2-subplot figure: pie (存储分布) + bar (记录数).

    Args:
        df: from build_asset_catalog() — must have 系统, 记录数, 存储大小(MB) columns.
        save_to: optional path to save PNG; if None just returns the Figure.
    """
    _ensure_chinese_font()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    colors = [SYSTEM_COLORS.get(sys_name, "#9E9E9E") for sys_name in df["系统"]]

    axes[0].pie(
        df["存储大小(MB)"],
        labels=df["系统"],
        autopct="%1.1f%%",
        colors=colors,
        startangle=90,
        explode=[0.02] * len(df),
    )
    axes[0].set_title("各系统存储分布", fontsize=14, fontweight="bold")
    axes[0].text(
        0, 0,
        f"总: {df['存储大小(MB)'].sum():.1f} MB",
        ha="center", va="center", fontsize=10, color="gray",
    )

    bars = axes[1].bar(
        df["系统"],
        df["记录数"] / 1_000_000,
        color=colors,
        edgecolor="white",
        linewidth=1.5,
    )
    axes[1].set_title("各系统记录数 (百万行)", fontsize=14, fontweight="bold")
    axes[1].set_ylabel("记录数 (百万)")
    for bar, rows in zip(bars, df["记录数"]):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{rows / 1_000_000:.1f}M",
            ha="center", va="bottom", fontsize=10,
        )
    axes[1].set_ylim(0, df["记录数"].max() / 1_000_000 * 1.15)

    plt.tight_layout()
    if save_to:
        fig.savefig(save_to, bbox_inches="tight")
    return fig


def plot_quality_scorecard(
    scores: pd.DataFrame,
    save_to: str | Path | None = None,
) -> plt.Figure:
    """2-subplot figure: grouped bar (4 dims per system) + horizontal bar (综合得分).

    Args:
        scores: from calc_quality_score() — rows=系统, cols=4 dims + 综合得分.
        save_to: optional path to save PNG.
    """
    _ensure_chinese_font()
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    dims = ["完整性", "一致性", "准确性", "唯一性"]
    x = np.arange(len(dims))
    width = 0.18
    systems = list(scores.index)

    for i, (sys_name, row) in enumerate(scores.iterrows()):
        axes[0].bar(
            x + i * width,
            row[dims],
            width,
            label=sys_name,
            color=SYSTEM_COLORS.get(sys_name, "#9E9E9E"),
            alpha=0.85,
        )

    axes[0].set_xlabel("质量维度", fontsize=12)
    axes[0].set_ylabel("评分", fontsize=12)
    axes[0].set_title("各系统四维质量评分", fontsize=14, fontweight="bold")
    axes[0].set_xticks(x + width * (len(systems) - 1) / 2)
    axes[0].set_xticklabels(dims, fontsize=11)
    axes[0].legend(fontsize=10)
    axes[0].set_ylim(80, 101)
    axes[0].axhline(y=90, color="red", linestyle="--", alpha=0.5, label="告警线(90分)")

    sorted_scores = scores["综合得分"].sort_values(ascending=True)
    bar_colors = ["#FF5722" if v < 90 else "#4CAF50" for v in sorted_scores]
    bars2 = axes[1].barh(
        sorted_scores.index,
        sorted_scores.values,
        color=bar_colors,
        alpha=0.85,
        edgecolor="white",
    )
    axes[1].set_xlabel("综合得分", fontsize=12)
    axes[1].set_title("各系统综合质量排名", fontsize=14, fontweight="bold")
    axes[1].set_xlim(85, 100)
    for bar, val in zip(bars2, sorted_scores.values):
        axes[1].text(
            val + 0.1,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}",
            va="center", ha="left", fontsize=11, fontweight="bold",
        )
    axes[1].axvline(x=90, color="red", linestyle="--", alpha=0.7, label="告警线")
    axes[1].legend()

    plt.tight_layout()
    if save_to:
        fig.savefig(save_to, bbox_inches="tight")
    return fig


def plot_security_levels(df: pd.DataFrame, save_to: str | Path | None = None) -> plt.Figure:
    """Single bar chart: 4 datasets colored by security level.

    Args:
        df: 4-row DataFrame with columns: 系统 (e.g. "PI-System"), 高度 (0-100), 标签.
        save_to: optional path to save PNG.
    """
    _ensure_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 4))

    color_map = {"核心资产": "#F44336", "重要资产": "#FF9800", "一般资产": "#FFC107"}
    colors = [color_map.get(level, "#9E9E9E") for level in df["安全级别"]]

    bars = ax.bar(
        df["系统"],
        df["高度"],
        color=colors,
        width=0.5,
        alpha=0.85,
        edgecolor="white",
        linewidth=2,
    )
    ax.set_ylim(0, 115)
    ax.set_ylabel("安全等级 (0-100)", fontsize=12)
    ax.set_title("数据资产安全分级", fontsize=14, fontweight="bold")
    ax.axhline(y=90, color="red", linestyle="--", alpha=0.5)
    ax.text(len(df) - 0.4, 91, "核心/重要边界", fontsize=9, color="red")

    for bar, h, label in zip(bars, df["高度"], df["标签"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + 1.5,
            label,
            ha="center", va="bottom", fontsize=10, fontweight="bold",
            color="#333333",
        )

    plt.tight_layout()
    if save_to:
        fig.savefig(save_to, bbox_inches="tight")
    return fig


def plot_business_impact(
    impacts: list[dict[str, float | str]],
    save_to: str | Path | None = None,
) -> plt.Figure:
    """Horizontal bar chart: alert_key -> 元/年 (教学示意).

    Args:
        impacts: list of dicts, each with keys: alert_key, label, total_yuan.
        save_to: optional path to save PNG.
    """
    _ensure_chinese_font()
    fig, ax = plt.subplots(figsize=(10, max(4, 0.6 * len(impacts) + 2)))

    impacts_sorted = sorted(impacts, key=lambda x: float(x["total_yuan"]))
    labels = [str(x["label"]) for x in impacts_sorted]
    values = [float(x["total_yuan"]) for x in impacts_sorted]

    colors = ["#F44336" if v > 100_000 else "#FF9800" if v > 10_000 else "#4CAF50" for v in values]
    bars = ax.barh(labels, values, color=colors, alpha=0.85, edgecolor="white")
    ax.set_xlabel("年成本（元，教学参考值）", fontsize=12)
    ax.set_title("数据质量告警业务影响（教学示意）", fontsize=14, fontweight="bold")
    ax.set_xscale("log")
    for bar, v in zip(bars, values):
        ax.text(
            v * 1.1,
            bar.get_y() + bar.get_height() / 2,
            f"{v:,.0f} 元",
            va="center", ha="left", fontsize=10,
        )

    plt.tight_layout()
    if save_to:
        fig.savefig(save_to, bbox_inches="tight")
    return fig


# ============================================================
# 模块二新增：根因 / 告警聚合可视化
# ============================================================


def plot_root_cause_distribution(
    by_group: "pd.Series | dict[str, int]",
    title: str,
    xlabel: str = "数量",
    save_to: str | Path | None = None,
) -> plt.Figure:
    """Horizontal bar chart for any single-dimension distribution (e.g. by_tag, by_auart).

    Args:
        by_group: pd.Series (index=标签, value=数量) or dict {标签: 数量}
        title: 图表标题（中文）
        xlabel: x 轴标签，默认"数量"
        save_to: optional path to save PNG.
    """
    _ensure_chinese_font()

    # Normalize to pd.Series
    if isinstance(by_group, dict):
        items = sorted(by_group.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [str(k) for k, _ in items]
        values = [int(v) for _, v in items]
    else:
        # pd.Series — limit to top 10
        top = by_group.sort_values(ascending=False).head(10)
        labels = [str(i) for i in top.index]
        values = [int(v) for v in top.values]

    fig, ax = plt.subplots(figsize=(10, max(3, 0.45 * len(labels) + 1.5)))

    if not values:
        ax.text(0.5, 0.5, "无数据", ha="center", va="center", fontsize=14, color="gray")
        ax.set_title(title, fontsize=14, fontweight="bold")
        return fig

    max_v = max(values)
    colors = ["#F44336" if v > max_v * 0.5 else "#FF9800" if v > max_v * 0.25 else "#4CAF50" for v in values]
    bars = ax.barh(labels[::-1], values[::-1], color=colors, alpha=0.85, edgecolor="white")
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlim(0, max_v * 1.15)
    for bar, v in zip(bars, values[::-1]):
        ax.text(
            v + max_v * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{v:,}",
            va="center", ha="left", fontsize=10,
        )

    plt.tight_layout()
    if save_to:
        fig.savefig(save_to, bbox_inches="tight")
    return fig


def plot_alert_heatmap(
    matrix: "pd.DataFrame",
    save_to: str | Path | None = None,
) -> plt.Figure:
    """Heatmap of system × alert type. Cells = impact (rows / pct). Color: red=high, green=low.

    Args:
        matrix: DataFrame, index=系统 (rows), columns=告警类型 (cols), values=数值（行数或百分比）
        save_to: optional path to save PNG.
    """
    _ensure_chinese_font()
    import numpy as np

    fig, ax = plt.subplots(figsize=(max(8, 0.9 * len(matrix.columns) + 4), max(3, 0.7 * len(matrix.index) + 2)))

    if matrix.empty or matrix.size == 0:
        ax.text(0.5, 0.5, "无告警数据", ha="center", va="center", fontsize=14, color="gray")
        return fig

    data = matrix.fillna(0).astype(float).values
    # Use log1p to compress huge range (e.g. 60K vs 1.8K)
    log_data = np.log1p(data)

    im = ax.imshow(log_data, cmap="RdYlGn_r", aspect="auto")
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=30, ha="right", fontsize=10)
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index, fontsize=10)
    ax.set_title("数据质量告警热力图（颜色越红=越严重）", fontsize=14, fontweight="bold")

    # Annotate cells with actual values
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            text_color = "white" if log_data[i, j] > log_data.max() * 0.5 else "black"
            if val >= 1000:
                label = f"{val / 1000:.1f}K"
            elif val > 0:
                label = f"{val:.0f}"
            else:
                label = "—"
            ax.text(j, i, label, ha="center", va="center", fontsize=9, color=text_color, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("影响行数 (log scale)", fontsize=10)

    plt.tight_layout()
    if save_to:
        fig.savefig(save_to, bbox_inches="tight")
    return fig


def plot_system_alert_summary(
    report: dict,
    save_to: str | Path | None = None,
) -> plt.Figure:
    """Per-system bar chart: total rules (blue) + failed rules (red) side-by-side.

    Args:
        report: GE scan report dict (from run_ge_scan()), with key "results": {system: [table_results]}
        save_to: optional path to save PNG.
    """
    _ensure_chinese_font()
    import numpy as np

    systems: list[str] = []
    totals: list[int] = []
    failed: list[int] = []
    scores: list[float] = []
    for sys_name, sys_results in report.get("results", {}).items():
        sys_total = sum(int(t.get("total", 0)) for t in sys_results)
        sys_passed = sum(int(t.get("passed", 0)) for t in sys_results)
        sys_failed = sys_total - sys_passed
        systems.append(sys_name)
        totals.append(sys_total)
        failed.append(sys_failed)
        # find score from summary
        for s in report.get("summary", []):
            if s.get("system") == sys_name:
                scores.append(float(s.get("score", 0)))
                break
        else:
            scores.append(0.0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    x = np.arange(len(systems))
    width = 0.35
    axes[0].bar(x - width / 2, totals, width, label="总规则数", color="#2196F3", alpha=0.85, edgecolor="white")
    axes[0].bar(x + width / 2, failed, width, label="失败规则数", color="#F44336", alpha=0.85, edgecolor="white")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(systems, fontsize=11)
    axes[0].set_ylabel("规则数", fontsize=12)
    axes[0].set_title("各系统 GE 规则数 vs 失败数", fontsize=14, fontweight="bold")
    axes[0].legend(fontsize=10)
    for i, (t, f) in enumerate(zip(totals, failed)):
        axes[0].text(i - width / 2, t + 0.3, str(t), ha="center", fontsize=9, fontweight="bold")
        if f > 0:
            axes[0].text(i + width / 2, f + 0.3, str(f), ha="center", fontsize=9, fontweight="bold", color="#F44336")

    # Right plot: overall score with grade color
    grade_colors = []
    for sc in scores:
        if sc >= 95:
            grade_colors.append("#4CAF50")
        elif sc >= 85:
            grade_colors.append("#8BC34A")
        elif sc >= 70:
            grade_colors.append("#FF9800")
        else:
            grade_colors.append("#F44336")
    bars = axes[1].bar(systems, scores, color=grade_colors, alpha=0.85, edgecolor="white", linewidth=2)
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("综合得分", fontsize=12)
    axes[1].set_title("各系统综合质量评分", fontsize=14, fontweight="bold")
    axes[1].axhline(y=90, color="red", linestyle="--", alpha=0.5, label="告警线(90分)")
    axes[1].axhline(y=70, color="orange", linestyle="--", alpha=0.5, label="及格线(70分)")
    axes[1].legend(fontsize=9, loc="lower right")
    for bar, sc in zip(bars, scores):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            sc + 1.5,
            f"{sc:.1f}",
            ha="center", va="bottom", fontsize=11, fontweight="bold",
        )

    plt.tight_layout()
    if save_to:
        fig.savefig(save_to, bbox_inches="tight")
    return fig
