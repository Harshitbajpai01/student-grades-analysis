"""
Dataset loading, validation, cleaning and feature engineering.

Responsibilities
----------------
* Load the UCI Student Performance CSVs (Mathematics / Portuguese) from local disk,
  from an in-app upload, or by downloading the official archive automatically.
* Validate the schema so we never silently analyse an incompatible file.
* Clean the data (duplicates, whitespace, invalid grades, missing values) and log
  every action so the dashboard can show a transparent cleaning report.
* Derive the analysis columns used by the objectives: StudentID, TotalMarks,
  Percentage, performance category and age group.

Nothing in this module invents data. Every column either comes from the CSV or is
computed from real columns with a formula documented next to it.
"""

from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import (
    AGE_GROUP_ORDER,
    DATA_DIR,
    DATASET_ZIP_URLS,
    DEFAULT_THRESHOLDS,
    GENDER_LABELS,
    GRADE_BASES,
    MAX_MARK_PER_PERIOD,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    SUBJECTS,
    ensure_dir,
)

# --------------------------------------------------------------------------------------
# Schema knowledge about the real UCI dataset
# --------------------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "school", "sex", "age", "address", "famsize", "Pstatus", "Medu", "Fedu",
    "Mjob", "Fjob", "reason", "guardian", "traveltime", "studytime", "failures",
    "schoolsup", "famsup", "paid", "activities", "nursery", "higher", "internet",
    "romantic", "famrel", "freetime", "goout", "Dalc", "Walc", "health",
    "absences", "G1", "G2", "G3",
]

NUMERIC_COLUMNS = [
    "age", "Medu", "Fedu", "traveltime", "studytime", "failures", "famrel",
    "freetime", "goout", "Dalc", "Walc", "health", "absences", "G1", "G2", "G3",
]

CATEGORICAL_COLUMNS = [
    "school", "sex", "address", "famsize", "Pstatus", "Mjob", "Fjob", "reason",
    "guardian", "schoolsup", "famsup", "paid", "activities", "nursery", "higher",
    "internet", "romantic",
]

# Human friendly rename map used in the UI / report tables only.
FRIENDLY_NAMES = {
    "school": "School",
    "sex": "Gender",
    "age": "Age",
    "address": "Address type",
    "famsize": "Family size",
    "Pstatus": "Parents' cohabitation",
    "Medu": "Mother's education (0-4)",
    "Fedu": "Father's education (0-4)",
    "Mjob": "Mother's job",
    "Fjob": "Father's job",
    "reason": "Reason for school choice",
    "guardian": "Guardian",
    "traveltime": "Travel time (1-4)",
    "studytime": "Weekly study time (1-4)",
    "failures": "Past class failures",
    "schoolsup": "Extra school support",
    "famsup": "Family educational support",
    "paid": "Paid classes",
    "activities": "Extra-curricular activities",
    "nursery": "Attended nursery",
    "higher": "Wants higher education",
    "internet": "Internet at home",
    "romantic": "In a romantic relationship",
    "famrel": "Family relationship quality (1-5)",
    "freetime": "Free time after school (1-5)",
    "goout": "Going out with friends (1-5)",
    "Dalc": "Workday alcohol consumption (1-5)",
    "Walc": "Weekend alcohol consumption (1-5)",
    "health": "Current health (1-5)",
    "absences": "School absences",
    "G1": "First period grade (G1)",
    "G2": "Second period grade (G2)",
    "G3": "Final grade (G3)",
    "TotalMarks": "Total marks (G1+G2+G3)",
    "Percentage": "Percentage",
    "Performance": "Performance category",
    "AgeGroup": "Age group",
    "Subject": "Subject",
    "StudentID": "Student ID",
    "Ethnicity": "Ethnicity",
}


# --------------------------------------------------------------------------------------
# Low level readers
# --------------------------------------------------------------------------------------
def _sniff_separator(sample_line: str) -> str:
    """The UCI files are semicolon separated, but uploaded files may use commas."""
    return ";" if sample_line.count(";") > sample_line.count(",") else ","


