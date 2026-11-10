"""
Shared analysis pipeline.

Both the Streamlit dashboard and the command-line runner use these functions, so the
numbers in the UI, the CSVs and the PDF can never drift apart.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import pandas as pd

from . import analysis, data_loader, ethnicity as ethnicity_module, static_charts
from .config import DEFAULT_GRADE_BASIS, DEFAULT_THRESHOLDS, SUBJECTS, ensure_dir


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------
def subject_keys(choice: str) -> List[str]:
    """Translate the UI choice into concrete subject keys."""
    if choice == "Both subjects":
        return list(SUBJECTS.keys())
    return [choice]


def load_and_clean(
    choice: str,
    uploaded: Optional[Dict[str, bytes]] = None,
) -> Tuple[pd.DataFrame, List[pd.DataFrame], Dict[str, Dict[str, Any]], List[str]]:
    """
    Load, validate and clean one or both subject files.

    Returns (combined_frame, cleaning_logs, validation_reports, errors).
    A missing/failed subject does not abort the run; the error is returned so the UI can
    show it in context.
    """
    uploaded = uploaded or {}
    frames: List[pd.DataFrame] = []
    logs: List[pd.DataFrame] = []
    validations: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []

    for subject in subject_keys(choice):
        try:
            payload = uploaded.get(subject)
            raw = data_loader.load_subject(subject, payload)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            errors.append(f"{subject}: {exc}")
            continue

        validations[subject] = data_loader.validate_dataset(raw)
        cleaned, log = data_loader.clean_dataset(raw)
        cleaned["Subject"] = subject
        cleaned = data_loader.assign_student_ids(cleaned)
        frames.append(cleaned)

        if log:
            log_frame = pd.DataFrame(log)
            log_frame.insert(0, "Subject", subject)
            logs.append(log_frame)

    if not frames:
        return pd.DataFrame(), logs, validations, errors

    combined = pd.concat(frames, ignore_index=True)
    return combined, logs, validations, errors


def attach_ethnicity(
    df: pd.DataFrame,
    ethnicity_bytes: Optional[bytes],
    filename: str = "",
    ethnicity_column: Optional[str] = None,
    mode: str = "Auto detect",
) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]], Optional[str]]:
    """
    Merge optional ethnicity data. Returns (frame, info, error).

    Never invents an ethnicity column: with no upload the frame is returned untouched.
    """
    if not ethnicity_bytes:
        return df, None, None
    if df.empty:
        return df, None, "Load a student dataset before attaching ethnicity data."
    try:
        if "Ethnicity" in df.columns:
            df = df.drop(columns=["Ethnicity"])
        merged, info = ethnicity_module.merge_ethnicity(
            df, ethnicity_bytes, filename=filename,
            ethnicity_column=ethnicity_column, mode=mode,
        )
        return merged, info, None
    except Exception as exc:  # noqa: BLE001
        return df, None, str(exc)


def migrate_ethnicity_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Rename a chosen ethnicity column to the canonical 'Ethnicity' name."""
    if column in df.columns and column != "Ethnicity":
        return df.rename(columns={column: "Ethnicity"})
    return df


