"""
Generate the bundled ILLUSTRATIVE ethnicity sample file.

The UCI dataset has no ethnicity column. This script builds a demo mapping purely to
exercise the upload -> merge -> analyse workflow during a project demonstration.
It is NOT real ethnicity data and the dashboard labels it as such.
"""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from modules import data_loader  # noqa: E402

OUT = PROJECT_ROOT / "data" / "sample_ethnicity_DEMO.csv"
LABELS = ["Group A", "Group B", "Group C", "Group D", "Group E"]
WEIGHTS = [30, 25, 20, 15, 10]  # percentages -> unequal group sizes

rows = []
for subject in ("Mathematics", "Portuguese"):
    raw = data_loader.load_subject(subject)
    cleaned, _ = data_loader.clean_dataset(raw)
    cleaned["Subject"] = subject
    cleaned = data_loader.assign_student_ids(cleaned)
    for i, student_id in enumerate(cleaned["StudentID"]):
        # Deterministic, grade-independent assignment that follows the weight pattern.
        slot = int((i % 100) + 1)
        cumulative, label = 0, LABELS[-1]
        for candidate, weight in zip(LABELS, WEIGHTS):
            cumulative += weight
            if slot <= cumulative:
                label = candidate
                break
        rows.append({
            "StudentID": student_id,
            "Ethnicity": label,
            "Data_Source": "ILLUSTRATIVE SAMPLE - not real ethnicity data",
        })

frame = pd.DataFrame(rows)
frame.to_csv(OUT, index=False)
print(f"wrote {OUT}: {len(frame)} rows, groups={frame['Ethnicity'].nunique()}")
print(frame["Ethnicity"].value_counts().to_string())
