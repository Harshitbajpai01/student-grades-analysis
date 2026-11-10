"""
Statistical analysis layer.

Every number the dashboard and the PDF report show is produced here with Pandas
`groupby` operations and NumPy - there are no hardcoded statistics anywhere.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .config import CATEGORY_ORDER, GENDER_LABELS, GRADE_COLUMNS, PALETTE
from .data_loader import FRIENDLY_NAMES, marks_series, percentage_series

# --------------------------------------------------------------------------------------
# KPI metrics
# --------------------------------------------------------------------------------------
def kpi_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    The KPI row of the dashboard. All values are computed from the *filtered* frame,
    so they update automatically whenever a filter changes.
    """
    if df.empty:
        return {
            "total_students": 0, "average_marks": np.nan, "highest_marks": np.nan,
            "lowest_marks": np.nan, "average_percentage": np.nan,
            "male_students": 0, "female_students": 0,
        }

    marks = df["Marks"] if "Marks" in df.columns else df.get("G3", pd.Series(dtype=float))
    percentage = df["Percentage"] if "Percentage" in df.columns else pd.Series(dtype=float)
    gender = df.get("Gender", pd.Series(dtype=object))

    return {
        "total_students": int(len(df)),
        "average_marks": float(np.nanmean(marks)) if len(marks.dropna()) else np.nan,
        "highest_marks": float(np.nanmax(marks)) if len(marks.dropna()) else np.nan,
        "lowest_marks": float(np.nanmin(marks)) if len(marks.dropna()) else np.nan,
        "average_percentage": float(np.nanmean(percentage)) if len(percentage.dropna()) else np.nan,
        "male_students": int((gender == GENDER_LABELS["M"]).sum()),
        "female_students": int((gender == GENDER_LABELS["F"]).sum()),
    }


# --------------------------------------------------------------------------------------
# Objective 1: gender-wise statistics
# --------------------------------------------------------------------------------------
def gender_summary(df: pd.DataFrame, basis_label: str) -> pd.DataFrame:
    """
    Objective 1: average / minimum / maximum marks, student count and average
    percentage for each gender, using the real `sex` column.

    Implemented with a single `groupby` aggregation so the numbers are verifiable.
    """
    if df.empty or "Gender" not in df.columns or "Marks" not in df.columns:
        return pd.DataFrame()

    grouped = df.groupby("Gender", dropna=True)
    summary = grouped.agg(
        Students=("Marks", "count"),
        **{
            "Average Marks": ("Marks", "mean"),
            "Minimum Marks": ("Marks", "min"),
            "Maximum Marks": ("Marks", "max"),
            "Median Marks": ("Marks", "median"),
            "Std. Deviation": ("Marks", "std"),
            "Average Percentage": ("Percentage", "mean"),
        },
    ).reset_index()

    summary = summary.sort_values("Gender", ascending=False).reset_index(drop=True)
    numeric_cols = [c for c in summary.columns if c not in ("Gender", "Students")]
    summary[numeric_cols] = summary[numeric_cols].round(2)
    summary["Grade basis"] = basis_label
    return summary