def read_csv_bytes(raw: bytes) -> pd.DataFrame:
    """Read a CSV payload robustly (separator sniffing, BOM handling, NA tokens)."""
    text = raw.decode("utf-8-sig", errors="replace")
    first_line = text.split("\n", 1)[0]
    sep = _sniff_separator(first_line)
    df = pd.read_csv(
        io.StringIO(text),
        sep=sep,
        na_values=["", "NA", "na", "N/A", "n/a", "?", "null", "NULL", "None"],
        skipinitialspace=True,
    )
    # Strip stray quotes / whitespace that the UCI files carry around string values.
    df.columns = [str(c).strip().strip('"') for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip().str.strip('"').replace({"nan": np.nan})
    return df


def dataset_path(subject: str) -> Path:
    """Absolute path of the bundled CSV for a subject (may not exist)."""
    return DATA_DIR / SUBJECTS[subject]["file"]


def has_bundled_dataset(subject: str) -> bool:
    """True when the CSV shipped with the repository is present and readable."""
    path = dataset_path(subject)
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def fetch_dataset_bytes(subject: str) -> Tuple[bytes, str]:
    """
    Download the official UCI archive and return the requested CSV as bytes.

    The payload is handled in memory first, so this also works on a read-only
    filesystem. Writing a copy into data/ is a best-effort cache that never raises.
    Returns ``(csv_bytes, source_description)``.
    """
    member = SUBJECTS[subject]["zip_member"]
    errors: List[str] = []
    for url in DATASET_ZIP_URLS:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if member not in archive.namelist():
                    raise KeyError(f"{member} not present in archive from {url}")
                csv_bytes = archive.read(member)
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            errors.append(f"{url} -> {exc}")
            continue

        # Best-effort cache: harmless if the filesystem is read-only or ephemeral.
        try:
            ensure_dir(DATA_DIR)
            target = dataset_path(subject)
            if not target.exists():
                target.write_bytes(csv_bytes)
        except OSError:
            pass
        return csv_bytes, f"UCI archive ({url.rsplit('/', 1)[-1]})"

    raise FileNotFoundError(
        "The dataset file for "
        f"{subject} ({SUBJECTS[subject]['file']}) is not in the data/ folder and could not be "
        "downloaded automatically. Upload the CSV from the sidebar, or add the file to data/ "
        "and redeploy.\n" + "\n".join(errors)
    )


def validate_upload(payload: bytes, filename: str = "") -> None:
    """
    Reject empty or oversized uploads before they are parsed.

    Keeps memory use predictable on Streamlit Community Cloud, where the container is
    small and shared.
    """
    name = filename or "the uploaded file"
    if not payload:
        raise ValueError(f"{name} is empty. Please choose a CSV file that contains student records.")
    if len(payload) > MAX_UPLOAD_BYTES:
        size_mb = len(payload) / (1024 * 1024)
        raise ValueError(
            f"{name} is {size_mb:.1f} MB, which is above the {MAX_UPLOAD_MB} MB limit for this "
            "dashboard. Please upload a smaller CSV (the UCI files are under 200 KB)."
        )


def load_subject(subject: str, uploaded_bytes: Optional[bytes] = None) -> pd.DataFrame:
    """
    Load one subject file.

    Order of precedence:
    1. An explicit upload from the sidebar (parsed in memory, never written to disk).
    2. The CSV bundled in ``data/`` (the normal Streamlit Cloud path).
    3. A one-off download from the UCI archive, only if the file is missing.
    """
    if uploaded_bytes:
        validate_upload(uploaded_bytes, SUBJECTS[subject]["file"])
        df = read_csv_bytes(uploaded_bytes)
        source = "uploaded file"
    elif has_bundled_dataset(subject):
        df = read_csv_bytes(dataset_path(subject).read_bytes())
        source = f"data/{SUBJECTS[subject]['file']}"
    else:
        csv_bytes, source = fetch_dataset_bytes(subject)
        df = read_csv_bytes(csv_bytes)

    df["Subject"] = subject
    df.attrs["source"] = source
    return df


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------
def validate_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Inspect a dataframe against the expected UCI schema.

    Returns a dictionary that the dashboard renders directly: missing columns,
    extra columns, missing values, duplicates and out-of-range grades.
    """
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    extra_columns = [c for c in df.columns if c not in REQUIRED_COLUMNS and c != "Subject"]

    missing_values = {
        col: int(df[col].isna().sum()) for col in df.columns if int(df[col].isna().sum()) > 0
    }
    total_missing = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    invalid_grades: Dict[str, int] = {}
    for col in ("G1", "G2", "G3"):
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            out_of_range = ((numeric < 0) | (numeric > MAX_MARK_PER_PERIOD)).sum()
            if out_of_range:
                invalid_grades[col] = int(out_of_range)

    warnings: List[str] = []
    if missing_columns:
        warnings.append(
            "Missing required column(s): " + ", ".join(missing_columns)
            + ". Analysis of those objectives will be skipped."
        )
    if total_missing:
        warnings.append(f"{total_missing} missing value(s) will be imputed during cleaning.")
    if duplicate_rows:
        warnings.append(f"{duplicate_rows} duplicate row(s) will be removed during cleaning.")
    if invalid_grades:
        warnings.append("Grades outside the 0-20 scale will be clipped to the valid range.")
    if not any(col in df.columns for col in ("sex",)):
        warnings.append("The 'sex' column is absent, so gender analysis is unavailable.")

    return {
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "columns": list(df.columns),
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "missing_values": missing_values,
        "total_missing": total_missing,
        "duplicate_rows": duplicate_rows,
        "invalid_grades": invalid_grades,
        "warnings": warnings,
        "is_uci_schema": not missing_columns,
    }


# --------------------------------------------------------------------------------------
# Cleaning / preprocessing
# --------------------------------------------------------------------------------------
def clean_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Clean and preprocess the raw dataframe.

    Steps are logged so the Dataset Explorer page can show exactly what happened:
    1. Drop fully empty rows/columns.
    2. Remove exact duplicate records.
    3. Coerce numeric columns, clip grades to 0-20.
    4. Impute missing numeric values with the median and categorical with the mode.
    5. Normalise gender codes to F/M.
    """
    log: List[Dict[str, Any]] = []
    work = df.copy()

    before_rows, before_cols = work.shape
    work = work.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if work.shape != (before_rows, before_cols):
        log.append({
            "Step": "Drop empty rows/columns",
            "Detail": f"Removed {before_rows - work.shape[0]} empty row(s) "
                      f"and {before_cols - work.shape[1]} empty column(s).",
            "Records affected": before_rows - work.shape[0],
        })

    duplicates = int(work.duplicated().sum())
    if duplicates:
        work = work.drop_duplicates().reset_index(drop=True)
        log.append({
            "Step": "Remove duplicate records",
            "Detail": f"Removed {duplicates} exact duplicate row(s).",
            "Records affected": duplicates,
        })

    numeric_present = [c for c in NUMERIC_COLUMNS if c in work.columns]
    coerced = 0
    for col in numeric_present:
        original_na = work[col].isna().sum()
        work[col] = pd.to_numeric(work[col], errors="coerce")
        coerced += int(max(0, work[col].isna().sum() - original_na))
    if coerced:
        log.append({
            "Step": "Coerce numeric columns",
            "Detail": f"{coerced} non-numeric value(s) were converted to missing.",
            "Records affected": coerced,
        })

    clipped = 0
    for col in [c for c in ("G1", "G2", "G3") if c in work.columns]:
        out_of_range = int(((work[col] < 0) | (work[col] > MAX_MARK_PER_PERIOD)).sum())
        if out_of_range:
            work[col] = work[col].clip(0, MAX_MARK_PER_PERIOD)
            clipped += out_of_range
    if clipped:
        log.append({
            "Step": "Clip invalid grades",
            "Detail": f"{clipped} grade value(s) outside 0-20 clipped to the valid scale.",
            "Records affected": clipped,
        })

    imputed = 0
    for col in numeric_present:
        if work[col].isna().any():
            count = int(work[col].isna().sum())
            work[col] = work[col].fillna(work[col].median())
            imputed += count
            log.append({
                "Step": "Impute missing numeric values",
                "Detail": f"{col}: {count} missing value(s) replaced with the column median.",
                "Records affected": count,
            })
    for col in [c for c in CATEGORICAL_COLUMNS if c in work.columns]:
        if work[col].isna().any():
            count = int(work[col].isna().sum())
            mode = work[col].mode(dropna=True)
            fill = mode.iloc[0] if not mode.empty else "Unknown"
            work[col] = work[col].fillna(fill)
            imputed += count
            log.append({
                "Step": "Impute missing categories",
                "Detail": f"{col}: {count} missing value(s) replaced with the mode ('{fill}').",
                "Records affected": count,
            })

    if "sex" in work.columns:
        work["sex"] = work["sex"].astype(str).str.strip().str.upper().str[0]
        work["sex"] = work["sex"].where(work["sex"].isin(["F", "M"]), np.nan)
        if work["sex"].isna().any():
            dropped = int(work["sex"].isna().sum())
            work = work.dropna(subset=["sex"]).reset_index(drop=True)
            log.append({
                "Step": "Normalise gender codes",
                "Detail": f"Dropped {dropped} row(s) with an unrecognisable gender code.",
                "Records affected": dropped,
            })

    if int(work.isna().sum().sum()) == 0:
        log.append({
            "Step": "Final check",
            "Detail": "No missing values remain after preprocessing.",
            "Records affected": 0,
        })

    work = work.reset_index(drop=True)
    work = assign_student_ids(work)
    return work, log


def assign_student_ids(df: pd.DataFrame, id_column: str = "StudentID") -> pd.DataFrame:
    """
    The UCI dataset has no student identifier, so we generate a transparent,
    reproducible row identifier: <subject code>-<row number>, e.g. MAT-001.
    """
    work = df.copy()
    subject_codes = work["Subject"].map(
        lambda s: SUBJECTS.get(s, {}).get("code", "STU")
    ) if "Subject" in work.columns else pd.Series("STU", index=work.index)
    sequence = work.groupby(subject_codes).cumcount() + 1
    work[id_column] = [f"{code}-{num:03d}" for code, num in zip(subject_codes, sequence)]
    return work


# --------------------------------------------------------------------------------------
# Feature engineering: total marks, percentage, performance category
# --------------------------------------------------------------------------------------
def grade_basis_columns(basis_label: str) -> List[str]:
    return GRADE_BASES[basis_label]["columns"]


def grade_basis_max(basis_label: str) -> float:
    return GRADE_BASES[basis_label]["max_marks"]


def marks_series(df: pd.DataFrame, basis_label: str) -> pd.Series:
    """Return the raw marks for a grade basis (G1/G2/G3 or G1+G2+G3)."""
    columns = [c for c in grade_basis_columns(basis_label) if c in df.columns]
    if not columns:
        raise KeyError(
            f"None of the columns {grade_basis_columns(basis_label)} exist in the dataset."
        )
    return df[columns].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)


