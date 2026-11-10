# Student Grades Analysis & Performance Dashboard

An interactive academic analytics dashboard built with **Python, Pandas, NumPy, Plotly, Matplotlib, Seaborn and Streamlit**. It analyses the **UCI Student Performance** dataset, computes real descriptive statistics, classifies every student into a performance band and produces downloadable CSV, PNG and PDF reports.

The project is packaged for **one-command deployment on Streamlit Community Cloud** with GitHub as the source repository: `streamlit run app.py` is the only command needed, and no pre-processing step has to be run first.

The project covers all four assignment objectives:

| # | Objective | Where it lives |
|---|-----------|----------------|
| 1 | Gender-wise statistical analysis (average, min, max, count, average %) | `Gender Analysis` page, `modules/analysis.py` |
| 2 | Gender-wise performance bar charts | `Gender Analysis` page, `modules/visualizations.py` |
| 3 | Percentage calculation and configurable performance categories | `Percentage Analysis` page, `modules/data_loader.py` |
| 4 | Ethnicity-wise performance analysis with a genuine ethnicity dataset | `Ethnicity Analysis` page, `modules/ethnicity.py` |

---

## 1. Project overview

**Goal:** examine student grades and academic performance, quantify the spread of results, compare performance by gender, and identify which demographic group performs best, with every figure computed from the real dataset rather than assumed.

**What the dashboard does**

* Loads the two UCI cohorts (Mathematics, Portuguese) from bundled CSV files, validates and cleans them, and shows the full cleaning log.
* Computes gender-wise average, minimum, maximum, count and average percentage, and renders the matching comparison charts.
* Adds a `Percentage` column and a configurable performance category for every student.
* Runs the ethnicity objective the only honest way possible: by merging a genuinely labelled ethnicity dataset that you supply.
* Exports the results as CSV tables, PNG charts, a ZIP of all charts, and a complete PDF report.

