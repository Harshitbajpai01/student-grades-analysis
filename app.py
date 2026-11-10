"""
Student Grades Analysis - interactive Streamlit dashboard.

Run with:  streamlit run app.py

Pages (sidebar navigation)
--------------------------
1. Overview            7 KPI cards, headline insights
2. Dataset Explorer    loading, validation, cleaning, preview, downloads
3. Gender Analysis     Objective 1 statistics + Objective 2 bar charts
4. Percentage Analysis Objective 3 percentage column and performance bands
5. Ethnicity Analysis  Objective 4, enabled by a genuine ethnicity dataset
6. Visualizations      the full chart gallery
7. Student Performance student-level browsing and detail
8. Download Reports    CSV, PNG and PDF exports
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from modules import analysis, data_loader, pipeline, reports
from modules import static_charts
from modules import visualizations as viz
from modules.config import (
    AGE_GROUP_ORDER,
    SAMPLE_ETHNICITY_PATH,
    CATEGORY_ORDER,
    DATASET_HOMEPAGE,
    DEFAULT_GRADE_BASIS,
    DEFAULT_THRESHOLDS,
    GENDER_LABELS,
    GRADE_BASES,
    PALETTE,
    SUBJECTS,
    SUBJECT_OPTIONS,
)
from modules.theme import (
    formula,
    hero,
    inject_css,
    kpi_row,
    notice,
    pill,
    section_title,
)

# --------------------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Student Grades Analysis",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

CTX: dict = {}
GENDERS = ["Female", "Male"]
SCHOOL_LABELS = {"GP": "GP (Gabriel Pereira)", "MS": "MS (Mousinho da Silveira)"}


# --------------------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------------------
def fmt(value, digits: int = 2, suffix: str = "") -> str:
    """Format a number for a KPI card, tolerating NaN and None."""
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if np.isnan(number):
        return "-"
    if digits == 0:
        return f"{number:,.0f}{suffix}"
    return f"{number:,.{digits}f}{suffix}"


def show_table(
    frame: pd.DataFrame,
    height: int | None = None,
    column_config: dict | None = None,
    empty_message: str = "No rows match the current filters.",
) -> None:
    """Render a dataframe, or a friendly notice when it is empty."""
    if frame is None or frame.empty:
        notice(empty_message, "info")
        return
    kwargs = {"width": "stretch", "hide_index": True, "column_config": column_config or {}}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(frame, **kwargs)


def percent_column_config(frame: pd.DataFrame) -> dict:
    """Progress-style column config for percentage columns."""
    config = {}
    for column in ("Average Percentage", "Percentage", "Share", "Share of Marks %",
                   "Average %", "Minimum %", "Maximum %"):
        if column in frame.columns:
            config[column] = st.column_config.ProgressColumn(
                column,
                format="%.2f%%",
                min_value=0.0,
                max_value=100.0,
            )
    return config


def chart_grade_frame(frame: pd.DataFrame, grade: str) -> pd.DataFrame:
    """
    Local view of the data for the grade selector on the Gender Analysis page.

    `grade` is one of G1, G2, G3 or 'Combined (G1+G2+G3)'. The percentage is
    recomputed against the matching maximum so all charts stay consistent.
    """
    view = frame.copy()
    if grade == "Combined (G1+G2+G3)":
        view["Marks"] = view[["G1", "G2", "G3"]].sum(axis=1)
        view["Percentage"] = view["Marks"] / 60.0 * 100.0
    else:
        view["Marks"] = view[grade]
        view["Percentage"] = view[grade] / 20.0 * 100.0
    return view


# --------------------------------------------------------------------------------------
# Data loading (cached)
# --------------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=8)
def load_dataset(subject_choice: str, upload_pairs: tuple):
    """
    Load and clean the selected subject files.

    Cached per subject selection and upload set, so switching pages or moving a
    filter never re-reads or re-cleans the CSVs. `max_entries` is deliberately small
    to keep memory low on Streamlit Community Cloud.
    """
    uploaded = {subject: payload for subject, payload in upload_pairs}
    base, logs, validations, errors = pipeline.load_and_clean(subject_choice, uploaded)
    return base, logs, validations, errors


@st.cache_data(show_spinner=False, max_entries=16)
def prepare_base_frame(base: pd.DataFrame, thresholds: tuple) -> pd.DataFrame:
    """Add TotalMarks / Percentage / Performance / AgeGroup once per threshold set."""
    return data_loader.add_derived_columns(base, dict(thresholds))


@st.cache_data(show_spinner=False, max_entries=16)
def prepare_full_frame(base: pd.DataFrame, basis: str, thresholds: tuple) -> pd.DataFrame:
    """Re-base marks and percentages on the selected grade basis (cached)."""
    return data_loader.with_basis_columns(base, basis, dict(thresholds))


def init_filter_state(subject_choice: str) -> None:
    """Create the sidebar widget state once so widgets can live below the nav."""
    defaults = {
        "flt_subject": "Both subjects",
        "flt_basis": DEFAULT_GRADE_BASIS,
        "flt_gender": GENDERS,
        "flt_school": [],
        "flt_age": [],
        "flt_category": [],
        "flt_show_thresholds": False,
        "thr_Excellent": DEFAULT_THRESHOLDS["Excellent"],
        "thr_Very Good": DEFAULT_THRESHOLDS["Very Good"],
        "thr_Good": DEFAULT_THRESHOLDS["Good"],
        "thr_Average": DEFAULT_THRESHOLDS["Average"],
        "thr_Needs Improvement": DEFAULT_THRESHOLDS["Needs Improvement"],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def current_thresholds() -> dict:
    """Read the configurable performance thresholds from the sidebar widgets."""
    got = {key: float(st.session_state.get(f"thr_{key}", value)) for key, value in DEFAULT_THRESHOLDS.items()}
    # Guard against impossible configurations that would break the banding.
    if len(set(got.values())) != len(got):
        notice("Thresholds must be distinct. Falling back to the project defaults for this run.", "warn")
        return dict(DEFAULT_THRESHOLDS)
    return got


def build_context() -> dict:
    """Run the full pipeline for the current sidebar selection and store the result."""
    subject_choice = st.session_state.get("flt_subject", "Both subjects")
    basis = st.session_state.get("flt_basis", DEFAULT_GRADE_BASIS)
    thresholds = current_thresholds()

    upload_pairs = tuple(
        (subject, payload)
        for subject, payload in (
            ("Mathematics", st.session_state.get("up_mat") and st.session_state["up_mat"].getvalue()),
            ("Portuguese", st.session_state.get("up_por") and st.session_state["up_por"].getvalue()),
        )
        if payload
    )

    base, logs, validations, errors = load_dataset(subject_choice, upload_pairs)
    if base is None or base.empty:
        return {"empty": True, "errors": errors, "base": pd.DataFrame()}

    base = prepare_base_frame(base, tuple(sorted(thresholds.items())))

    # Optional ethnicity mapping stored by the Ethnicity Analysis page.
    mapping = st.session_state.get("ethnicity_map")
    if mapping:
        base = base.copy()
        base["Ethnicity"] = base["StudentID"].map(mapping)

    full = prepare_full_frame(base, basis, tuple(sorted(thresholds.items())))

    range_key = f"flt_range_{grade_basis_max_safe(basis)}"
    grade_range = st.session_state.get(range_key, (0.0, grade_basis_max_safe(basis)))

    filtered = data_loader.apply_filters(
        full,
        genders=st.session_state.get("flt_gender", GENDERS),
        schools=st.session_state.get("flt_school", []),
        age_groups=st.session_state.get("flt_age", []),
        categories=st.session_state.get("flt_category", []),
        grade_range=grade_range,
    )

    return {
        "empty": False,
        "base": base,
        "full": full,
        "df": filtered,
        "logs": logs,
        "validations": validations,
        "errors": errors,
        "basis": basis,
        "thresholds": thresholds,
        "subject_choice": subject_choice,
        "ethnicity_info": st.session_state.get("ethnicity_info"),
    }


def grade_basis_max_safe(basis: str) -> float:
    return GRADE_BASES.get(basis, GRADE_BASES[DEFAULT_GRADE_BASIS])["max_marks"]


# --------------------------------------------------------------------------------------
# Sidebar filters (rendered after the navigation so the menu stays on top)
# --------------------------------------------------------------------------------------
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f"<div style='padding:6px 10px 2px 10px;font-size:0.68rem;font-weight:800;"
            f"letter-spacing:0.14em;text-transform:uppercase;color:{PALETTE['purple']}'>"
            f"Dashboard filters</div>",
            unsafe_allow_html=True,
        )

        st.selectbox(
            "Subject dataset",
            SUBJECT_OPTIONS,
            key="flt_subject",
            help="Mathematics (395 students), Portuguese (649 students), or both combined.",
        )
        st.selectbox(
            "Grade basis",
            list(GRADE_BASES.keys()),
            key="flt_basis",
            help="Marks, percentages and categories are recalculated for the chosen basis.",
        )

        with st.expander("Use your own CSV files", expanded=False):
            st.caption("Upload files with the same columns as the UCI dataset to analyse them instead.")
            st.file_uploader("student-mat.csv (Mathematics)", type="csv", key="up_mat")
            st.file_uploader("student-por.csv (Portuguese)", type="csv", key="up_por")

        st.multiselect("Gender", GENDERS, key="flt_gender")
        available_schools = sorted(CTX.get("full", pd.DataFrame()).get("school", pd.Series(dtype=str)).dropna().unique())
        if available_schools:
            st.multiselect(
                "School",
                available_schools,
                key="flt_school",
                format_func=lambda code: SCHOOL_LABELS.get(code, code),
            )
        st.multiselect("Age group", AGE_GROUP_ORDER, key="flt_age")

        max_marks = grade_basis_max_safe(st.session_state.get("flt_basis", DEFAULT_GRADE_BASIS))
        range_key = f"flt_range_{max_marks}"
        st.session_state.setdefault(range_key, (0.0, float(max_marks)))
        st.slider(
            "Grade range",
            min_value=0.0,
            max_value=float(max_marks),
            key=range_key,
            step=1.0,
            help="Filter students by the marks obtained on the selected grade basis.",
        )
        st.multiselect("Performance category", CATEGORY_ORDER, key="flt_category")

        with st.expander("Performance thresholds", expanded=False):
            st.caption("Lower bound of each band, in percent. Applied to every page.")
            for label in CATEGORY_ORDER:
                st.number_input(
                    label, min_value=0.0, max_value=100.0, step=1.0,
                    key=f"thr_{label}", format="%.0f",
                )

        st.divider()
        if st.button("Reset all filters", width="stretch"):
            for key in ["flt_subject", "flt_basis", "flt_gender", "flt_school", "flt_age",
                        "flt_category", "up_mat", "up_por", "ethnicity_map", "ethnicity_info",
                        "eth_signature", "report_pdf_bytes", "report_signature"]:
                st.session_state.pop(key, None)
            for key in list(st.session_state.keys()):
                if str(key).startswith("flt_range_"):
                    st.session_state.pop(key, None)
            for label in CATEGORY_ORDER:
                st.session_state.pop(f"thr_{label}", None)
            st.rerun()

        counts = len(CTX.get("df", []))
        total = len(CTX.get("full", []))
        st.caption(f"Showing **{counts:,}** of {total:,} students.")
        st.caption(f"[UCI Student Performance dataset]({DATASET_HOMEPAGE})")


# --------------------------------------------------------------------------------------
# Page 1: Overview
# --------------------------------------------------------------------------------------
def page_overview() -> None:
    df = CTX["df"]
    hero(
        "Academic performance analytics",
        "Student Grades Analysis",
        f"A statistical study of {len(df):,} student records from the UCI Student Performance dataset. "
        f"Objective: examine grades by gender and by demographic group, quantify the spread of results and "
        f"identify the best performing group. Grade basis: {CTX['basis']}.",
    )

    st.markdown(
        f"{pill(CTX['subject_choice'], 'purple')} &nbsp; {pill(CTX['basis'], 'blue')} &nbsp; "
        f"{pill('Dataset: UCI Student Performance', 'green')}",
        unsafe_allow_html=True,
    )
    st.write("")

    kpis = analysis.kpi_metrics(df)
    kpi_row([
        ("Total students", fmt(kpis["total_students"], 0), "records after filters"),
        ("Average marks", fmt(kpis["average_marks"]), f"out of {grade_basis_max_safe(CTX['basis']):g}"),
        ("Highest marks", fmt(kpis["highest_marks"], 0), "best result in view"),
        ("Lowest marks", fmt(kpis["lowest_marks"], 0), "lowest result in view"),
    ])
    st.write("")
    kpi_row([
        ("Average percentage", fmt(kpis["average_percentage"], 1, "%"), "marks obtained / maximum"),
        ("Female students", fmt(kpis["female_students"], 0), "from the sex column"),
        ("Male students", fmt(kpis["male_students"], 0), "from the sex column"),
    ])

    st.write("")
    left, right = st.columns([1.25, 1], gap="medium")

    with left:
        section_title("Average marks by gender", "Objective 1 and 2 at a glance")
        if not df.empty:
            summary = analysis.gender_summary(df, CTX["basis"])
            fig = viz.gender_average_chart(summary, CTX["basis"])
            if fig is not None:
                st.plotly_chart(fig, width="stretch", theme=None)
        else:
            notice("No students match the current filters. Widen the filters to see results.", "warn")

    with right:
        section_title("Performance bands", "Objective 3 classification")
        distribution = analysis.performance_distribution(df)
        if not distribution.empty and distribution["Students"].sum():
            st.plotly_chart(viz.performance_donut(distribution), width="stretch", theme=None)
        else:
            notice("No classified students in the current view.", "info")

    st.write("")
    left, right = st.columns([1, 1], gap="medium")
    with left:
        section_title("Subject cohort comparison", "Mathematics vs Portuguese")
        frames = {
            subject: data_loader.with_basis_columns(
                data_loader.add_derived_columns(CTX["base"][CTX["base"]["Subject"] == subject], CTX["thresholds"]),
                CTX["basis"],
                CTX["thresholds"],
            )
            for subject in CTX["base"]["Subject"].unique()
        } if "Subject" in CTX["base"].columns else {}
        comparison = analysis.subject_comparison(frames)
        if len(comparison) > 1:
            st.plotly_chart(viz.subject_comparison_bar(comparison), width="stretch", theme=None)
        show_table(comparison, empty_message="Single subject selected, no comparison to draw.")

    with right:
        section_title("Headline insights", "Computed live from the filtered data")
        summary = analysis.gender_summary(df, CTX["basis"])
        insights = []
        if not summary.empty:
            best = summary.sort_values("Average Marks", ascending=False).iloc[0]
            gap = summary["Average Marks"].max() - summary["Average Marks"].min()
            insights.append(f"**{best['Gender']}** students lead on average marks "
                            f"({best['Average Marks']:.2f} of {grade_basis_max_safe(CTX['basis']):g}). "
                            f"The gap between groups is {gap:.2f} marks.")
        if not df.empty and "Percentage" in df:
            pass_rate = float((df["Percentage"] >= 50).mean() * 100)
            insights.append(f"**{pass_rate:.1f}%** of students in view score 50% or more, "
                            f"equivalent to 10 of 20 in a single period.")
        distribution = analysis.performance_distribution(df)
        if not distribution.empty and distribution["Students"].sum():
            top = distribution.sort_values("Students", ascending=False).iloc[0]
            insights.append(f"The largest band is **{top['Performance']}** with "
                            f"{int(top['Students'])} students ({top['Share']:.1f}% of the cohort).")
        strongest = analysis.strongest_correlations(df)
        if not strongest.empty:
            row = strongest.iloc[0]
            insights.append(f"Strongest relationship with the final grade: **{row['Variable']}** "
                            f"(r = {row['Correlation with G3']:.2f}).")
        for text in insights:
            st.markdown(f"- {text}")

    st.write("")
    st.markdown(
        f"<div class='sga-card'><b style='color:{PALETTE['navy']}'>About the data</b><br>"
        f"<span style='font-size:0.86rem;line-height:1.6;color:{PALETTE['navy_soft']}'>"
        f"The dataset combines two Portuguese secondary school cohorts and reports grades on a 0-20 scale "
        f"for three periods (G1, G2, G3). It contains no ethnicity attribute, so the ethnicity objective "
        f"requires a separate, genuinely labelled dataset; the Ethnicity Analysis page explains and "
        f"supports that merge.</span></div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------------------
# Page 2: Dataset Explorer
# --------------------------------------------------------------------------------------
def page_dataset_explorer() -> None:
    base, full = CTX["base"], CTX["full"]
    hero(
        "Objective 0",
        "Dataset Explorer",
        "Automatic loading, schema validation, cleaning log and a preview of the records used by every "
        "analysis in this dashboard.",
    )

    total_missing = int(base.isna().sum().sum())
    duplicates = int(base.duplicated().sum())
    kpi_row([
        ("Total students", fmt(len(base), 0), "after preprocessing"),
        ("Total columns", fmt(base.shape[1], 0), "including calculated columns"),
        ("Missing values", fmt(total_missing, 0), "remaining after cleaning"),
        ("Duplicate records", fmt(duplicates, 0), "exact duplicates remaining"),
    ])

    st.write("")
    if CTX.get("errors"):
        for error in CTX["errors"]:
            notice(f"Loading issue: {error}", "warn")

    section_title("Source files", "Validated against the expected UCI schema")
    st.caption("Bundled CSVs in `data/` are used by default. Anything you upload in the sidebar is read in "
               "memory for your session only and is never written to the project folder.")
    for subject, report in (CTX.get("validations") or {}).items():
        status = "ok" if report["is_uci_schema"] else "warn"
        with st.expander(f"{subject}: {report['n_rows']:,} rows, {report['n_columns']} columns", expanded=True):
            columns = st.columns(4)
            columns[0].metric("Records", f"{report['n_rows']:,}")
            columns[1].metric("Columns", report["n_columns"])
            columns[2].metric("Missing values", report["total_missing"])
            columns[3].metric("Duplicates", report["duplicate_rows"])
            if report["warnings"]:
                for warning in report["warnings"]:
                    notice(warning, status)
            else:
                notice("Schema complete, no missing values and no duplicate records detected.", "ok")
            if report["missing_columns"]:
                st.write("Missing required columns:", ", ".join(report["missing_columns"]))

    section_title("Cleaning and preprocessing log", "Every transformation applied to the raw files")
    log_frames = CTX.get("logs") or []
    if log_frames:
        show_table(pd.concat(log_frames, ignore_index=True), height=260)
    else:
        notice("No cleaning steps were required for this data.", "ok")

    section_title("Data preview", "First 100 rows of the processed dataset")
    preview_columns = [c for c in ["StudentID", "Subject", "Gender", "age", "school", "Mjob", "Fedu",
                                   "studytime", "absences", "G1", "G2", "G3", "TotalMarks",
                                   "Percentage", "Performance"] if c in full.columns]
    st.dataframe(full[preview_columns].head(100), width="stretch", hide_index=True, height=340)

    left, right = st.columns(2, gap="medium")
    with left:
        section_title("Descriptive statistics", "Numeric variables used in the analysis")
        show_table(analysis.descriptive_statistics(full), height=300)
    with right:
        section_title("Categorical breakdown", "Choose a variable to inspect")
        categorical = [c for c in ["school", "sex", "address", "Mjob", "Fjob", "reason", "studytime",
                                   "Medu", "Fedu", "Performance"] if c in full.columns]
        chosen = st.selectbox("Variable", categorical, key="explorer_categorical")
        show_table(analysis.nominal_categorical_summary(full, chosen), height=300,
                   empty_message="No values to summarise for this variable.")

    section_title("Column dictionary", "What each field in the source dataset means")
    dictionary = pd.DataFrame(
        [{"Column": column, "Description": data_loader.FRIENDLY_NAMES.get(column, column)}
         for column in data_loader.REQUIRED_COLUMNS if column in full.columns]
    )
    show_table(dictionary, height=280)

    st.write("")
    left, right = st.columns([1, 1], gap="medium")
    with left:
        st.download_button(
            "Download cleaned dataset (CSV)",
            data=reports.to_csv_bytes(full),
            file_name=f"cleaned_dataset_{CTX['subject_choice'].lower().replace(' ', '_')}.csv",
            mime="text/csv",
            width="stretch",
        )
    with right:
        st.caption("The download contains every source column plus the calculated columns "
                   "(TotalMarks, Percentage, Performance, AgeGroup, StudentID).")


# --------------------------------------------------------------------------------------
# Page 3: Gender Analysis (Objectives 1 and 2)
# --------------------------------------------------------------------------------------
def page_gender_analysis() -> None:
    df = CTX["df"]
    hero(
        "Objectives 1 and 2",
        "Gender Analysis",
        "Descriptive statistics and comparison charts computed from the dataset's real <i>sex</i> column.",
    )

    if df.empty:
        notice("No students match the current filters. Widen the filters in the sidebar.", "warn")
        return

    summary = analysis.gender_summary(df, CTX["basis"])
    section_title("Objective 1: gender-wise statistical summary",
                  f"Marks and percentages for the {CTX['basis'].lower()}")
    show_table(
        summary,
        column_config=percent_column_config(summary),
        empty_message="Gender statistics are unavailable for this selection.",
    )
    st.caption("Average marks, minimum marks, maximum marks, total students and average percentage, "
               "computed with a single Pandas groupby aggregation on the sex column.")

    st.download_button(
        "Download this table (CSV)",
        data=reports.to_csv_bytes(summary),
        file_name="gender_analysis.csv",
        mime="text/csv",
    )

    st.write("")
    section_title("Objective 2: gender-wise performance charts",
                  "Switch the assessment to compare G1, G2, G3 or the combined grade")
    short_basis = GRADE_BASES[CTX["basis"]]["label"]
    default_grade = "Combined (G1+G2+G3)" if short_basis == "Combined" else short_basis
    grade_choice = st.segmented_control(
        "Assessment for these charts",
        ["G1", "G2", "G3", "Combined (G1+G2+G3)"],
        default=default_grade,
        key="gender_chart_grade",
    ) or default_grade

    view = chart_grade_frame(df, grade_choice)
    values = analysis.gender_metric_values(view)
    max_value = 20.0 if grade_choice != "Combined (G1+G2+G3)" else 60.0

    top_left, top_right = st.columns(2, gap="medium")
    with top_left:
        st.plotly_chart(
            viz.gender_metric_bar(values.get("Average marks"), "Average marks",
                                  f"Average marks by gender ({grade_choice})", max_value),
            width="stretch", theme=None,
        )
    with top_right:
        st.plotly_chart(
            viz.gender_metric_bar(values.get("Number of students"), "Number of students",
                                  "Number of students by gender"),
            width="stretch", theme=None,
        )

    bottom_left, bottom_right = st.columns(2, gap="medium")
    with bottom_left:
        st.plotly_chart(
            viz.gender_metric_bar(values.get("Minimum marks"), "Minimum marks",
                                  f"Minimum marks by gender ({grade_choice})", max_value),
            width="stretch", theme=None,
        )
    with bottom_right:
        st.plotly_chart(
            viz.gender_metric_bar(values.get("Maximum marks"), "Maximum marks",
                                  f"Maximum marks by gender ({grade_choice})", max_value),
            width="stretch", theme=None,
        )

    st.plotly_chart(viz.gender_grouped_bar(values), width="stretch", theme=None)

    left, right = st.columns(2, gap="medium")
    with left:
        distribution_column = "G3" if grade_choice == "Combined (G1+G2+G3)" else grade_choice
        st.plotly_chart(
            viz.grade_distribution_chart(
                analysis.grade_distribution_by_gender(df, distribution_column),
                distribution_column,
                f"{distribution_column} grade distribution by gender",
            ),
            width="stretch", theme=None,
        )
    with right:
        st.plotly_chart(viz.gender_percentage_comparison(view, f"Percentage distribution by gender ({grade_choice})"),
                        width="stretch", theme=None)

    st.plotly_chart(viz.g1_g2_g3_progression(analysis.g1_g2_g3_by_gender(df)), width="stretch", theme=None)

    section_title("Reading the charts", "How to interpret the comparison")
    for gender in ["Female", "Male"]:
        frame = view[view["Gender"] == gender]
        if frame.empty:
            continue
        st.markdown(
            f"- **{gender}**: {len(frame)} students, average {frame['Marks'].mean():.2f} "
            f"({frame['Percentage'].mean():.1f}%), range {frame['Marks'].min():.0f} to {frame['Marks'].max():.0f} "
            f"on {grade_choice}."
        )


# --------------------------------------------------------------------------------------
# Page 4: Percentage Analysis (Objective 3)
# --------------------------------------------------------------------------------------
def page_percentage_analysis() -> None:
    df = CTX["df"]
    hero(
        "Objective 3",
        "Percentage Analysis",
        "A calculated <b>Percentage</b> column and a configurable performance category for every student.",
    )

    formula(f"Percentage = (Total Marks Obtained / Maximum Possible Marks) x 100")
    st.caption("Final grade: (G3 / 20) x 100. Combined grade: ((G1 + G2 + G3) / 60) x 100. "
               "Thresholds can be edited in the sidebar under Performance thresholds.")

    if df.empty:
        notice("No students match the current filters.", "warn")
        return

    kpis = analysis.kpi_metrics(df)
    distribution = analysis.performance_distribution(df)
    excellent = int(distribution.loc[distribution["Performance"] == "Excellent", "Students"].sum()) \
        if not distribution.empty else 0
    needs_help = int(distribution.loc[distribution["Performance"] == "Needs Improvement", "Students"].sum()) \
        if not distribution.empty else 0
    kpi_row([
        ("Average percentage", fmt(kpis["average_percentage"], 2, "%"), "across the current view"),
        ("Excellent (>= 90%)", fmt(excellent, 0), "students in the top band"),
        ("Needs improvement", fmt(needs_help, 0), "students below 40%"),
        ("Bands in use", fmt(len(CTX["thresholds"]), 0), "configurable thresholds"),
    ])

    st.write("")
    left, right = st.columns([1, 1], gap="medium")
    with left:
        section_title("Band summary", "Students, share and percentage range per band")
        show_table(analysis.percentage_band_summary(df),
                   column_config=percent_column_config(analysis.percentage_band_summary(df)))
    with right:
        section_title("Distribution", "Share of students in each performance category")
        st.plotly_chart(viz.performance_donut(distribution), width="stretch", theme=None)

    section_title("Student-level percentage report",
                  "Student ID, gender, grade, percentage and performance category")
    band_filter = st.multiselect("Show only these categories", CATEGORY_ORDER, default=CATEGORY_ORDER,
                                 key="pct_band_filter")
    report = analysis.percentage_report(df)
    if band_filter and "Performance" in report.columns:
        report = report[report["Performance"].isin(band_filter)]
    show_table(
        report,
        height=420,
        column_config=percent_column_config(report),
        empty_message="No students match the selected categories.",
    )

    st.download_button(
        "Download percentage report (CSV)",
        data=reports.to_csv_bytes(report),
        file_name="percentage_report.csv",
        mime="text/csv",
    )

    st.write("")
    st.plotly_chart(viz.performance_category_bar(distribution), width="stretch", theme=None)
    st.plotly_chart(viz.gender_percentage_comparison(df, "Percentage distribution by gender"), width="stretch", theme=None)


# --------------------------------------------------------------------------------------
# Page 5: Ethnicity Analysis (Objective 4)
# --------------------------------------------------------------------------------------
def page_ethnicity_analysis() -> None:
    df = CTX["df"]
    hero(
        "Objective 4",
        "Ethnicity Analysis",
        "Group-level performance analysis. This objective runs only on a genuine ethnicity column, "
        "supplied as a separate dataset.",
    )

    notice(
        "<b>The UCI Student Performance dataset has no ethnicity column.</b> It records gender, age, school, "
        "family background and grades only. Relabelling a field such as mother's education, mother's job or "
        "address type as 'ethnicity' would be inaccurate, so this page does not do that. Upload a compatible "
        "dataset that carries a real ethnicity label, keyed by Student ID, and the analysis below runs on it.",
        "info",
    )

    sample_path = SAMPLE_ETHNICITY_PATH
    upload_column, action_column = st.columns([2, 1], gap="medium")
    with upload_column:
        uploaded = st.file_uploader(
            "Ethnicity dataset (CSV, XLSX not supported)",
            type="csv",
            key="eth_upload",
            help="Needs an ethnicity column plus either a StudentID column (e.g. MAT-001) or the same "
                 "number of rows as the student dataset.",
        )
    with action_column:
        st.caption("No file at hand? Load the bundled illustrative sample to see the full workflow. "
                   "Its labels are synthetic and clearly marked as such.")
        load_sample = st.button("Load sample ethnicity file", width="stretch")
        if st.session_state.get("ethnicity_map") and st.button("Remove ethnicity data", width="stretch"):
            st.session_state.pop("ethnicity_map", None)
            st.session_state.pop("ethnicity_info", None)
            st.rerun()

    if load_sample and sample_path.is_file():
        payload = sample_path.read_bytes()
        merged, info, error = pipeline.attach_ethnicity(CTX["base"], payload, sample_path.name)
        if error:
            st.error(error)
        else:
            st.session_state["ethnicity_map"] = dict(zip(merged["StudentID"], merged["Ethnicity"]))
            st.session_state["ethnicity_info"] = info
            st.rerun()

    if uploaded is not None:
        payload = uploaded.getvalue()
        try:
            preview = data_loader.read_csv_bytes(payload)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not read that file: {exc}")
            preview = pd.DataFrame()

        if not preview.empty:
            st.caption(f"Detected {len(preview):,} rows and {len(preview.columns)} columns in "
                       f"'{uploaded.name}'.")
            candidate = [c for c in preview.columns]
            default_index = 0
            for i, column in enumerate(candidate):
                if "ethnic" in str(column).lower() or str(column).lower() == "race":
                    default_index = i
                    break
            column_one, column_two = st.columns(2, gap="medium")
            with column_one:
                chosen_column = st.selectbox("Ethnicity column", candidate, index=default_index,
                                             key="eth_column")
            with column_two:
                merge_mode = st.selectbox(
                    "Match students by",
                    ["Auto detect", "Merge on student ID", "Assign by row order"],
                    key="eth_mode",
                )
            if st.button("Apply ethnicity data", type="primary"):
                merged, info, error = pipeline.attach_ethnicity(
                    CTX["base"], payload, uploaded.name,
                    ethnicity_column=chosen_column, mode=merge_mode,
                )
                if error:
                    st.error(error)
                else:
                    st.session_state["ethnicity_map"] = dict(zip(merged["StudentID"], merged["Ethnicity"]))
                    st.session_state["ethnicity_info"] = info
                    st.rerun()

    info = st.session_state.get("ethnicity_info")
    if not info or "Ethnicity" not in df.columns:
        st.write("")
        section_title("What happens once ethnicity data is attached", "Method used for the merge and ranking")
        st.markdown(
            "- The uploaded labels are merged onto the student records by Student ID (for example MAT-001) "
            "or, when the row counts match exactly, by row order.\n"
            "- Every group is summarised with student count, total marks, average marks, minimum and maximum "
            "marks and average percentage.\n"
            "- Groups are ranked by **average marks per student**, because raw totals favour larger groups. "
            "Ties are broken by average percentage.\n"
            "- A pie chart shows each group's share of all marks obtained."
        )
        return

    if info.get("demo_labels"):
        notice("<b>Illustrative sample in use.</b> The ethnicity labels shown below come from the bundled "
               "demonstration file, not from the UCI dataset. They prove the pipeline works and must not be "
               "presented as real findings. Upload a genuine ethnicity dataset to produce real results.",
               "warn")

    st.caption(f"Merged from '{info.get('filename')}': {info.get('method')}. "
               f"Matched {info.get('matched_rows', 0):,} students, {info.get('groups', 0)} groups.")

    table = analysis.ethnicity_summary(df, "Ethnicity")
    if table.empty:
        notice("The ethnicity labels could not be matched to the students in the current filter.", "warn")
        return

    best = analysis.best_performing_ethnicity(table)
    kpi_row([
        ("Ethnicity groups", fmt(len(table), 0), "distinct groups in view"),
        ("Best average", fmt(best["average_marks"] if best else np.nan), best["group"] if best else "-"),
        ("Students labelled", fmt(int(table["Students"].sum()), 0), "with an ethnicity label"),
        ("Groups compared", fmt(best["groups_compared"] if best else 0, 0), "ranked by average marks"),
    ])

    st.write("")
    if best:
        st.markdown(
            f"<div class='sga-card'><span class='sga-eyebrow'>Best performing group</span>"
            f"<div style='font-size:1.6rem;font-weight:800;color:{PALETTE['navy']}'>{best['group']}</div>"
            f"<div style='color:{PALETTE['navy_soft']};font-size:0.9rem;margin-top:4px'>"
            f"Average {best['average_marks']:.2f} marks ({best['average_percentage']:.2f}%) across "
            f"{best['students']} students"
            + (f", ahead of {best['runner_up']} by {best['gap_to_second']:.2f} marks." if best.get("runner_up") else ".")
            + "</div></div>",
            unsafe_allow_html=True,
        )

    section_title("Objective 4: ethnicity-wise summary", "Sorted by average marks per student")
    show_table(table, column_config=percent_column_config(table))

    left, right = st.columns(2, gap="medium")
    with left:
        st.plotly_chart(viz.ethnicity_pie(table), width="stretch", theme=None)
    with right:
        st.plotly_chart(viz.ethnicity_average_bar(table), width="stretch", theme=None)

    section_title("Methodology", "How the best performing group is determined")
    st.markdown(
        "- Metric: **average marks per student** on the selected grade basis, so a large group does not win "
        "simply by having more students.\n"
        "- Ranking: groups sorted by average marks, then by average percentage, then by student count.\n"
        "- Comparison: the gap to the runner-up group is reported next to the winner so small differences are "
        "not over-interpreted.\n"
        "- Caveat: groups with very few students produce unstable averages; check the student count column "
        "before drawing conclusions."
    )

    section_title("Student-wise total marks by ethnicity", "Objective 4 requirement, student level detail")
    show_table(analysis.student_marks_by_ethnicity(df, "Ethnicity"),
               height=380, column_config=percent_column_config(analysis.student_marks_by_ethnicity(df, "Ethnicity")))

    st.download_button(
        "Download ethnicity analysis (CSV)",
        data=reports.to_csv_bytes(table),
        file_name="ethnicity_analysis.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------------------
# Page 6: Visualizations gallery
# --------------------------------------------------------------------------------------
def page_visualizations() -> None:
    df = CTX["df"]
    hero(
        "Visualisation suite",
        "Visualizations",
        "Every required chart in one place. All figures are interactive: hover for exact values, "
        "click a legend entry to isolate a series, and use the toolbar to zoom or save.",
    )

    if df.empty:
        notice("No students match the current filters.", "warn")
        return

    values = analysis.gender_metric_values(df)
    summary = analysis.gender_summary(df, CTX["basis"])
    distribution = analysis.performance_distribution(df)

    row_one_left, row_one_right = st.columns(2, gap="medium")
    with row_one_left:
        st.plotly_chart(viz.gender_metric_bar(values.get("Average marks"), "Average marks",
                                             f"1. Gender-wise average marks ({CTX['basis']})",
                                             grade_basis_max_safe(CTX["basis"])),
                        width="stretch", theme=None)
    with row_one_right:
        st.plotly_chart(viz.gender_count_chart(values.get("Number of students"),
                                              "2. Gender-wise student count"),
                        width="stretch", theme=None)

    row_two_left, row_two_right = st.columns(2, gap="medium")
    with row_two_left:
        st.plotly_chart(viz.grade_histogram(df, "G3", "3. Final grade (G3) distribution"), width="stretch", theme=None)
    with row_two_right:
        st.plotly_chart(viz.g1_g2_g3_progression(analysis.g1_g2_g3_by_gender(df),
                                                "4. G1 vs G2 vs G3 comparison"),
                        width="stretch", theme=None)

    row_three_left, row_three_right = st.columns(2, gap="medium")
    with row_three_left:
        st.plotly_chart(viz.gender_percentage_comparison(df, "5. Gender-wise percentage comparison"),
                        width="stretch", theme=None)
    with row_three_right:
        st.plotly_chart(viz.performance_donut(distribution, "8. Student performance distribution"),
                        width="stretch", theme=None)

    if "Ethnicity" in df.columns:
        ethnicity_table = analysis.ethnicity_summary(df, "Ethnicity")
        if not ethnicity_table.empty:
            st.plotly_chart(viz.ethnicity_pie(ethnicity_table, "6. Ethnicity-wise total marks"),
                            width="stretch", theme=None)
    else:
        notice("Chart 6 (ethnicity-wise total marks) needs an ethnicity dataset. "
               "Add one on the Ethnicity Analysis page to enable it.", "info")

    st.plotly_chart(viz.correlation_heatmap(analysis.correlation_matrix(df),
                                            "7. Correlation heatmap of academic and demographic variables"),
                    width="stretch", theme=None)

    st.write("")
    section_title("Extra views", "Additional perspectives on the same filtered data")
    extra_left, extra_right = st.columns(2, gap="medium")
    with extra_left:
        st.plotly_chart(viz.study_time_scatter(df, "Weekly study time vs final grade"),
                        width="stretch", theme=None)
    with extra_right:
        st.plotly_chart(viz.performance_category_bar(distribution, "Students per performance category"),
                        width="stretch", theme=None)


# --------------------------------------------------------------------------------------
# Page 7: Student Performance
# --------------------------------------------------------------------------------------
def page_student_performance() -> None:
    df = CTX["df"]
    hero(
        "Student level",
        "Student Performance",
        "Browse individual records, search by Student ID and inspect a single student's full grade profile.",
    )

    if df.empty:
        notice("No students match the current filters.", "warn")
        return

    columns_row = st.columns([2, 1.4, 1], gap="medium")
    with columns_row[0]:
        search = st.text_input("Search by Student ID", placeholder="for example MAT-001", key="student_search")
    with columns_row[1]:
        sort_by = st.selectbox("Sort by", ["Percentage", "G3", "G2", "G1", "TotalMarks", "absences", "age"],
                               key="student_sort")
    with columns_row[2]:
        descending = st.toggle("Descending", value=True, key="student_desc")

    view = df.copy()
    if search:
        view = view[view["StudentID"].astype(str).str.contains(search.strip(), case=False, na=False)]
    if sort_by in view.columns:
        view = view.sort_values(sort_by, ascending=not descending)

    display_columns = [c for c in ["StudentID", "Subject", "Gender", "age", "school", "studytime",
                                   "failures", "absences", "G1", "G2", "G3", "TotalMarks",
                                   "Percentage", "Performance"] if c in view.columns]
    show_table(view[display_columns], height=380, column_config=percent_column_config(view),
               empty_message="No student matches that search.")

    kpis = analysis.kpi_metrics(view)
    st.caption(f"{len(view):,} students shown. Average {fmt(kpis['average_marks'])} marks, "
               f"{fmt(kpis['average_percentage'], 1, '%')}.")

    st.write("")
    left, right = st.columns(2, gap="medium")
    with left:
        section_title("Top 10 students", "Highest percentages in the current view")
        show_table(analysis.percentage_report(view).head(10), height=360,
                   column_config=percent_column_config(view))
    with right:
        section_title("Students needing support", "Lowest percentages in the current view")
        show_table(analysis.percentage_report(view).tail(10).iloc[::-1], height=360,
                   column_config=percent_column_config(view))

    section_title("Individual student profile", "Pick a student to see their full record")
    options = view["StudentID"].tolist()
    if options:
        selected = st.selectbox("Student", options, key="student_detail")
        record = view[view["StudentID"] == selected].iloc[0]
        kpi_row([
            ("Final grade (G3)", fmt(record.get("G3"), 0), "out of 20"),
            ("Total marks", fmt(record.get("TotalMarks"), 0), "G1+G2+G3 of 60"),
            ("Percentage", fmt(record.get("Percentage"), 1, "%"), "selected basis"),
            ("Category", str(record.get("Performance", "-")), "performance band"),
        ])
        st.write("")
        detail = pd.DataFrame({
            "Attribute": ["Student ID", "Subject", "Gender", "Age", "School", "Study time (1-4)",
                          "Failures", "Absences", "Mother's education", "Father's education",
                          "Wants higher education", "Internet at home", "G1", "G2", "G3"],
            "Value": [
                record.get("StudentID"), record.get("Subject"), record.get("Gender"),
                fmt(record.get("age"), 0), record.get("school"), fmt(record.get("studytime"), 0),
                fmt(record.get("failures"), 0), fmt(record.get("absences"), 0),
                fmt(record.get("Medu"), 0), fmt(record.get("Fedu"), 0),
                record.get("higher"), record.get("internet"),
                fmt(record.get("G1"), 0), fmt(record.get("G2"), 0), fmt(record.get("G3"), 0),
            ],
        })
        show_table(detail, height=340)

    st.write("")
    st.plotly_chart(viz.study_time_scatter(view, "Study time vs final grade for the filtered students"),
                    width="stretch", theme=None)


# --------------------------------------------------------------------------------------
# Page 8: Download Reports
# --------------------------------------------------------------------------------------
def _current_signature() -> str:
    """Signature describing the current analysis, used to cache generated reports."""
    df = CTX.get("df", pd.DataFrame())
    return "|".join([
        CTX.get("subject_choice", ""),
        CTX.get("basis", ""),
        str(len(df)),
        str(round(float(df["Percentage"].sum()), 4)) if "Percentage" in df.columns and not df.empty else "0",
        "eth" if "Ethnicity" in df.columns else "noeth",
        str(st.session_state.get("ethnicity_info", {}).get("matched_rows", 0)),
    ])


def page_download_reports() -> None:
    df = CTX["df"]
    hero(
        "Deliverables",
        "Download Reports",
        "Export the cleaned dataset, the analysis tables, chart images and a complete PDF project report "
        "for the current selection.",
    )

    if df.empty:
        notice("No students match the current filters, so there is nothing to export.", "warn")
        return

    summary = analysis.gender_summary(df, CTX["basis"])
    percentage = analysis.percentage_report(df)
    ethnicity_table = analysis.ethnicity_summary(df, "Ethnicity") if "Ethnicity" in df.columns else pd.DataFrame()

    section_title("Data exports", "CSV files generated from the filtered data")
    first, second, third = st.columns(3, gap="medium")
    with first:
        st.download_button("Cleaned dataset (CSV)", data=reports.to_csv_bytes(df),
                           file_name="cleaned_dataset.csv", mime="text/csv", width="stretch")
        st.caption("All source columns plus TotalMarks, Percentage, Performance, AgeGroup and StudentID.")
    with second:
        st.download_button("Gender analysis (CSV)", data=reports.to_csv_bytes(summary),
                           file_name="gender_analysis.csv", mime="text/csv", width="stretch")
        st.caption("Objective 1 summary table for the selected grade basis.")
    with third:
        st.download_button("Percentage report (CSV)", data=reports.to_csv_bytes(percentage),
                           file_name="percentage_report.csv", mime="text/csv", width="stretch")
        st.caption("Student level percentages and performance categories.")

    if not ethnicity_table.empty:
        st.write("")
        st.download_button("Ethnicity analysis (CSV)", data=reports.to_csv_bytes(ethnicity_table),
                           file_name="ethnicity_analysis.csv", mime="text/csv")

    st.write("")
    section_title("Chart images", "High resolution PNG renders of every figure")
    if st.button("Prepare chart images", width="stretch"):
        with st.spinner("Rendering charts..."):
            try:
                # A TemporaryDirectory cleans itself up, so repeated exports on a long
                # lived cloud container never fill the disk. Only the finished bytes
                # are kept in session state.
                with tempfile.TemporaryDirectory(prefix="sga_charts_") as tmp:
                    chart_dir = Path(tmp)
                    charts = static_charts.build_chart_pack(
                        df=df,
                        gender_summary_table=summary,
                        values_map=analysis.gender_metric_values(df),
                        progression=analysis.g1_g2_g3_by_gender(df),
                        distribution=analysis.performance_distribution(df),
                        correlation=analysis.correlation_matrix(df),
                        grade_basis_label=CTX["basis"],
                        output_dir=chart_dir,
                        ethnicity_table=ethnicity_table if not ethnicity_table.empty else None,
                    )
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                        for chart in charts:
                            archive.write(chart["path"], arcname=Path(chart["path"]).name)
                    # Keep small preview copies for the first four charts only.
                    previews = [
                        {"title": chart["title"], "name": Path(chart["path"]).name,
                         "bytes": Path(chart["path"]).read_bytes()}
                        for chart in charts[:4]
                    ]
                    listing = [{"Chart": chart["title"], "File": Path(chart["path"]).name}
                               for chart in charts]
                st.session_state["chart_zip"] = buffer.getvalue()
                st.session_state["chart_list"] = listing
                st.session_state["chart_previews"] = previews
            except Exception as exc:  # noqa: BLE001 - surface a readable message
                st.error(f"The chart images could not be rendered: {exc}")

    if st.session_state.get("chart_zip"):
        st.download_button("Download all charts (ZIP)", data=st.session_state["chart_zip"],
                           file_name="student_grades_charts.zip", mime="application/zip")
        with st.expander("Preview individual charts"):
            show_table(pd.DataFrame(st.session_state.get("chart_list", [])), height=260)
            for preview in st.session_state.get("chart_previews", []):
                st.image(preview["bytes"], caption=preview["title"], width="stretch")

    st.write("")
    section_title("PDF project report",
                  "Overview, methodology, dataset details, statistics, charts, ethnicity analysis and conclusions")

    signature = _current_signature()
    if st.session_state.get("report_signature") != signature:
        st.session_state.pop("report_pdf_bytes", None)

    if st.button("Generate PDF report", type="primary", width="stretch"):
        with st.spinner("Building the report..."):
            try:
                bundle = {
                    "frame": df,
                    "kpis": analysis.kpi_metrics(df),
                    "gender_summary": summary,
                    "percentage_report": percentage,
                    "percentage_bands": analysis.percentage_band_summary(df),
                    "distribution": analysis.performance_distribution(df),
                    "gender_values": analysis.gender_metric_values(df),
                    "grade_distribution": analysis.grade_distribution_by_gender(df, "G3"),
                    "progression": analysis.g1_g2_g3_by_gender(df),
                    "correlation": analysis.correlation_matrix(df),
                    "correlations": analysis.strongest_correlations(df),
                    "basis_label": CTX["basis"],
                    "thresholds": CTX["thresholds"],
                }
                frames = {
                    subject: data_loader.with_basis_columns(
                        data_loader.add_derived_columns(
                            CTX["base"][CTX["base"]["Subject"] == subject], CTX["thresholds"]),
                        CTX["basis"], CTX["thresholds"],
                    )
                    for subject in CTX["base"]["Subject"].unique()
                } if "Subject" in CTX["base"].columns else {}
                with tempfile.TemporaryDirectory(prefix="sga_report_") as tmp:
                    out_dir = Path(tmp)
                    paths = pipeline.write_report_outputs(
                        bundle=bundle,
                        output_dir=out_dir,
                        chart_dir=out_dir / "charts",
                        subject_label=CTX["subject_choice"],
                        cleaning_logs=CTX.get("logs"),
                        validation_reports=CTX.get("validations"),
                        ethnicity_info=st.session_state.get("ethnicity_info"),
                        ethnicity_table=ethnicity_table if not ethnicity_table.empty else None,
                        subject_comparison=analysis.subject_comparison(frames) if len(frames) > 1 else None,
                        prefix="student_grades",
                    )
                    st.session_state["report_pdf_bytes"] = Path(paths["pdf"]).read_bytes()
                st.session_state["report_signature"] = signature
                st.success("PDF report generated.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"The report could not be generated: {exc}")

    if st.session_state.get("report_pdf_bytes"):
        st.download_button("Download PDF report", data=st.session_state["report_pdf_bytes"],
                           file_name=f"student_grades_report_{datetime.now():%Y%m%d}.pdf",
                           mime="application/pdf", width="stretch")
    else:
        st.caption("The PDF includes the current filters, so it always matches what you see on screen.")

    st.write("")
    section_title("What the report contains", "Structure of the generated PDF")
    st.markdown(
        "1. Cover with the KPI summary\n"
        "2. Methodology, including the percentage formulas and performance bands\n"
        "3. Dataset details and the full cleaning log\n"
        "4. Objective 1: gender-wise statistical table\n"
        "5. Objective 2: gender comparison charts\n"
        "6. Objective 3: percentage bands and the top students\n"
        "7. Objective 4: ethnicity analysis, or the explanation of why it needs extra data\n"
        "8. Additional analysis: subject comparison and correlation findings\n"
        "9. Conclusions and limitations"
    )


# --------------------------------------------------------------------------------------
# Navigation
# --------------------------------------------------------------------------------------
init_filter_state(st.session_state.get("flt_subject", "Both subjects"))
CTX.update(build_context())

pages = [
    st.Page(page_overview, title="Overview", icon="🏠", default=True),
    st.Page(page_dataset_explorer, title="Dataset Explorer", icon="🗂️"),
    st.Page(page_gender_analysis, title="Gender Analysis", icon="⚖️"),
    st.Page(page_percentage_analysis, title="Percentage Analysis", icon="📊"),
    st.Page(page_ethnicity_analysis, title="Ethnicity Analysis", icon="🌍"),
    st.Page(page_visualizations, title="Visualizations", icon="📈"),
    st.Page(page_student_performance, title="Student Performance", icon="🎓"),
    st.Page(page_download_reports, title="Download Reports", icon="⬇️"),
]

if CTX.get("empty"):
    st.error("The dataset could not be loaded.")
    for error in CTX.get("errors", []):
        st.code(error)
    st.info("Check the internet connection for the automatic UCI download, or upload "
            "student-mat.csv / student-por.csv from the sidebar.")
    st.stop()

st.navigation(pages, position="sidebar").run()
render_sidebar()
