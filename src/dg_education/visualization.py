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