def percentage_series(df: pd.DataFrame, basis_label: str) -> pd.Series:
    """
    Percentage = (Total Marks Obtained / Maximum Possible Marks) x 100

    * G3    -> (G3 / 20) x 100
    * G1+G2+G3 -> ((G1 + G2 + G3) / 60) x 100
    """
    maximum = grade_basis_max(basis_label)
    return (marks_series(df, basis_label) / maximum) * 100.0


def categorise_percentage(
    percentages: pd.Series,
    thresholds: Optional[Dict[str, float]] = None,
) -> pd.Series:
    """
    Map a percentage to a performance band.

    `thresholds` maps a category name to its *lower bound* (inclusive). Bands are
    evaluated from the highest lower bound downwards, so the dictionary can be
    edited from the UI without touching this function.
    """
    limits = thresholds or DEFAULT_THRESHOLDS
    ordered = sorted(limits.items(), key=lambda item: item[1], reverse=True)

    def classify(value: float) -> Optional[str]:
        if pd.isna(value):
            return np.nan
        for label, lower in ordered:
            if value >= lower:
                return label
        return ordered[-1][0]

    return percentages.apply(classify)


def age_group(value: Any) -> Optional[str]:
    if pd.isna(value):
        return np.nan
    age = float(value)
    if age <= 16:
        return AGE_GROUP_ORDER[0]
    if age <= 18:
        return AGE_GROUP_ORDER[1]
    if age <= 20:
        return AGE_GROUP_ORDER[2]
    return AGE_GROUP_ORDER[3]


