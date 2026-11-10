#!/usr/bin/env python3
"""
Command-line runner for the Student Grades Analysis project.

Runs the entire analysis without the dashboard, which is handy for the project
evaluation (reproducible outputs) and for verifying the pipeline.

Examples
--------
python run_analysis.py
python run_analysis.py --subject Portuguese --basis "Combined (G1 + G2 + G3)"
python run_analysis.py --subject "Both subjects" --ethnicity data/sample_ethnicity_DEMO.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from modules import analysis, data_loader, pipeline
from modules.config import (
    CHART_DIR,
    DATASET_HOMEPAGE,
    DEFAULT_GRADE_BASIS,
    DEFAULT_THRESHOLDS,
    GRADE_BASES,
    REPORTS_DIR,
    SUBJECT_OPTIONS,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the complete student grades analysis.")
    parser.add_argument("--subject", default="Both subjects", choices=SUBJECT_OPTIONS,
                        help="Which UCI course file(s) to analyse.")
    parser.add_argument("--basis", default=DEFAULT_GRADE_BASIS, choices=list(GRADE_BASES.keys()),
                        help="Grade basis used for marks and percentages.")
    parser.add_argument("--ethnicity", default=None,
                        help="Optional CSV with real ethnicity data (StudentID + ethnicity column).")
    parser.add_argument("--outdir", default=str(REPORTS_DIR),
                        help="Directory for generated reports (default: reports/).")
    parser.add_argument("--chartdir", default=str(CHART_DIR),
                        help="Directory for chart PNGs (default: assets/charts/).")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    print("=" * 78)
    print(" Student Grades Analysis - command line run")
    print("=" * 78)
    print(f" Dataset source : {DATASET_HOMEPAGE}")
    print(f" Subject        : {args.subject}")
    print(f" Grade basis    : {args.basis}")
    print("-" * 78)

    base, cleaning_logs, validations, errors = pipeline.load_and_clean(args.subject)
    if errors:
        for error in errors:
            print(f"[warning] {error}")
    if base.empty:
        print("No data could be loaded. Check your connection or upload the CSVs manually.")
        return 1

    print(f" Loaded and cleaned: {len(base):,} student records, {base.shape[1]} columns")
    for subject, report in validations.items():
        print(f"   - {subject}: {report['n_rows']} rows | missing {report['total_missing']} | "
              f"duplicates {report['duplicate_rows']} | schema ok: {report['is_uci_schema']}")

    ethnicity_info = None
    if args.ethnicity:
        ethnicity_path = Path(args.ethnicity)
        payload = ethnicity_path.read_bytes()
        base, ethnicity_info, error = pipeline.attach_ethnicity(
            base, payload, filename=ethnicity_path.name
        )
        if error:
            print(f"[ethnicity] {error}")
        else:
            print(f"[ethnicity] merged {ethnicity_info['matched_rows']} rows via "
                  f"{ethnicity_info['method']} ({ethnicity_info['groups']} groups)")

    bundle = pipeline.build_analysis_bundle(base, args.basis, DEFAULT_THRESHOLDS)
    df = bundle["frame"]

    print("-" * 78)
    print(" KPI summary")
    for key, value in bundle["kpis"].items():
        print(f"   {key.replace('_', ' ').capitalize():<22}: {value}")

    print("-" * 78)
    print(" Objective 1 - gender-wise statistics")
    summary = bundle["gender_summary"]
    print(summary.to_string(index=False) if not summary.empty else "  No gender data available")

    print("-" * 78)
    print(" Objective 3 - performance bands")
    bands = bundle["percentage_bands"]
    print(bands.to_string(index=False) if not bands.empty else "  No percentage data")

    ethnicity_table = None
    if "Ethnicity" in df.columns:
        ethnicity_table = analysis.ethnicity_summary(df, "Ethnicity")
        print("-" * 78)
        print(" Objective 4 - ethnicity-wise performance")
        print(ethnicity_table.to_string(index=False))
        best = analysis.best_performing_ethnicity(ethnicity_table)
        if best:
            print(f"   Best performing group: {best['group']} "
                  f"(average {best['average_marks']:.2f} marks, {best['average_percentage']:.2f}%)")
    else:
        print("-" * 78)
        print(" Objective 4 - ethnicity-wise performance")
        print("   No ethnicity column available in the UCI dataset.")
        print("   Supply --ethnicity <file> with a genuine ethnicity column to run this objective.")

    subject_comparison = None
    if args.subject == "Both subjects":
        frames = {
            subject: data_loader.with_basis_columns(
                data_loader.add_derived_columns(base[base["Subject"] == subject], DEFAULT_THRESHOLDS),
                args.basis,
            )
            for subject in base["Subject"].unique()
        }
        subject_comparison = analysis.subject_comparison(frames)
        print("-" * 78)
        print(" Subject comparison")
        print(subject_comparison.to_string(index=False))

    slug = args.subject.lower().replace(" ", "_")
    paths = pipeline.write_report_outputs(
        bundle=bundle,
        output_dir=args.outdir,
        chart_dir=args.chartdir,
        subject_label=args.subject,
        cleaning_logs=cleaning_logs,
        validation_reports=validations,
        ethnicity_info=ethnicity_info,
        ethnicity_table=ethnicity_table,
        subject_comparison=subject_comparison,
        prefix=slug,
    )

    print("-" * 78)
    print(" Generated files")
    for key, value in paths.items():
        if key == "charts":
            for chart in value:
                print(f"   chart : {chart['path']}")
        else:
            print(f"   {key:<17}: {value}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
