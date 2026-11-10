# Student Grades Analysis: Project Report

**Dataset:** UCI Student Performance (Cortez & Silva, 2008)
**Cohorts analysed:** Mathematics (`student-mat.csv`, 395 students) and Portuguese (`student-por.csv`, 649 students)
**Grade basis for the headline results:** final grade `G3` (0 to 20 scale)
**Tooling:** Python 3.11, Pandas, NumPy, Plotly, Matplotlib, Seaborn, Streamlit, ReportLab

> Every figure in this report is computed from the dataset at run time by `run_analysis.py` / `app.py`. None of it is typed in by hand. Regenerate with:
> `python run_analysis.py --subject "Both subjects" --ethnicity data/sample_ethnicity_DEMO.csv`

---

## 1. Executive summary

* **1,044** student records were analysed after cleaning (591 female, 453 male).
* The overall average final grade is **11.34 / 20**, which is **56.71%** of the maximum. Marks span the full range from **0 to 20**.
* Female students average **11.45** (57.24%) against **11.20** (56.02%) for male students, a gap of **0.25 marks**. The difference is small relative to the within-group spread (standard deviation of about 3.9 marks in both groups).
* **77.97%** of students reach at least 10/20.
* The largest performance band is **Average (40-59%)** with 434 students (41.6%), followed by Good with 306 (29.3%).
* The earlier assessments are the strongest predictors of the final grade (`G2` r = 0.911, `G1` r = 0.809), and past failures are the strongest negative one (r = -0.383).
* The dataset carries **no ethnicity attribute**, so objective 4 is delivered as a merge-ready pipeline that runs on a genuinely labelled external dataset; the bundled sample is clearly marked as illustrative.

---

## 2. Dataset description

| Attribute | Value |
|-----------|-------|
| Source | UCI ML Repository, Student Performance |
| Records | 395 (Mathematics) + 649 (Portuguese) = 1,044 |
| Attributes | 30 source attributes plus calculated columns |
| Grade scale | 0-20 for G1, G2, G3 |
| Schools | GP (Gabriel Pereira), MS (Mousinho da Silveira) |
| Age range | 15 to 22 |
| Missing values in source | 0 |
| Duplicate records in source | 0 |

**Attribute groups**

* **Demographic:** `school`, `sex`, `age`, `address`, `famsize`, `Pstatus`
* **Family:** `Medu`, `Fedu` (education 0-4), `Mjob`, `Fjob`, `guardian`
* **Study habits:** `studytime`, `failures`, `schoolsup`, `famsup`, `paid`, `activities`, `higher`, `internet`
* **Lifestyle:** `famrel`, `freetime`, `goout`, `Dalc`, `Walc`, `health`, `absences`
* **Academic:** `G1`, `G2`, `G3`

**Two data caveats that shape the design**

1. There is no ethnicity field. Relabelling `Medu`, `Mjob` or `address` as ethnicity would be a fabrication, so objective 4 uses a separate, genuinely labelled dataset instead.
2. There is no student identifier. The pipeline generates `MAT-001` / `POR-001` style row IDs so records can be joined to an external ethnicity file.

---

## 3. Methodology

1. **Loading.** CSVs are read with separator detection (the UCI files are semicolon separated) and uploaded files are accepted with either `;` or `,`.
2. **Validation.** The schema is checked against the expected attribute list; missing values, duplicates and out-of-range grades are reported before any analysis.
3. **Cleaning.** Empty rows/columns and duplicates are removed, numeric columns are coerced, grades are clipped to 0-20, and any residual gaps are imputed with the median (numeric) or mode (categorical). Each step is logged and displayed in the Dataset Explorer.
4. **Feature engineering.** `TotalMarks = G1 + G2 + G3`, `Percentage = marks / maximum * 100`, `Performance` = threshold band, `AgeGroup` = bucketed age.
5. **Statistics.** Pandas `groupby` aggregations produce mean, min, max, count, median and standard deviation per gender and per ethnicity group.
6. **Percentage formulas.** Final grade: `(G3 / 20) * 100`. Combined: `((G1 + G2 + G3) / 60) * 100`.
7. **Performance bands** (configurable in the dashboard):

| Category | Range |
|----------|-------|
| Excellent | >= 90% |
| Very Good | 75% to 89.99% |
| Good | 60% to 74.99% |
| Average | 40% to 59.99% |
| Needs Improvement | < 40% |

8. **Visualisation.** Plotly for interactive figures, Matplotlib/Seaborn for the static PNG renders used in the PDF.
9. **Reporting.** ReportLab assembles the PDF from the same dataframes, embedding the rendered charts.

