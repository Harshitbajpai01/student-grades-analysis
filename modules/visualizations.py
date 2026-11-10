"""
Interactive Plotly charts for the dashboard.

Every figure is built from the analysed dataframe, uses the project palette and is
returned for `st.plotly_chart`. Charts gracefully degrade to an informative
"no data" placeholder instead of raising when a filter empties the dataset.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .config import (
    CATEGORY_COLORS,
    CATEGORY_ORDER,
    ETHNICITY_COLORS,
    GENDER_COLORS,
    HEATMAP_SCALE,
    PALETTE,
    PLOTLY_FONT,
)

NAVY = PALETTE["navy"]
NAVY_SOFT = PALETTE["navy_soft"]
GRID = PALETTE["grid"]
PURPLE = PALETTE["purple"]
BLUE = PALETTE["blue"]


# --------------------------------------------------------------------------------------
# Shared styling
# --------------------------------------------------------------------------------------
def style_figure(fig: go.Figure, title: str, height: int = 400, show_legend: bool = True) -> go.Figure:
    """Apply the dashboard's visual language to any Plotly figure."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, color=NAVY, family=PLOTLY_FONT),
            x=0.015,
            xanchor="left",
            y=0.95,
        ),
        height=height,
        margin=dict(l=12, r=16, t=64, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOTLY_FONT, color=NAVY_SOFT, size=13),
        showlegend=show_legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=NAVY_SOFT),
        ),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_color=NAVY, bordercolor=GRID),
        colorway=[PURPLE, BLUE, PALETTE["teal"], PALETTE["amber"], PALETTE["rose"]],
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=NAVY_SOFT), title_font=dict(size=12))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=NAVY_SOFT), title_font=dict(size=12))
    return fig


def empty_figure(message: str = "No data available for the current filters") -> go.Figure:
    """Clearly labelled placeholder so an empty state never looks like a bug."""
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(size=14, color=NAVY_SOFT, family=PLOTLY_FONT),
    )
    fig.update_layout(
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=16, r=16, t=16, b=16),
    )
    return fig


# --------------------------------------------------------------------------------------
# Objective 2: gender comparison charts
# --------------------------------------------------------------------------------------
def gender_metric_bar(
    values: pd.DataFrame,
    metric_label: str,
    title: Optional[str] = None,
    max_value: Optional[float] = None,
) -> go.Figure:
    """
    Bar chart of one metric (average / min / max marks or student count) by gender.

    `values` must contain Gender and value columns (from analysis.gender_metric_values).
    """
    if values is None or values.empty:
        return empty_figure(f"No {metric_label.lower()} data available")

    fig = go.Figure()
    for _, row in values.iterrows():
        gender = row["Gender"]
        fig.add_trace(go.Bar(
            x=[gender],
            y=[row["value"]],
            name=gender,
            marker=dict(
                color=GENDER_COLORS.get(gender, PURPLE),
                line=dict(width=0),
                cornerradius=8,
            ),
            text=[f"{row['value']:.2f}" if metric_label != "Number of students" else f"{int(row['value'])}"],
            textposition="outside",
            textfont=dict(color=NAVY, size=13),
            hovertemplate=f"<b>{gender}</b><br>{metric_label}: %{{y:.2f}}<extra></extra>",
            width=0.45,
        ))

    fig.update_layout(barmode="group")
    if max_value:
        fig.update_yaxes(range=[0, max_value * 1.18])
    style_figure(fig, title or f"{metric_label} by gender", height=380, show_legend=False)
    fig.update_yaxes(title_text=metric_label)
    fig.update_xaxes(title_text="")
    return fig


def gender_average_chart(summary: pd.DataFrame, grade_basis: str = "G3") -> go.Figure:
    """Compact average-marks bar chart built directly from the gender summary table."""
    if summary is None or summary.empty:
        return empty_figure("No gender statistics available")

    fig = go.Figure(go.Bar(
        x=summary["Gender"],
        y=summary["Average Marks"],
        marker=dict(
            color=[GENDER_COLORS.get(g, PURPLE) for g in summary["Gender"]],
            cornerradius=8,
        ),
        text=[f"{v:.2f}" for v in summary["Average Marks"]],
        textposition="outside",
        textfont=dict(color=NAVY, size=13),
        width=0.45,
        hovertemplate="<b>%{x}</b><br>Average marks: %{y:.2f}<extra></extra>",
    ))
    style_figure(fig, f"Average marks by gender ({grade_basis})", height=380, show_legend=False)
    fig.update_yaxes(title_text="Average marks")
    return fig