def add_derived_columns(
    df: pd.DataFrame,
    thresholds: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Add the calculated columns used across the dashboard.

    * TotalMarks  = G1 + G2 + G3
    * Percentage  = G3 / 20 * 100 (the assignment's primary percentage definition)
    * Percentage_Combined = (G1 + G2 + G3) / 60 * 100
    * Performance = category of `Percentage`
    * Performance_Combined = category of `Percentage_Combined`
    * AgeGroup    = bucketed age for filtering
    * Gender      = readable label for the `sex` code
    """
    work = df.copy()
    limits = thresholds or DEFAULT_THRESHOLDS

    if all(c in work.columns for c in ("G1", "G2", "G3")):
        work["TotalMarks"] = work[["G1", "G2", "G3"]].apply(
            pd.to_numeric, errors="coerce"
        ).sum(axis=1)
        work["Percentage"] = (work["G3"] / MAX_MARK_PER_PERIOD) * 100.0
        work["Percentage_Combined"] = (work["TotalMarks"] / 60.0) * 100.0
        work["Performance"] = categorise_percentage(work["Percentage"], limits)
        work["Performance_Combined"] = categorise_percentage(
            work["Percentage_Combined"], limits
        )
    else:
        work["TotalMarks"] = np.nan
        work["Percentage"] = np.nan
        work["Percentage_Combined"] = np.nan
        work["Performance"] = np.nan
        work["Performance_Combined"] = np.nan

    if "age" in work.columns:
        work["AgeGroup"] = work["age"].apply(age_group)
    if "sex" in work.columns:
        work["Gender"] = work["sex"].map(GENDER_LABELS).fillna(work["sex"])
    return work


def with_basis_columns(
    df: pd.DataFrame,
    basis_label: str,
    thresholds: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Return a copy of `df` where `Percentage` / `Performance` reflect the currently
    selected grade basis. This keeps every page consistent with the UI selector.
    """
    work = df.copy()
    limits = thresholds or DEFAULT_THRESHOLDS
    work["Marks"] = marks_series(work, basis_label)
    work["MaxMarks"] = grade_basis_max(basis_label)
    work["Percentage"] = (work["Marks"] / work["MaxMarks"]) * 100.0
    work["Performance"] = categorise_percentage(work["Percentage"], limits)
    work["GradeBasis"] = GRADE_BASES[basis_label]["label"]
    return work


# --------------------------------------------------------------------------------------
# Filtering helpers
# --------------------------------------------------------------------------------------
def apply_filters(
    df: pd.DataFrame,
    genders: Optional[Iterable[str]] = None,
    schools: Optional[Iterable[str]] = None,
    age_groups: Optional[Iterable[str]] = None,
    categories: Optional[Iterable[str]] = None,
    grade_range: Optional[Tuple[float, float]] = None,
) -> pd.DataFrame:
    """Apply the dashboard filters. Empty/None selections mean 'no restriction'."""
    work = df
    if genders:
        genders = list(genders)
        if genders and "Gender" in work.columns:
            work = work[work["Gender"].isin(genders)]
    if schools:
        schools = list(schools)
        if schools and "school" in work.columns:
            work = work[work["school"].isin(schools)]
    if age_groups:
        age_groups = list(age_groups)
        if age_groups and "AgeGroup" in work.columns:
            work = work[work["AgeGroup"].isin(age_groups)]
    if categories:
        categories = list(categories)
        if categories and "Performance" in work.columns:
            work = work[work["Performance"].isin(categories)]
    if grade_range and "Marks" in work.columns:
        low, high = grade_range
        work = work[(work["Marks"] >= low) & (work["Marks"] <= high)]
    return work.reset_index(drop=True)


def summary_of_dataset(df: pd.DataFrame, subject_label: str) -> Dict[str, Any]:
    """Compact dataset facts used by the KPI row and the PDF report."""
    return {
        "Subject": subject_label,
        "Students (records)": int(len(df)),
        "Columns": int(df.shape[1]),
        "Schools": ", ".join(sorted(df["school"].dropna().unique())) if "school" in df else "-",
        "Age range": f"{int(df['age'].min())}-{int(df['age'].max())}" if "age" in df else "-",
        "Female students": int((df.get("Gender") == "Female").sum()) if "Gender" in df else 0,
        "Male students": int((df.get("Gender") == "Male").sum()) if "Gender" in df else 0,
        "Missing values": int(df.isna().sum().sum()),
        "Duplicate rows": int(df.duplicated().sum()),
    }
