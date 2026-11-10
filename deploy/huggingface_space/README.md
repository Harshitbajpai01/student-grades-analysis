---
title: Student Grades Analysis
emoji: bar_chart
colorFrom: purple
colorTo: indigo
sdk: streamlit
sdk_version: 1.67.0
app_file: app.py
pinned: false
license: mit
short_description: UCI student performance dashboard with gender and grade analysis
---

# Student Grades Analysis & Performance Dashboard

An interactive Streamlit dashboard for the UCI Student Performance dataset
(Mathematics and Portuguese). Eight pages cover an overview, dataset explorer,
gender-wise statistics, percentage bands, ethnicity analysis, interactive
visualisations, per-student performance and exportable reports (CSV, PNG charts,
PDF).

## What it does

- Cleans and prepares both cohorts on load (1,044 students after cleaning).
- Computes averages, pass rates, percentage bands and grade distributions, per
  subject and per gender, driven by the sidebar filters.
- Merges a labelled ethnicity dataset keyed by Student ID when one is uploaded.
  The UCI data has no ethnicity column, so the bundled file is clearly marked as
  synthetic demo data and nothing is relabelled.
- Exports the cleaned dataset, chart bundles and a generated PDF report.

## Data

`data/student-mat.csv` and `data/student-por.csv` are the UCI Student
Performance files (Cortez & Silva, 2008), bundled so the Space starts without any
network call. `data/sample_ethnicity_DEMO.csv` is synthetic and labelled as such
in the UI and in the reports.

Full documentation, local setup and deployment notes live in `PROJECT_README.md`.