def gender_grouped_bar(values_map: dict, title: str = "Gender performance comparison") -> go.Figure:
    """Grouped bar comparing average, minimum and maximum marks for both genders."""
    metrics = ["Average marks", "Minimum marks", "Maximum marks"]
    available = {m: values_map[m] for m in metrics if m in values_map and not values_map[m].empty}
    if not available:
        return empty_figure("No gender comparison data available")

    fig = go.Figure()
    for gender in ["Female", "Male"]:
        y_values = []
        for metric in metrics:
            frame = available.get(metric)
            if frame is None:
                y_values.append(None)
                continue
            match = frame[frame["Gender"] == gender]
            y_values.append(float(match["value"].iloc[0]) if not match.empty else None)
        fig.add_trace(go.Bar(
            name=gender,
            x=metrics,
            y=y_values,
            marker=dict(color=GENDER_COLORS[gender], cornerradius=6),
            hovertemplate="<b>%{x}</b><br>" + gender + ": %{y:.2f}<extra></extra>",
            text=[f"{v:.1f}" if v is not None and not pd.isna(v) else "" for v in y_values],
            textposition="outside",
            textfont=dict(color=NAVY, size=12),
        ))
    fig.update_layout(barmode="group")
    style_figure(fig, title, height=400)
    fig.update_yaxes(title_text="Marks (out of 20)")
    return fig


def gender_count_chart(values: pd.DataFrame, title: str = "Number of students by gender") -> go.Figure:
    """Donut showing the gender split with counts."""
    if values is None or values.empty:
        return empty_figure("No student records available")
    fig = go.Figure(go.Pie(
        labels=values["Gender"],
        values=values["value"],
        hole=0.58,
        marker=dict(colors=[GENDER_COLORS.get(g, PURPLE) for g in values["Gender"]],
                    line=dict(color="#FFFFFF", width=3)),
        textinfo="label+percent",
        textfont=dict(size=13, color="#FFFFFF", family=PLOTLY_FONT),
        hovertemplate="<b>%{label}</b><br>Students: %{value}<br>Share: %{percent}<extra></extra>",
        sort=False,
    ))
    total = int(values["value"].sum())
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:11px'>students</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(size=20, color=NAVY, family=PLOTLY_FONT),
    )
    style_figure(fig, title, height=380, show_legend=False)
    return fig


def grade_distribution_chart(
    table: pd.DataFrame,
    column: str = "G3",
    title: Optional[str] = None,
) -> go.Figure:
    """Stacked bar of exact grade values, split by gender."""
    if table is None or table.empty:
        return empty_figure("No grade distribution available")

    fig = go.Figure()
    for gender in ["Female", "Male"]:
        if gender in table.columns:
            fig.add_trace(go.Bar(
                x=table[column],
                y=table[gender],
                name=gender,
                marker=dict(color=GENDER_COLORS[gender], cornerradius=4),
                hovertemplate="Grade %{x}<br>" + gender + ": %{y} students<extra></extra>",
            ))
    fig.update_layout(barmode="stack")
    style_figure(fig, title or f"Distribution of {column} grades by gender", height=400)
    fig.update_xaxes(title_text=f"{column} grade (0-20)", dtick=1)
    fig.update_yaxes(title_text="Number of students")
    return fig


def grade_histogram(
    df: pd.DataFrame,
    column: str = "G3",
    title: Optional[str] = None,
    bins: int = 20,
) -> go.Figure:
    """Histogram of a grade column with per-gender overlays."""
    if df is None or df.empty or column not in df.columns:
        return empty_figure(f"No {column} data available")

    fig = go.Figure()
    for gender in ["Female", "Male"]:
        subset = df[df["Gender"] == gender] if "Gender" in df.columns else df
        if subset.empty:
            continue
        fig.add_trace(go.Histogram(
            x=subset[column],
            name=gender,
            nbinsx=bins,
            marker=dict(color=GENDER_COLORS[gender]),
            opacity=0.78,
            hovertemplate="Grade %{x}<br>" + gender + ": %{y}<extra></extra>",
        ))
    fig.update_layout(barmode="overlay")
    style_figure(fig, title or f"{column} grade distribution", height=400)
    fig.update_xaxes(title_text=f"{column} grade (0-20)")
    fig.update_yaxes(title_text="Students")
    return fig


