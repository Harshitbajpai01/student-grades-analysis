"""
Static (Matplotlib / Seaborn) chart pack.

The interactive dashboard uses Plotly, but downloads and the PDF report need
portable raster images, so the same analysis is rendered here with Matplotlib.
Both layers read from the identical computed dataframes, so the numbers always match.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib

matplotlib.use("Agg")  # headless rendering for servers / CI

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from .config import (
    CATEGORY_COLORS,
    ensure_dir,
    CATEGORY_ORDER,
    ETHNICITY_COLORS,
    GENDER_COLORS,
    PALETTE,
)

NAVY = PALETTE["navy"]
NAVY_SOFT = PALETTE["navy_soft"]
GRID = PALETTE["grid"]
PURPLE = PALETTE["purple"]
BLUE = PALETTE["blue"]

# Global Matplotlib look: light canvas, navy type, no chart junk.
plt.rcParams.update({
    "figure.facecolor": "#FFFFFF",
    "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": GRID,
    "axes.labelcolor": NAVY_SOFT,
    "axes.titlecolor": NAVY,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 10.5,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.9,
    "xtick.color": NAVY_SOFT,
    "ytick.color": NAVY_SOFT,
    "text.color": NAVY,
    "font.family": "DejaVu Sans",
    "legend.frameon": False,
    "legend.fontsize": 9.5,
})


def _figure(width: float = 7.4, height: float = 4.2) -> Tuple[Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height), dpi=160)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return fig, ax


def _empty(ax, message: str = "No data available") -> Figure:
    ax.text(0.5, 0.5, message, ha="center", va="center", color=NAVY_SOFT, fontsize=11)
    ax.set_axis_off()
    return ax.figure


# --------------------------------------------------------------------------------------
# Individual charts
# --------------------------------------------------------------------------------------
def gender_average_bar(summary: pd.DataFrame, grade_basis: str = "G3", metric: str = "Average Marks") -> Figure:
    fig, ax = _figure()
    if summary is None or summary.empty:
        return _empty(ax)
    colors = [GENDER_COLORS.get(g, PURPLE) for g in summary["Gender"]]
    bars = ax.bar(summary["Gender"], summary[metric], color=colors, width=0.45, zorder=3)
    for bar, value in zip(bars, summary[metric]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.3, f"{value:.2f}",
                ha="center", va="bottom", fontsize=11, color=NAVY, fontweight="bold")
    ax.set_title(f"{metric} by gender ({grade_basis})", loc="left", pad=14)
    ax.set_ylabel("Marks (out of 20)")
    ax.set_ylim(0, max(22, float(summary[metric].max()) * 1.2))
    return fig


def gender_count_donut(values_map: Dict[str, pd.DataFrame], title: str = "Students by gender") -> Figure:
    fig, ax = plt.subplots(figsize=(5.6, 4.2), dpi=160)
    frame = values_map.get("Number of students")
    if frame is None or frame.empty:
        return _empty(ax)
    colors = [GENDER_COLORS.get(g, PURPLE) for g in frame["Gender"]]
    wedges, _texts, autotexts = ax.pie(
        frame["value"], labels=frame["Gender"], colors=colors, autopct="%1.1f%%",
        startangle=90, wedgeprops=dict(width=0.42, edgecolor="#FFFFFF", linewidth=3),
        pctdistance=0.79, textprops=dict(color=NAVY, fontsize=10),
    )
    for text in autotexts:
        text.set_color("#FFFFFF")
        text.set_fontweight("bold")
    total = int(frame["value"].sum())
    ax.text(0, 0, f"{total}\nstudents", ha="center", va="center",
            fontsize=15, color=NAVY, fontweight="bold")
    ax.set_title(title, loc="left", pad=14)
    return fig


def grade_histogram(df: pd.DataFrame, column: str = "G3", title: Optional[str] = None) -> Figure:
    fig, ax = _figure()
    if df is None or df.empty or column not in df.columns:
        return _empty(ax)
    bins = np.arange(-0.5, 21.5, 1)
    for gender in ["Female", "Male"]:
        subset = df[df["Gender"] == gender] if "Gender" in df.columns else df
        if subset.empty:
            continue
        ax.hist(subset[column], bins=bins, alpha=0.75,
                color=GENDER_COLORS[gender], edgecolor="#FFFFFF", linewidth=0.8, label=gender, zorder=3)
    ax.set_title(title or f"{column} grade distribution", loc="left", pad=14)
    ax.set_xlabel(f"{column} grade (0-20)")
    ax.set_ylabel("Number of students")
    ax.set_xticks(range(0, 21, 2))
    ax.legend()
    return fig


def grade_distribution_stacked(df: pd.DataFrame, column: str = "G3") -> Figure:
    """Stacked counts of exact grades per gender."""
    fig, ax = _figure(height=4.4)
    if df is None or df.empty or column not in df.columns:
        return _empty(ax)
    table = df.groupby([column, "Gender"]).size().unstack(fill_value=0)
    grades = table.index.astype(int)
    bottom = np.zeros(len(table))
    for gender in ["Female", "Male"]:
        if gender in table.columns:
            ax.bar(grades, table[gender].values, bottom=bottom,
                   color=GENDER_COLORS[gender], label=gender, width=0.85, zorder=3)
            bottom += table[gender].values
    ax.set_title(f"{column} grade distribution by gender", loc="left", pad=14)
    ax.set_xlabel(f"{column} grade")
    ax.set_ylabel("Students")
    ax.legend()
    return fig


def g1g2g3_comparison(progression: pd.DataFrame) -> Figure:
    fig, ax = _figure()
    if progression is None or progression.empty:
        return _empty(ax)
    assessments = ["G1", "G2", "G3"]
    width = 0.35
    positions = np.arange(len(assessments))
    for offset, gender in zip((-width / 2, width / 2), ["Female", "Male"]):
        frame = progression[progression["Gender"] == gender]
        values = [
            float(frame.loc[frame["Assessment"] == a, "Average marks"].iloc[0])
            if not frame.loc[frame["Assessment"] == a].empty else 0.0
            for a in assessments
        ]
        bars = ax.bar(positions + offset, values, width, color=GENDER_COLORS[gender],
                      label=gender, zorder=3)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.25, f"{value:.1f}",
                    ha="center", va="bottom", fontsize=9.5, color=NAVY)
    ax.set_xticks(positions)
    ax.set_xticklabels(assessments)
    ax.set_ylim(0, 22)
    ax.set_ylabel("Average marks (out of 20)")
    ax.set_title("G1 vs G2 vs G3 average marks by gender", loc="left", pad=14)
    ax.legend()
    return fig


def percentage_box(df: pd.DataFrame) -> Figure:
    fig, ax = _figure()
    if df is None or df.empty or "Percentage" not in df.columns:
        return _empty(ax)
    order = [g for g in ["Female", "Male"] if g in df["Gender"].unique()]
    data = [df.loc[df["Gender"] == g, "Percentage"].dropna().values for g in order]
    if not data:
        return _empty(ax)
    box = ax.boxplot(data, tick_labels=order, patch_artist=True, widths=0.42,
                     medianprops=dict(color=NAVY, linewidth=2),
                     flierprops=dict(marker="o", markersize=4, markerfacecolor=NAVY_SOFT,
                                     markeredgecolor="none", alpha=0.5))
    for patch, gender in zip(box["boxes"], order):
        patch.set_facecolor(GENDER_COLORS[gender])
        patch.set_alpha(0.45)
        patch.set_edgecolor(GENDER_COLORS[gender])
    means = [float(np.mean(d)) for d in data]
    ax.scatter(range(1, len(means) + 1), means, color=NAVY, zorder=5, s=32, label="Mean")
    ax.set_ylabel("Percentage (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Percentage distribution by gender", loc="left", pad=14)
    ax.legend()
    return fig


def performance_distribution_chart(distribution: pd.DataFrame) -> Figure:
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=160)
    if distribution is None or distribution.empty or distribution["Students"].sum() == 0:
        return _empty(ax)
    active = distribution[distribution["Students"] > 0]
    colors = [CATEGORY_COLORS.get(c, PURPLE) for c in active["Performance"]]
    wedges, _t, autotexts = ax.pie(
        active["Students"], labels=active["Performance"], colors=colors, autopct="%1.0f%%",
        startangle=90, wedgeprops=dict(width=0.44, edgecolor="#FFFFFF", linewidth=2.5),
        pctdistance=0.79, textprops=dict(color=NAVY, fontsize=9),
    )
    for text in autotexts:
        text.set_color("#FFFFFF")
        text.set_fontweight("bold")
        text.set_fontsize(9)
    ax.text(0, 0, f"{int(active['Students'].sum())}\nstudents", ha="center", va="center",
            fontsize=14, color=NAVY, fontweight="bold")
    ax.set_title("Performance category distribution", loc="left", pad=14)
    return fig


def ethnicity_pie_chart(summary: pd.DataFrame, column: str = "Total Marks") -> Figure:
    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=160)
    if summary is None or summary.empty:
        return _empty(ax)
    colors = [ETHNICITY_COLORS[i % len(ETHNICITY_COLORS)] for i in range(len(summary))]
    wedges, _texts, autotexts = ax.pie(
        summary[column], labels=summary["Ethnicity"], colors=colors, autopct="%1.1f%%",
        startangle=90, wedgeprops=dict(edgecolor="#FFFFFF", linewidth=2),
        textprops=dict(color=NAVY, fontsize=9.5),
    )
    for text in autotexts:
        text.set_color("#FFFFFF")
        text.set_fontweight("bold")
        text.set_fontsize(9)
    ax.set_title(f"Share of {column.lower()} by ethnicity", loc="left", pad=14)
    return fig


def ethnicity_average_bar(summary: pd.DataFrame) -> Figure:
    fig, ax = _figure(height=4.2)
    if summary is None or summary.empty:
        return _empty(ax)
    frame = summary.sort_values("Average Marks")
    colors = [ETHNICITY_COLORS[i % len(ETHNICITY_COLORS)] for i in range(len(frame))]
    bars = ax.barh(frame["Ethnicity"], frame["Average Marks"], color=colors, zorder=3, height=0.6)
    for bar, value in zip(bars, frame["Average Marks"]):
        ax.text(value + 0.15, bar.get_y() + bar.get_height() / 2, f"{value:.2f}",
                va="center", fontsize=9.5, color=NAVY)
    ax.set_xlabel("Average marks per student")
    ax.set_title("Average marks by ethnicity", loc="left", pad=14)
    return fig


def correlation_heatmap_chart(matrix: pd.DataFrame) -> Figure:
    if matrix is None or matrix.empty:
        fig, ax = _figure()
        return _empty(ax, "Not enough numeric variables")
    from .analysis import CORRELATION_LABELS

    labels = [CORRELATION_LABELS.get(c, c) for c in matrix.columns]
    size = max(6.6, 0.52 * len(labels) + 3.2)
    fig, ax = plt.subplots(figsize=(size, size * 0.86), dpi=160)
    sns.heatmap(
        matrix, annot=True, fmt=".2f", cmap="coolwarm", center=0, vmin=-1, vmax=1,
        square=True, linewidths=1.4, linecolor="#FFFFFF", ax=ax,
        annot_kws={"fontsize": 7.5, "color": NAVY},
        cbar_kws={"shrink": 0.72, "label": "Pearson r"},
        xticklabels=labels, yticklabels=labels,
    )
    ax.set_title("Correlation heatmap", loc="left", pad=14)
    ax.tick_params(axis="x", rotation=45, labelsize=8.5)
    ax.tick_params(axis="y", rotation=0, labelsize=8.5)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_horizontalalignment("right")
    return fig


def subject_comparison_chart(table: pd.DataFrame) -> Figure:
    fig, ax = _figure()
    if table is None or table.empty:
        return _empty(ax)
    bars = ax.bar(table["Subject"], table["Average marks"],
                  color=[PURPLE, BLUE][: len(table)], width=0.42, zorder=3)
    for bar, value in zip(bars, table["Average marks"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.2, f"{value:.2f}",
                ha="center", va="bottom", fontsize=11, color=NAVY, fontweight="bold")
    ax.set_ylim(0, 22)
    ax.set_ylabel("Average marks")
    ax.set_title("Mathematics vs Portuguese", loc="left", pad=14)
    return fig


# --------------------------------------------------------------------------------------
# Chart pack used by the PDF report and the screenshot assets
# --------------------------------------------------------------------------------------
def save_figure(fig: Figure, path: Union[str, Path], dpi: int = 170) -> Path:
    """Render a figure to PNG on disk (headless Agg backend, safe on servers)."""
    target = Path(path)
    ensure_dir(target.parent)
    fig.tight_layout()
    fig.savefig(target, dpi=dpi, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    return target


def build_chart_pack(
    df: pd.DataFrame,
    gender_summary_table: pd.DataFrame,
    values_map: Dict[str, pd.DataFrame],
    progression: pd.DataFrame,
    distribution: pd.DataFrame,
    correlation: pd.DataFrame,
    grade_basis_label: str,
    output_dir: Union[str, Path],
    ethnicity_table: Optional[pd.DataFrame] = None,
) -> List[Dict[str, Any]]:
    """
    Render every static chart to `output_dir` and return [{title, path}] in report order.
    """
    output_dir = ensure_dir(output_dir)
    charts: List[Dict[str, Any]] = []

    def add(title: str, fig: Optional[Figure], filename: str) -> None:
        if fig is None:
            return
        path = save_figure(fig, output_dir / filename)
        charts.append({"title": title, "path": path})

    add("Average marks by gender", gender_average_bar(gender_summary_table, grade_basis_label),
        "01_gender_average_marks.png")
    add("Students by gender", gender_count_donut(values_map), "02_gender_student_count.png")
    add(f"{grade_basis_label} grade distribution", grade_histogram(df, "G3" if "G3" in df.columns else "Marks"),
        "03_grade_histogram.png")
    add("Grade distribution by gender", grade_distribution_stacked(df, "G3" if "G3" in df.columns else "Marks"),
        "04_grade_distribution_by_gender.png")
    add("G1 vs G2 vs G3 comparison", g1g2g3_comparison(progression), "05_g1_g2_g3_comparison.png")
    add("Percentage distribution by gender", percentage_box(df), "06_gender_percentage.png")
    add("Performance category distribution", performance_distribution_chart(distribution),
        "07_performance_distribution.png")
    add("Correlation heatmap", correlation_heatmap_chart(correlation), "08_correlation_heatmap.png")
    if ethnicity_table is not None and not ethnicity_table.empty:
        add("Total marks by ethnicity", ethnicity_pie_chart(ethnicity_table), "09_ethnicity_pie.png")
        add("Average marks by ethnicity", ethnicity_average_bar(ethnicity_table), "10_ethnicity_average.png")
    return charts