**What this project does not do:** it does not invent demographic data, and it does not claim a cloud deployment that has not happened (see [section 10](#10-verification-status)).

---

## 2. Main features

**Dashboard (8 pages)**

1. **Overview** — seven live KPI cards, subject comparison, headline insights.
2. **Dataset Explorer** — schema validation, missing/duplicate detection, cleaning log, preview, descriptive statistics, column dictionary, cleaned-data download.
3. **Gender Analysis** — objective 1 summary table plus objective 2 charts (average, minimum, maximum, student count, grade distribution, percentage spread) with a G1 / G2 / G3 / combined selector.
4. **Percentage Analysis** — the `Percentage` column, configurable bands, band summary, student-level percentage report.
5. **Ethnicity Analysis** — upload and merge a real ethnicity dataset, group summary, student-wise totals, pie chart, best-performing group and a written methodology.
6. **Visualizations** — the complete required chart gallery (8 charts plus extras).
7. **Student Performance** — search by Student ID, sort, top/bottom performers, single-student profile.
8. **Download Reports** — cleaned dataset, analysis tables, chart ZIP and the generated PDF report.

**Filters and interactivity**

Sidebar controls: subject dataset, grade basis, gender, school, age group, grade range, performance category and the performance thresholds. **Every KPI, table and chart recomputes from the filtered data** on each change, and the selection persists as you move between pages. A single **Reset all filters** button restores the defaults.

**Exports**

| Export | Format | Where |
|--------|--------|-------|
| Cleaned dataset | CSV (UTF-8 with BOM, opens in Excel) | Dataset Explorer, Download Reports |
| Gender analysis, percentage report, ethnicity analysis | CSV | Gender / Percentage / Ethnicity pages, Download Reports |
| All charts | ZIP of 8-10 PNG renders | Download Reports |
| Full project report | PDF (11 pages) | Download Reports |

**Deployment features**

* All paths are resolved with `pathlib` from the project folder, so nothing depends on the working directory or on a local machine layout.
* Datasets load from the bundled `data/` folder first, so the app starts instantly and works without internet access. The UCI download is only a fallback for a clone that is missing the CSVs.
* `@st.cache_data` on dataset loading, cleaning and frame preparation; no repeated parsing or recalculation between reruns.
* Uploads are parsed in memory, size-checked, never written to the project folder, and never mixed into the bundled sample data.
* Generated charts and PDFs are built in temporary directories that clean themselves up, with only the finished bytes kept in session state.

---

## 3. Technology stack

| Layer | Tools |
|-------|-------|
| Language | Python 3.11 (tested); works on 3.10-3.12 |
| Data analysis | Pandas, NumPy |
| Interactive charts | Plotly |
| Static charts (PNG, PDF figures) | Matplotlib, Seaborn (Agg backend) |
| PDF report | ReportLab, Pillow |
| Dashboard / frontend | Streamlit (light theme, white cards, navy type, purple and blue accents) |
| Deployment | GitHub + Streamlit Community Cloud |

Pinned versions are in [`requirements.txt`](requirements.txt).

---

## 4. Dataset information

* **Source:** UCI Machine Learning Repository, Student Performance (Cortez & Silva, 2008)
  <https://archive.ics.uci.edu/ml/datasets/Student+Performance>
* **Files:** `student-mat.csv` (Mathematics, **395** students) and `student-por.csv` (Portuguese, **649** students), both bundled in `data/`.
* **Fields:** 30 attributes per student covering demographics (`sex`, `age`, `school`, `address`, `famsize`), family background (`Medu`, `Fedu`, `Mjob`, `Fjob`), study habits (`studytime`, `failures`, `absences`) and three grades: `G1`, `G2`, `G3`, each on a **0 to 20** scale.

### Two honest notes about the data

1. **There is no ethnicity column.** The dataset records gender, age, school and family background, but no ethnicity or race attribute. This project therefore never relabels a field such as mother's education or mother's job as "ethnicity". The Ethnicity Analysis page instead accepts a **separate, genuinely labelled ethnicity dataset**, merged by Student ID (e.g. `MAT-001`) or by row order.
2. **There is no student ID column.** Reproducible identifiers are generated as `<subject code>-<row number>` (`MAT-001`, `POR-001`, ...). These are row identifiers, not personal identifiers.

`data/sample_ethnicity_DEMO.csv` is a bundled **illustrative** file used to demonstrate the objective-4 workflow. Its labels are synthetic (`Group A` … `Group E`), the file name and a `Data_Source` column say so, and the UI shows a red warning whenever it is in use. It must not be presented as real findings.

---

## 5. Project structure

```
student-grades-analysis/
├── app.py                          # Streamlit dashboard (8 pages)
├── run_analysis.py                 # Headless CLI runner
├── requirements.txt                # Pinned dependencies
├── README.md
├── REPORT.md                       # Written project report with results
├── .gitignore
├── .streamlit/
│   └── config.toml                 # Light theme, palette, server settings
├── data/
│   ├── student-mat.csv             # UCI Mathematics cohort (395 students)
│   ├── student-por.csv             # UCI Portuguese cohort (649 students)
│   ├── student-attribute-info.txt
│   └── sample_ethnicity_DEMO.csv   # Illustrative only, clearly labelled
├── modules/
│   ├── config.py                   # Paths (pathlib), palette, grade bases, thresholds
│   ├── data_loader.py              # Loading, validation, cleaning, derived columns
│   ├── analysis.py                 # groupby statistics, bands, correlations
│   ├── ethnicity.py                # Optional ethnicity merge and ranking
│   ├── visualizations.py           # Interactive Plotly figures
│   ├── static_charts.py            # Matplotlib/Seaborn renders for PNG + PDF
│   ├── reports.py                  # CSV export and the ReportLab PDF report
│   ├── pipeline.py                 # Shared orchestration for UI and CLI
│   └── theme.py                    # Dashboard CSS, KPI cards, notices
├── assets/
│   ├── screenshots/                # Captured screenshots of every page
│   └── charts/                     # Generated chart PNGs (regenerable)
├── reports/                        # Generated CSVs and PDF (regenerable)
├── deploy/
│   └── huggingface_space/          # Self-contained copy packaged as a HF Space
├── Dockerfile                      # Container route (Render, Railway, Koyeb, Fly.io)
├── render.yaml                     # Render blueprint
├── Procfile                        # Buildpack start command
├── runtime.txt                     # Python version for buildpack hosts
└── tools/
    └── make_demo_ethnicity.py      # Rebuilds the illustrative ethnicity sample
```

The structure follows the requested layout; the only deviation is `modules/` instead of `src/`, because that is the package name the existing project already uses, and renaming it would churn every import for no benefit.

---

## 6. Local installation

```bash
# 1. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

Python 3.10+ is required (developed and tested on Python 3.11).

### Run the dashboard

```bash
streamlit run app.py
```

Open <http://localhost:8501>. The bundled CSVs in `data/` load automatically; there is no separate preparation step and nothing has to be run before the app.

### Run the analysis without the UI

Useful for a reproducible evaluation or to regenerate every artefact:

```bash
# both cohorts, final grade basis
python run_analysis.py

# one cohort, combined grade basis
python run_analysis.py --subject Portuguese --basis "Combined (G1 + G2 + G3)"

# with the bundled demo ethnicity file (labels are illustrative)
python run_analysis.py --subject "Both subjects" --ethnicity data/sample_ethnicity_DEMO.csv
```

Outputs land in `reports/` (CSVs and the PDF report) and `assets/charts/` (PNG charts). Both directories can be deleted at any time; the app regenerates them on demand.

---

## 7. Deploying to Streamlit Community Cloud with GitHub

### 7.1 Upload the project to GitHub

**Option A: GitHub web interface (no Git knowledge needed)**

1. Sign in at <https://github.com> and click **New repository**.
2. Name it `student-grades-analysis`, choose **Public** (Streamlit Community Cloud deploys from public repositories on the free plan; private repositories need the owner to authorise GitHub access), then click **Create repository**.
3. On the empty repository page click **uploading an existing file**.
4. Drag the *contents* of the `student-grades-analysis` folder into the upload area. Keep the folder structure: `.streamlit/`, `data/`, `modules/`, `assets/`, `reports/`, `app.py`, `requirements.txt`, `README.md`, `.gitignore`.
   * On macOS press `Cmd + Shift + .` to reveal `.streamlit` and `.gitignore`, which are hidden by default.
   * If drag and drop hides the dot-folders, create them with **Add file → Create new file** and type `.streamlit/config.toml` as the file name.
5. Commit with a message such as `Student Grades Analysis - deployment ready`.

**Option B: command line**

```bash
cd student-grades-analysis
git init
git add .
git commit -m "Student Grades Analysis - deployment ready"
git branch -M main
git remote add origin https://github.com/<your-username>/student-grades-analysis.git
git push -u origin main
```

Check with `git status --ignored` that `.streamlit/secrets.toml`, `.env` and `__pycache__/` were **not** committed.

### 7.2 Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io/> and sign in with GitHub.
2. Click **Create app**, then **Yup, I have an app**.
3. **Repository:** `<your-username>/student-grades-analysis`
4. **Branch:** `main`
5. **Main file path:** `app.py`
6. **App URL (optional):** pick a subdomain, e.g. `student-grades-analysis`.
7. Open **Advanced settings** and set **Python version** to **3.11** (the version this project was tested on; 3.12 also works). No secrets are required.
8. Click **Deploy**. The first build installs `requirements.txt` and usually finishes in 2-4 minutes.

The app is live at `https://<your-subdomain>.streamlit.app/` once the log shows the app has started.

### 7.3 What Streamlit Community Cloud needs from this repository

* `requirements.txt` at the repository root, with pinned versions: present.
* `app.py` as the entry point: present. Nothing else has to be run first.
* `data/` committed, so no download is needed at start-up. If `data/` is ever missing, the app downloads the archive from UCI on first run and caches it in the container.
* No write access to the container filesystem is required: charts and PDFs are generated in system temp directories.
* No secrets, no API keys, no `.env` file. `.streamlit/config.toml` only sets the light theme and server flags.

---

## 8. Deploying somewhere other than Streamlit Community Cloud

The app is a plain Streamlit app, so any host that runs Python or a container works. Three ready-made routes are included; nothing in the code changes between them.

### 8.1 Hugging Face Spaces (no GitHub account needed)

Best option if you would rather not use GitHub. Free, and Streamlit is a first-class SDK there.

1. Create an account at https://huggingface.co/join (email is enough).
2. Go to https://huggingface.co/new-space, pick a name, select **Streamlit** as the SDK, choose the **Free** hardware, and create the Space.
3. Open the **Files** tab, then drag the contents of `deploy/huggingface_space/` into the uploader (or drag the whole project folder once the Space exists). The `README.md` in that folder is the Space card that tells Hugging Face to run `app.py`.
4. Commit the upload. The Space builds automatically and serves the dashboard on its public URL.

`deploy/huggingface_space/` is a self-contained copy of the app (code, modules, datasets, `.streamlit/config.toml`, `requirements.txt`) prepared for exactly this. It has been booted and page-tested independently.

If you would rather push from the command line:

```bash
pip install huggingface_hub
huggingface-cli login            # paste an access token with write scope
cd deploy/huggingface_space
huggingface-cli upload <your-username>/<space-name> . --repo-type=space
```

### 8.2 Render, Railway, Koyeb or Fly.io (container or buildpack)

`Dockerfile`, `render.yaml`, `Procfile` and `runtime.txt` are included.

- **Render:** push the project to a repository, then **New → Blueprint** and select it (`render.yaml` sets the build and start commands). Free plan is enough. Streamlit must bind to the platform's `$PORT`, which the start command already does.
- **Railway / Koyeb / Fly.io:** point them at the repository or the `Dockerfile`; the container exposes port 8501 and answers `/_stcore/health`.
- **Any Docker host:** `docker build -t student-grades . && docker run -p 8501:8501 student-grades`

### 8.3 Vercel (Container Runtime)

Vercel now runs arbitrary containers on Fluid compute, so this Streamlit app deploys there unmodified through `Dockerfile.vercel` in the project root. Vercel's older serverless-only mode cannot host Streamlit, because the dashboard needs a long-lived HTTP server and a WebSocket stream; the container runtime is what makes it possible.

1. Install the CLI: `npm i -g vercel`
2. From the project folder: `vercel link` (creates or selects a project), then `vercel deploy --prod`
3. Or import the repository in the Vercel dashboard; Vercel detects `Dockerfile.vercel` and selects the Container preset.

`Dockerfile.vercel` starts Streamlit on the port Vercel provides (`$PORT`, default 80) and answers `/_stcore/health`. Idle instances scale to zero after five minutes and cold start on the next request, so the first visit after a quiet period takes a few seconds.

### 8.4 What every host needs

| Requirement | Where it comes from |
| --- | --- |
| Start command | `streamlit run app.py` (add `--server.port $PORT --server.address 0.0.0.0` on PaaS) |
| Python version | 3.11 (see `runtime.txt`) |
| Dependencies | `requirements.txt` |
| Data | bundled in `data/`, no download at boot |
| Theme | `.streamlit/config.toml` |
| Writable paths | exports use temp directories, so a read-only or ephemeral filesystem is fine |

## 9. Dashboard reference

### Performance bands (configurable in the sidebar)

| Category | Default range |
|----------|---------------|
| Excellent | 90% and above |
| Very Good | 75% - 89.99% |
| Good | 60% - 74.99% |
| Average | 40% - 59.99% |
| Needs Improvement | below 40% |

### Percentage formulas

```
Final grade     : Percentage = (G3 / 20) * 100
Combined grades : Percentage = ((G1 + G2 + G3) / 60) * 100
```

### Key results (both cohorts, final grade G3)

| Metric | Value |
|--------|-------|
| Students analysed | 1,044 (591 female, 453 male) |
| Average marks | 11.34 / 20 (56.7%) |
| Highest / lowest marks | 20 / 0 |
| Female average | 11.45 (57.24%) |
| Male average | 11.20 (56.02%) |
| Pass rate (>= 10/20) | 77.97% |
| Most common band | Average (41.6% of students) |

Full narrative, tables and embedded charts: see [`REPORT.md`](REPORT.md) and `reports/both_subjects_report.pdf`.

### Methodology summary

1. **Load** the CSVs with separator detection (the UCI files are semicolon-separated).
2. **Validate** the schema against the expected columns and report missing values, duplicates and out-of-range grades.
3. **Clean**: drop empty rows/columns and duplicates, coerce numeric types, clip grades to 0-20, impute residual gaps with the median (numeric) or mode (categorical). Every step is logged and shown in the UI.
4. **Derive** `StudentID`, `TotalMarks`, `Percentage`, `Percentage_Combined`, `Performance`, `Performance_Combined` and `AgeGroup`.
5. **Analyse** with Pandas `groupby` aggregations; percentages use NumPy division against the basis maximum.
6. **Visualise** with Plotly (interactive) and Matplotlib/Seaborn (static exports).
7. **Report** with ReportLab, embedding the real chart images and the real tables.

**Ethnicity ranking method:** groups are ranked by **average marks per student** for the selected grade basis, because raw totals reward larger groups. Ties break on average percentage, then on student count. The gap to the runner-up is always shown so small differences are not over-read.

---

## 10. Privacy and security

* **No secrets in the repository.** `.gitignore` excludes `.streamlit/secrets.toml`, `.env` and any variant of them, plus caches and generated output.
* **No credentials, API keys or personal data** are used anywhere in the project; the UCI dataset is public and contains no names or student identifiers.
* **Uploads stay in memory.** Uploaded CSVs are parsed from the in-memory buffer, are size-checked (empty files and anything above 25 MB are refused with a readable message), and are never written to `data/` or anywhere else. Your files therefore never mix with the bundled sample data or with another visitor's session.
* **Synthetic data is labelled.** The bundled ethnicity sample is named `sample_ethnicity_DEMO.csv`, carries a `Data_Source` column, and triggers an explicit warning banner and a PDF note when in use.
* **No telemetry.** `gatherUsageStats = false` in `.streamlit/config.toml`.

---

## 11. Verification status

Everything below was executed against this exact code before packaging.

| # | Check | Result |
|---|-------|--------|
| 1 | All 8 pages render | Passed: no Streamlit exception on any page; Plotly charts drawn per page 3 / 0 / 8 / 3 / 2 / 9 / 1 / 0 |
| 2 | Filters update KPIs | Passed: subject Mathematics 1,044 to 395 students; combined grade basis switches to "out of 60"; Female-only removes the male KPI; filters persist across pages; Reset restores 1,044 |
| 3 | Gender-wise average / min / max | Passed: Female 591 students, average 11.45, min 0, max 19; Male 453 students, average 11.20, min 0, max 20 |
| 4 | Percentage calculations | Passed: G3 basis gives 0-100%, combined basis uses `(G1+G2+G3)/60*100`, bands follow the configured thresholds |
| 5 | Mathematics and Portuguese analysis | Passed: 395 and 649 students; cohort comparison 10.42 vs 11.91 average marks |
| 6 | Ethnicity dataset merge | Passed: bundled sample merges by Student ID, 5 groups, best-group card (Group E, 12.43 marks), pie and bar charts |
| 7 | Pie chart and bar chart rendering | Passed: 2 Plotly charts on the Ethnicity page, 9 in the chart gallery |
| 8 | CSV downloads | Passed: cleaned dataset CSV, 1,044 rows, full column set |
| 9 | PDF generation and download | Passed: 11-page PDF, 771 KB, chart images embedded |
| 10 | No hardcoded local paths | Passed: no `C:\`, `C:/`, `localhost` or `127.0.0.1` in any Python file |
| 11 | Dependencies install | Passed: every pinned package is installed and imports cleanly in the tested environment |
| 12 | `streamlit run app.py` starts the whole app | Passed: starts headless from a clean environment, no warnings in the server log, serves HTTP 200 |

**Not claimed:** this project has **not** been deployed to Streamlit Community Cloud from this environment, because that requires your GitHub account and authorisation. The deployment steps above are the only remaining action, and the repository as packaged is ready for them.

---

## 12. Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| `FileNotFoundError: The dataset file for Mathematics ... is not in the data/ folder` | `data/student-mat.csv` or `student-por.csv` was not uploaded to GitHub. Add the `data/` folder, or upload the CSV from the sidebar. |
| Build stops with "Install dependencies" | `requirements.txt` is missing or has a typo. It must sit at the repository root, next to `app.py`. |
| Build fails on a package version | Check **Advanced settings → Python version** (use 3.11). After any dependency change click **Manage app → Reboot**. |
| `ModuleNotFoundError: modules` | The `modules/` folder was not uploaded, or the entry point is wrong. The main file path must be `app.py`. |
| Charts do not appear | `plotly` failed to install. Reboot the app and read the build log. |
| PNG ZIP or PDF export fails | Rendering needs `matplotlib`, `seaborn`, `reportlab` and `Pillow`; all are pinned in `requirements.txt`, and the in-app message names the cause. |
| Ethnicity merge reports "no rows matched" | Your file needs a `StudentID` column using the generated IDs (`MAT-001`, `POR-001`, ...), or the same number of rows as the dataset, or use "Assign by row order". |
| Upload is rejected | Empty files and files above 25 MB are refused deliberately to protect the cloud container. The UCI files are under 200 KB. |
| Port already in use locally | `streamlit run app.py --server.port 8502` |
| App sleeps, then takes ~30 s to wake | Normal on the free tier after inactivity; keep the tab open or click **Wake up**. |
| Pushed changes do not appear | Push to the branch the app was created from (`main`), then refresh. Dependency changes need **Manage app → Reboot**. |

---

## 13. Limitations

* The dataset is observational and covers two Portuguese secondary schools; results describe this sample and are not causal.
* Grades are on a 0-20 scale, so percentages are computed against 20 per period and 60 for the combined basis.
* Ethnicity analysis requires an additional labelled dataset and is reported separately from the UCI data.
* Streamlit Community Cloud containers are ephemeral: generated reports live in the session and in temp directories, not on persistent storage. Download anything you want to keep.

---

## 14. Credits

* Dataset: P. Cortez and A. Silva, *Using Data Mining to Predict Secondary School Student Performance*, 2008 (UCI Machine Learning Repository).
* Built with Streamlit, Plotly, Pandas, NumPy, Matplotlib, Seaborn and ReportLab.