def g1_g2_g3_progression(progression: pd.DataFrame, title: str = "G1 vs G2 vs G3: average marks by gender") -> go.Figure:
    """Grouped bar showing how each gender progresses across the three periods."""
    if progression is None or progression.empty:
        return empty_figure("No assessment data available")

    fig = px.bar(
        progression,
        x="Assessment",
        y="Average marks",
        color="Gender",
        barmode="group",
        text="Average marks",
        color_discrete_map=GENDER_COLORS,
        category_orders={"Assessment": ["G1", "G2", "G3"]},
    )
    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
        textfont=dict(color=NAVY, size=12),
        marker=dict(cornerradius=6),
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.2f}<extra></extra>",
    )
    style_figure(fig, title, height=400)
    fig.update_yaxes(title_text="Average marks (out of 20)", range=[0, 22])
    fig.update_xaxes(title_text="Assessment period")
    return fig


def gender_percentage_comparison(df: pd.DataFrame, title: str = "Percentage distribution by gender") -> go.Figure:
    """Box plot of percentages per gender, with all student points overlaid."""
    if df is None or df.empty or "Percentage" not in df.columns:
        return empty_figure("No percentage data available")

    fig = go.Figure()
    for gender in ["Female", "Male"]:
        subset = df[df["Gender"] == gender]
        if subset.empty:
            continue
        fig.add_trace(go.Box(
            y=subset["Percentage"],
            name=gender,
            marker_color=GENDER_COLORS[gender],
            boxmean=True,
            boxpoints="all",
            jitter=0.4,
            pointpos=-1.6,
            line=dict(width=2),
            fillcolor=f"rgba({int(GENDER_COLORS[gender][1:3], 16)}, "
                      f"{int(GENDER_COLORS[gender][3:5], 16)}, "
                      f"{int(GENDER_COLORS[gender][5:7], 16)}, 0.22)",
            hovertemplate="<b>" + gender + "</b><br>Percentage: %{y:.2f}%<extra></extra>",
        ))
    style_figure(fig, title, height=440, show_legend=False)
    fig.update_yaxes(title_text="Percentage (%)")
    return fig


# --------------------------------------------------------------------------------------
# Objective 3: performance categories
# --------------------------------------------------------------------------------------
def performance_donut(distribution: pd.DataFrame, title: str = "Student performance distribution") -> go.Figure:
    """Donut of the performance-category split."""
    if distribution is None or distribution.empty or distribution["Students"].sum() == 0:
        return empty_figure("No performance categories available")

    active = distribution[distribution["Students"] > 0]
    fig = go.Figure(go.Pie(
        labels=active["Performance"],
        values=active["Students"],
        hole=0.55,
        marker=dict(
            colors=[CATEGORY_COLORS.get(c, PURPLE) for c in active["Performance"]],
            line=dict(color="#FFFFFF", width=3),
        ),
        textinfo="label+percent",
        textfont=dict(size=12, color="#FFFFFF", family=PLOTLY_FONT),
        hovertemplate="<b>%{label}</b><br>Students: %{value}<br>Share: %{percent}<extra></extra>",
        sort=False,
    ))
    total = int(active["Students"].sum())
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:11px'>students</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(size=20, color=NAVY, family=PLOTLY_FONT),
    )
    style_figure(fig, title, height=420, show_legend=False)
    return fig


def performance_category_bar(distribution: pd.DataFrame, title: str = "Students per performance category") -> go.Figure:
    """Horizontal bar of category counts."""
    if distribution is None or distribution.empty:
        return empty_figure("No performance categories available")
    fig = go.Figure(go.Bar(
        x=distribution["Students"],
        y=distribution["Performance"],
        orientation="h",
        marker=dict(
            color=[CATEGORY_COLORS.get(c, PURPLE) for c in distribution["Performance"]],
            cornerradius=6,
        ),
        text=[f"{int(v)} ({s:.1f}%)" for v, s in zip(distribution["Students"], distribution["Share"])],
        textposition="outside",
        textfont=dict(color=NAVY, size=12),
        hovertemplate="<b>%{y}</b><br>Students: %{x}<extra></extra>",
    ))
    style_figure(fig, title, height=380, show_legend=False)
    fig.update_xaxes(title_text="Number of students")
    fig.update_yaxes(title_text="", categoryorder="array",
                     categoryarray=list(reversed(CATEGORY_ORDER)))
    return fig


# --------------------------------------------------------------------------------------
# Objective 4: ethnicity charts
# --------------------------------------------------------------------------------------
def ethnicity_pie(summary: pd.DataFrame, title: str = "Distribution of total marks by ethnicity") -> go.Figure:
    """Pie chart of each group's share of all marks obtained."""
    if summary is None or summary.empty:
        return empty_figure("No ethnicity data available")
    colors = [ETHNICITY_COLORS[i % len(ETHNICITY_COLORS)] for i in range(len(summary))]
    fig = go.Figure(go.Pie(
        labels=summary["Ethnicity"],
        values=summary["Total Marks"],
        hole=0.28,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=3)),
        textinfo="label+percent",
        textfont=dict(size=12, color="#FFFFFF", family=PLOTLY_FONT),
        hovertemplate="<b>%{label}</b><br>Total marks: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        sort=False,
    ))
    style_figure(fig, title, height=440, show_legend=False)
    return fig