def gender_metric_values(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Numbers for the Objective 2 bar charts, one tidy frame per metric."""
    if df.empty or "Gender" not in df.columns:
        return {}
    grouped = df.groupby("Gender")["Marks"]
    return {
        "Average marks": grouped.mean().rename("value").reset_index(),
        "Minimum marks": grouped.min().rename("value").reset_index(),
        "Maximum marks": grouped.max().rename("value").reset_index(),
        "Number of students": grouped.count().astype(float).rename("value").reset_index(),
        "Average percentage": df.groupby("Gender")["Percentage"].mean().rename("value").reset_index(),
    }


def grade_distribution_by_gender(df: pd.DataFrame, column: str = "G3") -> pd.DataFrame:
    """Counts of each exact grade value per gender (for the stacked distribution chart)."""
    if df.empty or column not in df.columns or "Gender" not in df.columns:
        return pd.DataFrame()
    table = (
        df.groupby([column, "Gender"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
        .reset_index()
    )
    return table


def g1_g2_g3_by_gender(df: pd.DataFrame) -> pd.DataFrame:
    """Average of G1, G2 and G3 per gender, for the progression comparison chart."""
    available = [c for c in GRADE_COLUMNS if c in df.columns]
    if df.empty or not available or "Gender" not in df.columns:
        return pd.DataFrame()
    table = df.groupby("Gender")[available].mean().round(2).reset_index()
    return table.melt(id_vars="Gender", var_name="Assessment", value_name="Average marks")


# --------------------------------------------------------------------------------------
# Objective 3: percentage report
# --------------------------------------------------------------------------------------
def percentage_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Student level report: ID, gender, subject, grade, percentage and category.

    Expects `Marks`, `MaxMarks`, `Percentage` and `Performance` to already be set
    by `data_loader.with_basis_columns`.
    """
    if df.empty:
        return pd.DataFrame()

    columns = [
        c for c in [
            "StudentID", "Gender", "Subject", "school", "age",
            "G1", "G2", "G3", "Marks", "MaxMarks", "Percentage", "Performance",
        ] if c in df.columns
    ]
    report = df[columns].copy()
    if "Percentage" in report.columns:
        report["Percentage"] = report["Percentage"].round(2)
    rename = {c: FRIENDLY_NAMES.get(c, c) for c in ("school", "Marks", "MaxMarks", "Performance")}
    report = report.rename(columns=rename)
    sort_col = "Percentage" if "Percentage" in report.columns else None
    if sort_col:
        report = report.sort_values(sort_col, ascending=False).reset_index(drop=True)
    return report


def performance_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Count and share of students in each performance band (all bands kept, even 0)."""
    if df.empty or "Performance" not in df.columns:
        return pd.DataFrame(columns=["Performance", "Students", "Share"])
    counts = df["Performance"].value_counts().reindex(CATEGORY_ORDER).fillna(0)
    total = counts.sum()
    table = pd.DataFrame({
        "Performance": counts.index,
        "Students": counts.astype(int).values,
        "Share": (counts / total * 100).round(2).values if total else 0.0,
    })
    return table


def percentage_band_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Average percentage per performance band, useful for the report narrative."""
    if df.empty or "Performance" not in df.columns:
        return pd.DataFrame()
    table = (
        df.groupby("Performance")
        .agg(
            Students=("Percentage", "count"),
            **{
                "Average %": ("Percentage", "mean"),
                "Minimum %": ("Percentage", "min"),
                "Maximum %": ("Percentage", "max"),
            },
        )
        .reindex(CATEGORY_ORDER)
        .dropna(how="all")
        .reset_index()
    )
    for col in ["Average %", "Minimum %", "Maximum %"]:
        table[col] = table[col].round(2)
    table["Students"] = table["Students"].fillna(0).astype(int)
    return table


# --------------------------------------------------------------------------------------
# Objective 4: ethnicity (only ever from a real, uploaded ethnicity column)
# --------------------------------------------------------------------------------------
def ethnicity_summary(df: pd.DataFrame, ethnicity_column: str) -> pd.DataFrame:
    """
    Group students by a genuine ethnicity column and summarise performance.

    Returns one row per ethnicity with student count, total marks, average marks,
    minimum/maximum marks, average percentage and share of all marks.
    """
    if df.empty or ethnicity_column not in df.columns:
        return pd.DataFrame()

    work = df.dropna(subset=[ethnicity_column]).copy()
    if work.empty:
        return pd.DataFrame()

    value_column = "Marks" if "Marks" in work.columns else "TotalMarks"
    grouped = work.groupby(ethnicity_column)
    table = grouped.agg(
        Students=(value_column, "count"),
        **{
            "Total Marks": (value_column, "sum"),
            "Average Marks": (value_column, "mean"),
            "Minimum Marks": (value_column, "min"),
            "Maximum Marks": (value_column, "max"),
            "Average Percentage": ("Percentage", "mean"),
        },
    ).reset_index()

    table = table.rename(columns={ethnicity_column: "Ethnicity"})
    grand_total = table["Total Marks"].sum()
    table["Share of Marks %"] = (
        (table["Total Marks"] / grand_total * 100).round(2) if grand_total else 0.0
    )
    numeric_cols = ["Total Marks", "Average Marks", "Minimum Marks", "Maximum Marks", "Average Percentage"]
    table[numeric_cols] = table[numeric_cols].round(2)
    table["Students"] = table["Students"].astype(int)
    table = table.sort_values("Average Marks", ascending=False).reset_index(drop=True)
    return table


def best_performing_ethnicity(summary: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Identify the best performing group.

    Methodology (also printed in the UI): groups are ranked by **average marks per
    student** for the selected grade basis, because raw totals favour larger groups.
    Ties are broken by average percentage and then by the number of students.
    """
    if summary is None or summary.empty:
        return None
    ranked = summary.sort_values(
        ["Average Marks", "Average Percentage", "Students"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    top = ranked.iloc[0]
    runner_up = ranked.iloc[1] if len(ranked) > 1 else None
    return {
        "group": str(top["Ethnicity"]),
        "average_marks": float(top["Average Marks"]),
        "average_percentage": float(top["Average Percentage"]),
        "students": int(top["Students"]),
        "gap_to_second": float(top["Average Marks"] - runner_up["Average Marks"]) if runner_up is not None else np.nan,
        "runner_up": str(runner_up["Ethnicity"]) if runner_up is not None else None,
        "groups_compared": int(len(ranked)),
        "ranking": ranked,
    }


def student_marks_by_ethnicity(df: pd.DataFrame, ethnicity_column: str) -> pd.DataFrame:
    """Student-wise total marks by ethnicity (Objective 4 requirement)."""
    if df.empty or ethnicity_column not in df.columns:
        return pd.DataFrame()
    columns = [
        c for c in ["StudentID", ethnicity_column, "Gender", "Subject", "G1", "G2", "G3",
                    "TotalMarks", "Marks", "Percentage", "Performance"]
        if c in df.columns
    ]
    table = df[columns].rename(columns={ethnicity_column: "Ethnicity"}).copy()
    if "Percentage" in table.columns:
        table["Percentage"] = table["Percentage"].round(2)
    return table.sort_values(["Ethnicity", "Percentage"], ascending=[True, False]).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# Correlations and misc analytics
# --------------------------------------------------------------------------------------
CORRELATION_CANDIDATES = [
    "age", "Medu", "Fedu", "traveltime", "studytime", "failures", "famrel",
    "freetime", "goout", "Dalc", "Walc", "health", "absences", "G1", "G2", "G3",
]

CORRELATION_LABELS = {
    "age": "Age", "Medu": "Mother edu.", "Fedu": "Father edu.",
    "traveltime": "Travel time", "studytime": "Study time", "failures": "Failures",
    "famrel": "Family rel.", "freetime": "Free time", "goout": "Going out",
    "Dalc": "Workday alcohol", "Walc": "Weekend alcohol", "health": "Health",
    "absences": "Absences", "G1": "G1", "G2": "G2", "G3": "Final G3",
}


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation of every academic + demographic numeric variable."""
    columns = [c for c in CORRELATION_CANDIDATES if c in df.columns]
    if df.empty or len(columns) < 2:
        return pd.DataFrame()
    numeric = df[columns].apply(pd.to_numeric, errors="coerce")
    return numeric.corr(numeric_only=True).round(3)


def strongest_correlations(df: pd.DataFrame, target: str = "G3", top_n: int = 5) -> pd.DataFrame:
    """Which variables move most with the final grade (absolute correlation)."""
    matrix = correlation_matrix(df)
    if matrix.empty or target not in matrix.columns:
        return pd.DataFrame()
    series = matrix[target].drop(labels=[target], errors="ignore").dropna()
    if series.empty:
        return pd.DataFrame()
    ranked = series.reindex(series.abs().sort_values(ascending=False).index).head(top_n)
    return pd.DataFrame({
        "Variable": [CORRELATION_LABELS.get(v, v) for v in ranked.index],
        "Correlation with G3": ranked.values.round(3),
        "Direction": ["Positive" if v > 0 else "Negative" for v in ranked.values],
    })


def subject_comparison(frames: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare the Mathematics and Portuguese cohorts side by side."""
    rows = []
    for subject, frame in frames.items():
        if frame is None or frame.empty:
            continue
        rows.append({
            "Subject": subject,
            "Students": int(len(frame)),
            "Average marks": round(float(frame["Marks"].mean()), 2),
            "Average percentage": round(float(frame["Percentage"].mean()), 2),
            "Highest marks": float(frame["Marks"].max()),
            "Lowest marks": float(frame["Marks"].min()),
            "Pass rate (>=10/20)": round(float((frame["Marks"] >= 10).mean() * 100), 2)
                if "Marks" in frame else np.nan,
        })
    return pd.DataFrame(rows)


def descriptive_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Standard descriptive statistics table for the dataset explorer."""
    if df.empty:
        return pd.DataFrame()
    columns = [c for c in GRADE_COLUMNS + ["absences", "studytime", "age"] if c in df.columns]
    if not columns:
        return pd.DataFrame()
    stats = df[columns].describe().T.reset_index().rename(columns={"index": "Variable"})
    stats = stats.rename(columns={
        "count": "Count", "mean": "Mean", "std": "Std. Dev.", "min": "Min",
        "25%": "Q1", "50%": "Median", "75%": "Q3", "max": "Max",
    })
    numeric = [c for c in stats.columns if c != "Variable"]
    stats[numeric] = stats[numeric].round(2)
    return stats


def nominal_categorical_summary(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Value counts for a categorical column, used in the explorer."""
    if df.empty or column not in df.columns:
        return pd.DataFrame()
    counts = df[column].value_counts(dropna=False).reset_index()
    counts.columns = [FRIENDLY_NAMES.get(column, column), "Students"]
    return counts