---

## 4. Objective 1: gender-wise statistical analysis

Computed with a single `groupby('Gender')` aggregation over the real `sex` column.

| Gender | Students | Average marks | Minimum | Maximum | Median | Std. dev. | Average % |
|--------|---------:|--------------:|--------:|--------:|-------:|----------:|----------:|
| Female | 591 | 11.45 | 0 | 19 | 12.0 | 3.87 | 57.24% |
| Male | 453 | 11.20 | 0 | 20 | 11.0 | 3.85 | 56.02% |

**Combined grade basis (G1 + G2 + G3, out of 60):** Female 34.05 (56.74%), Male 33.48 (55.81%).

**Reading it:** the female average is 0.25 marks higher, but the two distributions overlap heavily. Both groups span nearly the whole scale, and their standard deviations differ by 0.02. Treat the gap as a small sample difference, not a performance verdict.

---

## 5. Objective 2: gender-wise performance charts

![Average marks by gender](assets/charts/01_gender_average_marks.png)

![Students by gender](assets/charts/02_gender_student_count.png)

![G1 vs G2 vs G3 comparison by gender](assets/charts/05_g1_g2_g3_comparison.png)

![G3 distribution by gender](assets/charts/04_grade_distribution_by_gender.png)

The dashboard versions of these charts are interactive and can be switched between `G1`, `G2`, `G3` and the combined grade without leaving the page.

---

## 6. Objective 3: percentage and performance categories

Each student receives a `Percentage` column and a performance band.

| Category | Students | Share | Average % | Range |
|----------|---------:|------:|----------:|-------|
| Excellent | 35 | 3.4% | 91.29 | 90-100 |
| Very Good | 169 | 16.2% | 78.61 | 75-85 |
| Good | 306 | 29.3% | 64.79 | 60-70 |
| Average | 434 | 41.6% | 49.47 | 40-55 |
| Needs Improvement | 100 | 9.6% | 14.30 | 0-35 |

![Performance category distribution](assets/charts/07_performance_distribution.png)

**Reading it:** 49% of students sit in Excellent, Very Good or Good, while 9.6% (100 students) fall below 40%. That bottom group is the natural target for intervention. Because the thresholds are configurable in the sidebar, the same classification can be re-cut for a different grading policy without touching the code.

---

## 7. Objective 4: ethnicity-wise performance analysis

### The issue with the source data

The UCI dataset contains no ethnicity attribute. Presenting another field as ethnicity would produce a false result, so the project does not do that. Instead it provides a full pipeline for a compatible dataset:

1. Upload a CSV with an ethnicity column plus either a `StudentID` (e.g. `MAT-001`) or a row count matching the student dataset.
2. Choose the ethnicity column and the match method (ID merge, or row order).
3. The app merges the labels, then computes per-group student count, total marks, average marks, minimum, maximum, average percentage and share of all marks.
4. Groups are ranked by **average marks per student** (ties break on average percentage, then on student count) and the winner is reported with the gap to the runner-up.
5. A pie chart shows each group's share of total marks.

### Demonstration run (illustrative labels, not real data)

Using the bundled `data/sample_ethnicity_DEMO.csv`, whose groups are assigned deterministically and **independently of student performance**:

| Group | Students | Total marks | Average marks | Min | Max | Average % | Share of marks |
|-------|---------:|------------:|--------------:|----:|----:|----------:|---------------:|
| Group E | 95 | 1,181 | 12.43 | 0 | 18 | 62.16% | 9.97% |
| Group A | 330 | 3,935 | 11.92 | 0 | 19 | 59.62% | 33.23% |
| Group B | 269 | 2,960 | 11.00 | 0 | 20 | 55.02% | 25.00% |
| Group C | 200 | 2,190 | 10.95 | 0 | 19 | 54.75% | 18.50% |
| Group D | 150 | 1,575 | 10.50 | 0 | 19 | 52.50% | 13.30% |

**Best performing group: Group E (12.43 average marks, 62.16%), 0.51 marks ahead of Group A.**

**Important:** those labels were generated at random with respect to grades, so the ranking above is statistical noise. It demonstrates that the workflow runs end to end. Real conclusions require a genuine ethnicity dataset, which can be uploaded on the Ethnicity Analysis page.

![Total marks by ethnicity (illustrative labels)](assets/charts/09_ethnicity_pie.png)

---

## 8. Additional analysis

### Cohort comparison