def ethnicity_average_bar(summary: pd.DataFrame, title: str = "Average marks by ethnicity") -> go.Figure:
    """Average marks per group, sorted best first, with the leader highlighted."""
    if summary is None or summary.empty:
        return empty_figure("No ethnicity data available")
    frame = summary.sort_values("Average Marks", ascending=True)
    colors = [ETHNICITY_COLORS[i % len(ETHNICITY_COLORS)] for i in range(len(frame))][::-1]
    if len(colors) >= 1:
        colors[-1] = PURPLE  # best performer on top

    fig = go.Figure(go.Bar(
        x=frame["Average Marks"],
        y=frame["Ethnicity"],
        orientation="h",
        marker=dict(color=colors, cornerradius=6),
        text=[f"{v:.2f}" for v in frame["Average Marks"]],
        textposition="outside",
        textfont=dict(color=NAVY, size=12),
        customdata=np.stack([frame["Students"], frame["Average Percentage"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>Average marks: %{x:.2f}<br>Students: %{customdata[0]}"
                      "<br>Average: %{customdata[1]:.2f}%<extra></extra>",
    ))
    style_figure(fig, title, height=max(340, 60 * len(frame) + 120), show_legend=False)
    fig.update_xaxes(title_text="Average marks per student")
    fig.update_yaxes(title_text="")
    return fig


# --------------------------------------------------------------------------------------
# Correlation + extras
# --------------------------------------------------------------------------------------
def correlation_heatmap(matrix: pd.DataFrame, title: str = "Correlation heatmap: academic and demographic variables") -> go.Figure:
    """Annotated heatmap of the Pearson correlation matrix."""
    if matrix is None or matrix.empty:
        return empty_figure("Not enough numeric variables for a correlation heatmap")

    from .analysis import CORRELATION_LABELS

    labels = [CORRELATION_LABELS.get(c, c) for c in matrix.columns]
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=labels,
        y=labels,
        colorscale=HEATMAP_SCALE,
        zmin=-1,
        zmax=1,
        text=matrix.values.round(2),
        texttemplate="%{text}",
        textfont=dict(size=9),
        hovertemplate="%{y} vs %{x}<br>r = %{z:.3f}<extra></extra>",
        colorbar=dict(title=dict(text="r", font=dict(color=NAVY_SOFT)), thickness=12),
        xgap=1.5,
        ygap=1.5,
    ))
    size = 760
    style_figure(fig, title, height=size, show_legend=False)
    fig.update_xaxes(tickangle=-45, showgrid=False, side="bottom")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_layout(margin=dict(l=90, r=20, t=70, b=110))
    return fig


def subject_comparison_bar(table: pd.DataFrame, title: str = "Mathematics vs Portuguese: average marks") -> go.Figure:
    """Compare the two subject cohorts."""
    if table is None or table.empty:
        return empty_figure("Select 'Both subjects' to compare cohorts")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=table["Subject"],
        y=table["Average marks"],
        name="Average marks",
        marker=dict(color=[PURPLE, BLUE][: len(table)], cornerradius=8),
        text=[f"{v:.2f}" for v in table["Average marks"]],
        textposition="outside",
        textfont=dict(color=NAVY, size=13),
        width=0.45,
        hovertemplate="<b>%{x}</b><br>Average marks: %{y:.2f}<extra></extra>",
    ))
    style_figure(fig, title, height=380, show_legend=False)
    fig.update_yaxes(title_text="Average marks (out of 20)", range=[0, 22])
    return fig


def study_time_scatter(df: pd.DataFrame, title: str = "Weekly study time vs final grade") -> go.Figure:
    """Scatter of study time against the final grade, coloured by gender."""
    if df is None or df.empty or "studytime" not in df.columns or "G3" not in df.columns:
        return empty_figure("Study time data unavailable")
    fig = px.scatter(
        df, x="studytime", y="G3", color="Gender",
        color_discrete_map=GENDER_COLORS,
        hover_data={"StudentID": True, "absences": True} if "StudentID" in df.columns else None,
        opacity=0.7,
    )
    fig.update_traces(marker=dict(size=8, line=dict(width=0)))
    style_figure(fig, title, height=420)
    fig.update_xaxes(title_text="Weekly study time (1 = <2h ... 4 = >10h)", dtick=1)
    fig.update_yaxes(title_text="Final grade G3")
    return fig