# --------------------------------------------------------------------------------------
# Analysis bundle
# --------------------------------------------------------------------------------------
def build_analysis_bundle(
    base: pd.DataFrame,
    basis_label: str = DEFAULT_GRADE_BASIS,
    thresholds: Optional[Dict[str, float]] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Produce every derived table the dashboard and report need from a cleaned frame.

    Steps: derive calculated columns -> apply the selected grade basis -> apply filters
    -> compute the four objective tables plus supporting analytics.
    """
    limits = thresholds or DEFAULT_THRESHOLDS
    if base.empty:
        return {
            "frame": base, "gender_summary": pd.DataFrame(), "percentage_report": pd.DataFrame(),
            "percentage_bands": pd.DataFrame(), "division": pd.DataFrame(), "distribution": pd.DataFrame(),
            "gender_values": {}, "grade_distribution": pd.DataFrame(), "progression": pd.DataFrame(),
            "correlation": pd.DataFrame(), "correlations": pd.DataFrame(), "kpis": analysis.kpi_metrics(base),
        }

    derived = data_loader.add_derived_columns(base, limits)
    derived = data_loader.with_basis_columns(derived, basis_label, limits)

    active_filters = filters or {}
    filtered = data_loader.apply_filters(
        derived,
        genders=active_filters.get("genders"),
        schools=active_filters.get("schools"),
        age_groups=active_filters.get("age_groups"),
        categories=active_filters.get("categories"),
        grade_range=active_filters.get("grade_range"),
    )

    bundle: Dict[str, Any] = {
        "frame": filtered,
        "kpis": analysis.kpi_metrics(filtered),
        "gender_summary": analysis.gender_summary(filtered, basis_label),
        "percentage_report": analysis.percentage_report(filtered),
        "percentage_bands": analysis.percentage_band_summary(filtered),
        "distribution": analysis.performance_distribution(filtered),
        "gender_values": analysis.gender_metric_values(filtered),
        "grade_distribution": analysis.grade_distribution_by_gender(filtered, "G3" if "G3" in filtered else "Marks"),
        "progression": analysis.g1_g2_g3_by_gender(filtered),
        "correlation": analysis.correlation_matrix(filtered),
        "correlations": analysis.strongest_correlations(filtered),
        "basis_label": basis_label,
        "thresholds": limits,
    }
    return bundle


# --------------------------------------------------------------------------------------
# Exports (used by both UI and CLI)
# --------------------------------------------------------------------------------------
def write_report_outputs(
    bundle: Dict[str, Any],
    output_dir: Union[str, Path],
    chart_dir: Union[str, Path],
    subject_label: str,
    cleaning_logs: Optional[List[pd.DataFrame]] = None,
    validation_reports: Optional[Dict[str, Dict[str, Any]]] = None,
    ethnicity_info: Optional[Dict[str, Any]] = None,
    ethnicity_table: Optional[pd.DataFrame] = None,
    subject_comparison: Optional[pd.DataFrame] = None,
    prefix: str = "",
) -> Dict[str, Any]:
    """
    Write cleaned data, CSVs, chart PNGs and the PDF report to disk.

    Returns a dictionary of the generated paths.
    """
    output_dir = ensure_dir(output_dir)
    chart_dir = ensure_dir(chart_dir)
    df = bundle["frame"]
    slug = prefix or "student_grades"

    paths: Dict[str, Any] = {}
    paths["cleaned_dataset"] = output_dir / f"{slug}_cleaned_dataset.csv"
    df.to_csv(paths["cleaned_dataset"], index=False)

    paths["gender_analysis"] = output_dir / f"{slug}_gender_analysis.csv"
    (bundle["gender_summary"] if not bundle["gender_summary"].empty else pd.DataFrame()).to_csv(
        paths["gender_analysis"], index=False)

    paths["percentage_report"] = output_dir / f"{slug}_percentage_report.csv"
    bundle["percentage_report"].to_csv(paths["percentage_report"], index=False)

    paths["percentage_bands"] = output_dir / f"{slug}_percentage_bands.csv"
    bundle["percentage_bands"].to_csv(paths["percentage_bands"], index=False)

    if ethnicity_table is not None and not ethnicity_table.empty:
        paths["ethnicity_analysis"] = output_dir / f"{slug}_ethnicity_analysis.csv"
        ethnicity_table.to_csv(paths["ethnicity_analysis"], index=False)

    charts = static_charts.build_chart_pack(
        df=df,
        gender_summary_table=bundle["gender_summary"],
        values_map=bundle["gender_values"],
        progression=bundle["progression"],
        distribution=bundle["distribution"],
        correlation=bundle["correlation"],
        grade_basis_label=bundle["basis_label"],
        output_dir=chart_dir,
        ethnicity_table=ethnicity_table,
    )
    paths["charts"] = charts

    cleaning_frame = pd.concat(cleaning_logs, ignore_index=True) if cleaning_logs else pd.DataFrame()
    facts = _dataset_facts(df, subject_label, validation_reports)

    top_students = bundle["percentage_report"].head(10) if not bundle["percentage_report"].empty else pd.DataFrame()

    best_group = analysis.best_performing_ethnicity(ethnicity_table) if ethnicity_table is not None else None

    from . import reports as reports_module

    paths["pdf"] = output_dir / f"{slug}_report.pdf"
    reports_module.build_pdf_report(
        output_path=paths["pdf"],
        subject_label=subject_label,
        grade_basis_label=bundle["basis_label"],
        kpis=bundle["kpis"],
        dataset_facts=facts,
        cleaning_log=cleaning_frame,
        gender_table=bundle["gender_summary"],
        percentage_band_table=bundle["percentage_bands"],
        correlation_table=bundle["correlations"],
        charts=charts,
        subject_comparison_table=subject_comparison,
        ethnicity_table=ethnicity_table,
        ethnicity_info=ethnicity_info,
        best_group=best_group,
        thresholds=bundle["thresholds"],
        top_students=top_students,
    )
    return paths


def _dataset_facts(
    df: pd.DataFrame,
    subject_label: str,
    validation_reports: Optional[Dict[str, Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """One-row-per-fact table describing the analysed dataset."""
    validation_reports = validation_reports or {}
    rows = [
        ("Subject selection", subject_label),
        ("Students analysed (after cleaning)", f"{len(df):,}"),
        ("Columns", str(df.shape[1])),
        ("Missing values remaining", str(int(df.isna().sum().sum()))),
        ("Duplicate rows remaining", str(int(df.duplicated().sum()))),
        ("Age range", f"{int(df['age'].min())}-{int(df['age'].max())}" if "age" in df else "-"),
        ("Schools", ", ".join(sorted(df["school"].dropna().unique())) if "school" in df else "-"),
        ("Female students", str(int((df.get("Gender") == "Female").sum()))),
        ("Male students", str(int((df.get("Gender") == "Male").sum()))),
        ("Grade scale", "0-20 per period (UCI)"),
    ]
    for subject, report in validation_reports.items():
        rows.append((
            f"Source records - {subject}",
            f"{report['n_rows']} rows, {report['n_columns']} columns, "
            f"{report['duplicate_rows']} duplicate(s), {report['total_missing']} missing value(s)",
        ))
    return pd.DataFrame(rows, columns=["Dataset attribute", "Value"])