| Subject | Students | Average marks | Average % | Highest | Lowest | Pass rate (>= 10/20) |
|---------|---------:|--------------:|----------:|--------:|-------:|---------------------:|
| Mathematics | 395 | 10.42 | 52.08% | 20 | 0 | 67.09% |
| Portuguese | 649 | 11.91 | 59.53% | 19 | 0 | 84.59% |

Portuguese results are stronger on every measure: 1.49 marks higher on average and a pass rate 17.5 points higher. Mathematics has the wider spread and produces the only 20/20 scores.

### Grade progression

![G1 to G3 progression](assets/charts/05_g1_g2_g3_comparison.png)

![Percentage distribution by gender](assets/charts/06_gender_percentage.png)

### Correlations with the final grade

| Variable | r with G3 | Direction |
|----------|----------:|-----------|
| G2 | 0.911 | Positive |
| G1 | 0.809 | Positive |
| Past failures | -0.383 | Negative |
| Mother's education | 0.201 | Positive |
| Weekly study time | 0.162 | Positive |
| Father's education | 0.160 | Positive |
| Absences | -0.046 | Essentially none |

![Correlation heatmap](assets/charts/08_correlation_heatmap.png)

Prior attainment dominates: G1 and G2 explain most of the variance in G3. Of the background variables, parental education and study time carry small positive associations, while failures carry a clear negative one. Absences show almost no linear relationship in this sample.

---

## 9. Findings

1. **Gender difference is real but small and cohort-dependent.** Overall, female students average 11.45 against 11.20 for male students. Split by subject, the direction reverses: in Mathematics, male students lead (10.91 vs 9.97), while in Portuguese, female students lead (12.25 vs 11.41). Reporting only the pooled figure would hide this, which is why the dashboard keeps a subject filter.
2. **The distribution is wide, not bimodal.** Marks run from 0 to 20 with a standard deviation near 3.9 and a median (11-12) close to the mean (11.34). Most students cluster in the Average and Good bands.
3. **About one student in ten needs support.** 100 students score below 40%, mostly in the Needs Improvement band, and Mathematics accounts for a disproportionate share of low results.
4. **Early grades predict final grades strongly.** G2 alone correlates at 0.911 with G3, which makes the first two periods the practical early-warning signal.
5. **Ethnicity analysis is methodologically gated, not skipped.** The pipeline is complete and tested, and it refuses to invent labels. With a genuine labelled dataset, the same page produces per-group statistics and the best-performing group.

---

## 10. Conclusion

The project turns the UCI Student Performance dataset into a working analytics system: it loads and cleans real data, computes verifiable statistics with Pandas and NumPy, classifies students into configurable performance bands, and presents everything through a responsive dashboard with interactive charts, dynamic filters, CSV exports and a generated PDF report. Three objectives are answered directly from the dataset's own fields. The fourth is handled honestly: the source has no ethnicity attribute, so the system provides a merge-ready ethnicity pipeline and clearly separates real data from the illustrative sample used for demonstration.

## 11. Limitations

* The dataset is observational, drawn from two Portuguese secondary schools, and describes that sample only. No causal claim is made.
* Grades use a 0-20 scale; percentages are computed against 20 per period and 60 for the combined basis.
* Student IDs are generated row identifiers, not personal identifiers.
* Ethnicity results depend entirely on the quality and provenance of an uploaded ethnicity dataset.
* Groups with very few students produce unstable averages; the student count is always displayed next to the average for that reason.

## 12. Reproducing this report

```bash
pip install -r requirements.txt
python run_analysis.py --subject "Both subjects" \
    --basis "Final grade (G3)" \
    --ethnicity data/sample_ethnicity_DEMO.csv
```

Artefacts written to `reports/` (CSVs, PDF) and `assets/charts/` (PNG charts). The same PDF is available from the dashboard under **Download Reports**, built from whatever filters are active.

## 13. Deployment

The dashboard is packaged for **Streamlit Community Cloud** with GitHub as the source repository. It needs no preparation step: `streamlit run app.py` loads the bundled CSVs, cleans them and renders all eight pages. Dependencies are pinned in `requirements.txt`, the light theme and palette live in `.streamlit/config.toml`, and all file paths are resolved with `pathlib` from the project folder. `README.md` documents the GitHub upload and the seven deployment steps.

The project was verified locally against every requirement (all pages, filters, statistics, both cohorts, ethnicity merge, CSV/PNG/PDF exports and a clean start with the exact deployment command). It has **not** been deployed to the cloud from the development environment, because that step needs the repository owner's GitHub account.
