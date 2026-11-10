"""
Central configuration for the Student Grades Analysis project.

Everything that a college evaluation might want to tweak (performance thresholds,
colour palette, dataset locations, grade bases) lives here so the rest of the code
stays declarative and easy to read.

Deployment note
---------------
Every path in this module is derived from the location of *this file*, using
``pathlib``. Nothing depends on the current working directory and there are no
absolute, machine-specific paths, so the project behaves identically on a laptop
and on Streamlit Community Cloud (Linux).
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------------------
# Paths (all relative to the project root, never to the current working directory)
# --------------------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
SCREENSHOT_DIR: Path = ASSETS_DIR / "screenshots"
CHART_DIR: Path = ASSETS_DIR / "charts"
SAMPLE_ETHNICITY_PATH: Path = DATA_DIR / "sample_ethnicity_DEMO.csv"


def project_path(*parts: str) -> Path:
    """Build an absolute path inside the project root, e.g. project_path('data', 'x.csv')."""
    return PROJECT_ROOT.joinpath(*parts)


def ensure_dir(path: str | Path) -> Path:
    """
    Create a directory if needed and return it.

    On a read-only or ephemeral filesystem (some cloud hosts) the ``mkdir`` can fail;
    that must never crash the app, so the failure is swallowed and the path is
    returned unchanged. Callers that truly need a writable directory use a temp dir.
    """
    directory = Path(path)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return directory


# --------------------------------------------------------------------------------------
# Dataset metadata (UCI Student Performance, Cortez & Silva 2008)
# --------------------------------------------------------------------------------------
DATASET_HOMEPAGE = "https://archive.ics.uci.edu/ml/datasets/Student+Performance"

# The bundled CSVs in data/ are always used first, so the app starts offline and fast.
# These mirrors are only a fallback for a clone that is missing the data files.
DATASET_ZIP_URLS = [
    "https://archive.ics.uci.edu/static/public/320/student+performance.zip",
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip",
]

SUBJECTS = {
    "Mathematics": {
        "file": "student-mat.csv",
        "zip_member": "student-mat.csv",
        "code": "MAT",
        "description": "Mathematics course, 395 students (UCI student-mat.csv)",
    },
    "Portuguese": {
        "file": "student-por.csv",
        "zip_member": "student-por.csv",
        "code": "POR",
        "description": "Portuguese language course, 649 students (UCI student-por.csv)",
    },
}

SUBJECT_OPTIONS = ["Mathematics", "Portuguese", "Both subjects"]

# Column that is *actually* present in the dataset and is used for the gender analysis.
GENDER_COLUMN = "sex"
GENDER_LABELS = {"F": "Female", "M": "Male"}

# --------------------------------------------------------------------------------------
# Grade handling
# --------------------------------------------------------------------------------------
GRADE_COLUMNS = ["G1", "G2", "G3"]
MAX_MARK_PER_PERIOD = 20.0  # UCI grades are on a 0-20 scale

GRADE_BASES = {
    "Final grade (G3)": {"columns": ["G3"], "max_marks": 20.0, "label": "G3"},
    "First period (G1)": {"columns": ["G1"], "max_marks": 20.0, "label": "G1"},
    "Second period (G2)": {"columns": ["G2"], "max_marks": 20.0, "label": "G2"},
    "Combined (G1 + G2 + G3)": {"columns": ["G1", "G2", "G3"], "max_marks": 60.0, "label": "Combined"},
}
DEFAULT_GRADE_BASIS = "Final grade (G3)"

# --------------------------------------------------------------------------------------
# Performance categories (configurable from the sidebar, these are the defaults)
# --------------------------------------------------------------------------------------
DEFAULT_THRESHOLDS = {
    "Excellent": 90.0,           # >= 90 %
    "Very Good": 75.0,           # 75 - 89.99 %
    "Good": 60.0,                # 60 - 74.99 %
    "Average": 40.0,             # 40 - 59.99 %
    "Needs Improvement": 0.0,    # < 40 %
}

CATEGORY_ORDER = ["Excellent", "Very Good", "Good", "Average", "Needs Improvement"]

# --------------------------------------------------------------------------------------
# Visual identity: light background, white cards, navy type, purple/blue accents.
# These values mirror .streamlit/config.toml so the native widgets and the custom
# HTML/Plotly components share one palette.
# --------------------------------------------------------------------------------------
PALETTE = {
    "background": "#F7F5FC",
    "card": "#FFFFFF",
    "navy": "#17213D",
    "navy_soft": "#4A5578",
    "purple": "#6954D9",
    "blue": "#3B82F6",
    "teal": "#14B8A6",
    "amber": "#F59E0B",
    "rose": "#F43F5E",
    "grid": "#E6E9F2",
}

GENDER_COLORS = {
    "Female": "#6954D9",  # purple
    "Male": "#2563EB",    # blue
}

CATEGORY_COLORS = {
    "Excellent": "#6954D9",
    "Very Good": "#3B82F6",
    "Good": "#14B8A6",
    "Average": "#F59E0B",
    "Needs Improvement": "#F43F5E",
}

# Categorical sequence used for ethnicity groups (cycled if there are many groups).
ETHNICITY_COLORS = [
    "#6954D9", "#3B82F6", "#14B8A6", "#F59E0B", "#F43F5E",
    "#8B5CF6", "#0EA5E9", "#22C55E", "#EC4899", "#64748B",
]

# Palette for the correlation heatmap (purple -> white -> blue diverging look).
HEATMAP_SCALE = [
    [0.0, "#F43F5E"],
    [0.25, "#F9A8D4"],
    [0.5, "#FFFFFF"],
    [0.75, "#93C5FD"],
    [1.0, "#1D4ED8"],
]

PLOTLY_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"

# --------------------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------------------
AGE_GROUP_ORDER = ["15-16", "17-18", "19-20", "21 and above"]

# --------------------------------------------------------------------------------------
# Deployment guard rails
# --------------------------------------------------------------------------------------
# Uploaded CSV files larger than this are rejected with a helpful message instead of
# being read into memory (Streamlit Community Cloud has limited RAM).
MAX_UPLOAD_MB = 25
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
