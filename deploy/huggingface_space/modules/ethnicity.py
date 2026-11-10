"""
Optional ethnicity data handling.

The UCI Student Performance dataset has **no ethnicity column**, so the project
never relabels an existing field (such as mother's education or mother's job) as
ethnicity. Instead this module merges a *genuinely labelled* ethnicity dataset that
the user supplies, keyed either on a matching student ID or by row order.

Supported inputs
----------------
1. A file with a `StudentID` column (e.g. MAT-001) plus an ethnicity column.
2. A file whose row count matches the student dataset (assigned in the same order).
3. A file with a single ethnicity column and a matching row count.

If none of these are satisfied the merger raises a clear, actionable error.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .data_loader import read_csv_bytes

# Column names frequently used for ethnicity in external datasets.
CANDIDATE_ETHNICITY_COLUMNS = [
    "ethnicity", "Ethnicity", "ethnic_group", "EthnicGroup", "ethnicity_group",
    "race", "Race", "ethnic", "Ethnic", "ethnicity_label", "group", "Group",
]

CANDIDATE_ID_COLUMNS = ["StudentID", "student_id", "studentid", "ID", "id"]

DEMO_MARKER_COLUMN = "Data_Source"


def detect_ethnicity_column(df: pd.DataFrame) -> Optional[str]:
    """Best guess at the ethnicity column, or None if nothing looks right."""
    for name in CANDIDATE_ETHNICITY_COLUMNS:
        if name in df.columns:
            return name
    # Fall back to any column whose header mentions 'ethnic' or 'race'.
    for col in df.columns:
        lowered = str(col).lower()
        if "ethnic" in lowered or lowered == "race":
            return col
    return None


def is_demo_file(df: pd.DataFrame, filename: str = "") -> bool:
    """
    True when the uploaded file is the bundled illustrative sample.
    The dashboard shows an explicit warning for those labels.
    """
    if DEMO_MARKER_COLUMN in df.columns:
        return True
    return "demo" in (filename or "").lower()


def ethnicity_file_overview(df: pd.DataFrame) -> Dict[str, Any]:
    """Quick facts about an uploaded ethnicity file, shown before merging."""
    column = detect_ethnicity_column(df)
    overview: Dict[str, Any] = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "detected_ethnicity_column": column,
        "groups": int(df[column].nunique(dropna=True)) if column else 0,
        "group_names": sorted(df[column].dropna().unique().tolist())[:25] if column else [],
    }
    return overview


def merge_ethnicity(
    students: pd.DataFrame,
    ethnicity_bytes: bytes,
    filename: str = "",
    ethnicity_column: Optional[str] = None,
    mode: str = "Auto detect",
    id_column: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Merge an uploaded ethnicity dataset into the student frame.

    Returns `(merged_frame, info)` where `info` documents exactly how the merge was
    performed (method, matched rows, columns added, demo flag).
    """
    eth = read_csv_bytes(ethnicity_bytes)
    if eth.empty:
        raise ValueError("The uploaded ethnicity file contains no rows.")

    eth_clean = eth.dropna(axis=1, how="all").copy()
    column = ethnicity_column or detect_ethnicity_column(eth_clean)
    if column is None or column not in eth_clean.columns:
        raise ValueError(
            "Could not find an ethnicity column in the uploaded file. "
            "Please rename the column to 'Ethnicity' (or select it explicitly)."
        )

    eth_clean = eth_clean.rename(columns={column: "Ethnicity"})
    eth_clean["Ethnicity"] = eth_clean["Ethnicity"].astype(str).str.strip()
    eth_clean = eth_clean[eth_clean["Ethnicity"].ne("") & eth_clean["Ethnicity"].ne("nan")]

    demo = is_demo_file(eth_clean, filename)
    merged = students.copy()
    method = ""

    id_candidates = [c for c in CANDIDATE_ID_COLUMNS if c in eth_clean.columns]
    chosen_id = id_column if id_column in eth_clean.columns else (id_candidates[0] if id_candidates else None)

    use_id_merge = mode in ("Auto detect", "Merge on student ID") and chosen_id and "StudentID" in merged.columns
    use_id_merge = bool(use_id_merge)

    if use_id_merge:
        eth_subset = eth_clean[[chosen_id, "Ethnicity"]].drop_duplicates(subset=[chosen_id])
        eth_subset = eth_subset.rename(columns={chosen_id: "StudentID"})
        eth_subset["StudentID"] = eth_subset["StudentID"].astype(str).str.strip()
        merged = merged.merge(eth_subset, on="StudentID", how="left", validate="many_to_one")
        matched = int(merged["Ethnicity"].notna().sum())
        method = f"Merged on the '{chosen_id}' column"
    elif mode in ("Auto detect", "Assign by row order"):
        if len(eth_clean) != len(merged):
            raise ValueError(
                f"Row-order merge needs the same number of rows: the ethnicity file has "
                f"{len(eth_clean)} rows but the student dataset has {len(merged)}. "
                f"Add a StudentID column (e.g. MAT-001) to merge on a key instead."
            )
        merged["Ethnicity"] = eth_clean["Ethnicity"].reset_index(drop=True).values
        matched = len(merged)
        method = "Assigned by row order (files had identical row counts)"
    else:
        raise ValueError(
            "Could not merge the ethnicity file: it has no usable ID column and its row "
            "count differs from the student dataset. Add a StudentID column to merge on a key."
        )

    if matched == 0:
        raise ValueError(
            "No rows matched between the ethnicity file and the student dataset. "
            "Check that the StudentID values look like MAT-001 / POR-001."
        )

    unmatched = int(len(merged) - matched)
    info = {
        "method": method,
        "matched_rows": matched,
        "unmatched_rows": unmatched,
        "groups": int(merged["Ethnicity"].nunique(dropna=True)),
        "group_names": sorted(merged["Ethnicity"].dropna().unique().tolist()),
        "source_rows": int(len(eth_clean)),
        "source_columns": list(eth.columns),
        "demo_labels": bool(demo),
        "filename": filename or "uploaded file",
    }
    return merged, info


def incomplete_groups(summary: pd.DataFrame, min_students: int = 1) -> List[str]:
    """Groups with too few students to be statistically meaningful."""
    if summary is None or summary.empty:
        return []
    small = summary[summary["Students"] < min_students]
    return small["Ethnicity"].astype(str).tolist()
