"""
Reporting layer: CSV exports, PNG chart downloads and the PDF project report.

The PDF is assembled with ReportLab Platypus and embeds the *real* Matplotlib chart
images produced from the analysed data, plus the real statistical tables.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .config import DATASET_HOMEPAGE, PALETTE

NAVY = colors.HexColor(PALETTE["navy"])
NAVY_SOFT = colors.HexColor(PALETTE["navy_soft"])
PURPLE = colors.HexColor(PALETTE["purple"])
BLUE = colors.HexColor(PALETTE["blue"])
LIGHT = colors.HexColor(PALETTE["background"])
GRID = colors.HexColor("#E6E9F2")


# --------------------------------------------------------------------------------------
# CSV helpers
# --------------------------------------------------------------------------------------
def to_csv_bytes(df: pd.DataFrame, index: bool = False) -> bytes:
    """UTF-8 CSV bytes (BOM included so Excel opens it correctly on Windows)."""
    if df is None or df.empty:
        df = pd.DataFrame({"message": ["No rows available for the current filters"]})
    return df.to_csv(index=index).encode("utf-8-sig")


# --------------------------------------------------------------------------------------
# PDF report
# --------------------------------------------------------------------------------------
def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleX", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=27, leading=32, textColor=NAVY, alignment=TA_LEFT,
                                spaceAfter=6),
        "subtitle": ParagraphStyle("SubX", parent=base["Normal"], fontName="Helvetica",
                                   fontSize=12.5, leading=18, textColor=NAVY_SOFT, spaceAfter=4),
        "h1": ParagraphStyle("H1X", parent=base["Heading1"], fontName="Helvetica-Bold",
                             fontSize=16, leading=20, textColor=NAVY, spaceBefore=16, spaceAfter=8),
        "h2": ParagraphStyle("H2X", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=12.5, leading=16, textColor=PURPLE, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("BodyX", parent=base["Normal"], fontName="Helvetica",
                               fontSize=9.8, leading=14.5, textColor=colors.HexColor("#333A56"),
                               alignment=TA_JUSTIFY, spaceAfter=7),
        "bullet": ParagraphStyle("BulletX", parent=base["Normal"], fontName="Helvetica",
                                 fontSize=9.8, leading=14.5, textColor=colors.HexColor("#333A56"),
                                 leftIndent=14, bulletIndent=4, spaceAfter=4),
        "caption": ParagraphStyle("CapX", parent=base["Normal"], fontName="Helvetica-Oblique",
                                  fontSize=8.6, leading=11, textColor=NAVY_SOFT, spaceAfter=10),
        "small": ParagraphStyle("SmallX", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8.2, leading=11, textColor=NAVY_SOFT),
    }


def _data_table(
    df: pd.DataFrame,
    styles: Dict[str, ParagraphStyle],
    max_rows: Optional[int] = None,
    col_widths: Optional[Sequence[float]] = None,
    font_size: float = 8.2,
) -> Table:
    """Render a dataframe as a clean, zebra-striped ReportLab table."""
    frame = df.copy()
    if max_rows is not None and len(frame) > max_rows:
        frame = frame.head(max_rows)
    frame.columns = [str(c) for c in frame.columns]
    data = [list(frame.columns)] + frame.astype(str).values.tolist()

    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333A56")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _kpi_strip(items: List[tuple], styles: Dict[str, ParagraphStyle]) -> Table:
    """A row of KPI boxes for the report's opening page."""
    cells = []
    for label, value in items:
        cells.append(Paragraph(
            f"<font size=15 color='{PALETTE['navy']}'><b>{value}</b></font><br/>"
            f"<font size=7.5 color='{PALETTE['navy_soft']}'>{label}</font>",
            ParagraphStyle("kpi", fontName="Helvetica", alignment=1, leading=19),
        ))
    table = Table([cells], colWidths=[17.0 * cm / len(cells)] * len(cells), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _chart_flowable(path, width_cm: float = 16.2) -> Optional[Image]:
    """Embed a PNG while preserving its aspect ratio."""
    if not path:
        return None
    image_path = Path(path)
    if not image_path.is_file():
        return None
    from PIL import Image as PILImage

    with PILImage.open(image_path) as img:
        w, h = img.size
    width = width_cm * cm
    height = width * h / w
    max_height = 12.0 * cm
    if height > max_height:
        height = max_height
        width = height * w / h
    return Image(str(image_path), width=width, height=height)


class _ReportDoc(BaseDocTemplate):
    """A4 document with a navy footer and page numbers."""

    def __init__(self, filename: str, title: str, **kwargs):
        super().__init__(filename, pagesize=A4, title=title,
                         author="Student Grades Analysis", **kwargs)
        frame = Frame(2.2 * cm, 2.0 * cm, A4[0] - 4.4 * cm, A4[1] - 3.6 * cm, id="main")
        self.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=self._decorate)])

    def _decorate(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(LIGHT)
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.6)
        canvas.line(2.2 * cm, A4[1] - 1.5 * cm, A4[0] - 2.2 * cm, A4[1] - 1.5 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(NAVY_SOFT)
        canvas.drawString(2.2 * cm, 1.25 * cm, "Student Grades Analysis - UCI Student Performance dataset")
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.25 * cm, f"Page {doc.page}")
        canvas.restoreState()


def build_pdf_report(
    output_path: str,
    subject_label: str,
    grade_basis_label: str,
    kpis: Dict[str, Any],
    dataset_facts: pd.DataFrame,
    cleaning_log: pd.DataFrame,
    gender_table: pd.DataFrame,
    percentage_band_table: pd.DataFrame,
    correlation_table: pd.DataFrame,
    charts: List[Dict[str, str]],
    subject_comparison_table: Optional[pd.DataFrame] = None,
    ethnicity_table: Optional[pd.DataFrame] = None,
    ethnicity_info: Optional[Dict[str, Any]] = None,
    best_group: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, float]] = None,
    top_students: Optional[pd.DataFrame] = None,
    dataset_source_note: str = "",
) -> str:
    """
    Build the full PDF project report and return its path.

    Sections: cover + KPIs, methodology, dataset details, cleaning log, objective 1-4
    results with charts, correlation insight, conclusions and limitations.
    """
    output_path = Path(output_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    styles = _styles()
    story: List[Any] = []
    generated = datetime.now().strftime("%d %B %Y, %H:%M")

    # ---- Cover -----------------------------------------------------------------------
    story.append(Paragraph("Student Grades Analysis", styles["title"]))
    story.append(Paragraph(
        "An interactive analysis of student academic performance<br/>"
        f"UCI Student Performance dataset &nbsp;|&nbsp; {subject_label} &nbsp;|&nbsp; "
        f"Grade basis: {grade_basis_label}",
        styles["subtitle"],
    ))
    story.append(Paragraph(f"Report generated on {generated}", styles["small"]))
    story.append(Spacer(1, 10))

    story.append(_kpi_strip([
        ("Total students", f"{kpis.get('total_students', 0):,}"),
        ("Average marks", f"{kpis.get('average_marks', float('nan')):.2f}"),
        ("Highest marks", f"{kpis.get('highest_marks', float('nan')):.0f}"),
        ("Lowest marks", f"{kpis.get('lowest_marks', float('nan')):.0f}"),
        ("Average %", f"{kpis.get('average_percentage', float('nan')):.1f}%"),
    ], styles))
    story.append(Spacer(1, 6))
    story.append(_kpi_strip([
        ("Female students", f"{kpis.get('female_students', 0):,}"),
        ("Male students", f"{kpis.get('male_students', 0):,}"),
        ("Ethnicity groups", f"{0 if ethnicity_table is None else len(ethnicity_table)}"),
        ("Performance bands", f"{len(thresholds or {})}"),
    ], styles))

    # ---- 1. Project overview ---------------------------------------------------------
    story.append(Paragraph("1. Project overview", styles["h1"]))
    story.append(Paragraph(
        "This report summarises a data-analysis study of student academic performance. "
        "The application loads the official UCI Student Performance dataset, validates and cleans it, "
        "then computes descriptive statistics and visualisations for four objectives: gender-wise "
        "statistics, gender comparison charts, percentage and performance-band classification, and an "
        "ethnicity-wise performance analysis that is enabled only when genuine ethnicity data is supplied.",
        styles["body"],
    ))
    story.append(Paragraph(
        f"Dataset source: {DATASET_HOMEPAGE}. Two course files are published: student-mat.csv "
        f"(Mathematics, 395 students) and student-por.csv (Portuguese, 649 students). Both are analysed "
        f"with the same pipeline; this report covers {subject_label}.",
        styles["body"],
    ))
    if dataset_source_note:
        story.append(Paragraph(dataset_source_note, styles["body"]))

    # ---- 2. Methodology --------------------------------------------------------------
    story.append(Paragraph("2. Methodology", styles["h1"]))
    for text in [
        "<b>Loading.</b> CSV files are read with separator detection (the UCI files are semicolon "
        "separated) and optional automatic download from the UCI archive.",
        "<b>Cleaning.</b> Empty rows and columns, duplicate records, non-numeric values and "
        "out-of-range grades are removed or corrected; residual gaps are imputed with the median "
        "(numeric) or mode (categorical). Every action is logged.",
        "<b>Statistics.</b> Gender-wise measures are computed with Pandas <i>groupby</i> aggregations "
        "(mean, min, max, count, median, standard deviation) over the selected grade basis.",
        "<b>Percentage.</b> Percentage = (marks obtained / maximum possible marks) x 100. For the final "
        "grade this is (G3 / 20) x 100; for the combined basis it is ((G1 + G2 + G3) / 60) x 100.",
        "<b>Ethnicity.</b> The UCI dataset contains no ethnicity attribute, so no field is relabelled. "
        "Where an ethnicity dataset is supplied it is merged on Student ID (or row order) and groups are "
        "ranked by average marks per student.",
    ]:
        story.append(Paragraph(text, styles["bullet"], bulletText="\u2022"))

    if thresholds:
        story.append(Paragraph("Performance bands used", styles["h2"]))
        ordered = sorted(thresholds.items(), key=lambda kv: kv[1], reverse=True)
        band_rows = []
        for index, (label, lower) in enumerate(ordered):
            upper = ordered[index - 1][1] if index > 0 else None
            band_rows.append({
                "Category": label,
                "Lower bound (%)": f"{lower:.0f}",
                "Range": f">= {lower:.0f}%" if upper is None else f"{lower:.0f}% - {upper - 0.01:.2f}%",
            })
        story.append(_data_table(pd.DataFrame(band_rows), styles, font_size=8.4))

    # ---- 3. Dataset details ----------------------------------------------------------
    story.append(Paragraph("3. Dataset details and data quality", styles["h1"]))
    story.append(_data_table(dataset_facts, styles, font_size=8.4))
    if cleaning_log is not None and not cleaning_log.empty:
        story.append(Paragraph("Cleaning and preprocessing log", styles["h2"]))
        story.append(_data_table(cleaning_log, styles, font_size=8.0))

    # ---- 4. Objective 1 --------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("4. Objective 1: gender-wise statistical analysis", styles["h1"]))
    story.append(Paragraph(
        f"Statistics below are computed from the real <i>sex</i> column of the dataset for the "
        f"selected grade basis ({grade_basis_label}).",
        styles["body"],
    ))
    if gender_table is not None and not gender_table.empty:
        story.append(_data_table(gender_table, styles, font_size=8.6))
        story.append(Spacer(1, 8))

    # ---- 5. Objective 2 charts -------------------------------------------------------
    story.append(Paragraph("5. Objective 2: gender-wise performance charts", styles["h1"]))
    for chart in charts[:6]:
        flowable = _chart_flowable(chart["path"])
        if flowable is not None:
            story.append(KeepTogether([
                flowable,
                Paragraph(f"Figure: {chart['title']}", styles["caption"]),
            ]))

    # ---- 6. Objective 3 --------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("6. Objective 3: percentage calculation and performance bands", styles["h1"]))
    story.append(Paragraph(
        "Each student receives a <i>Percentage</i> column derived from the selected grade basis and a "
        "performance category using the configurable thresholds above.",
        styles["body"],
    ))
    if percentage_band_table is not None and not percentage_band_table.empty:
        story.append(_data_table(percentage_band_table, styles, font_size=8.6))
        story.append(Spacer(1, 8))
    if top_students is not None and not top_students.empty:
        story.append(Paragraph("Top 10 students by percentage", styles["h2"]))
        story.append(_data_table(top_students, styles, max_rows=10, font_size=8.2))

    # ---- 7. Objective 4 --------------------------------------------------------------
    story.append(Paragraph("7. Objective 4: ethnicity-wise performance analysis", styles["h1"]))
    if ethnicity_table is not None and not ethnicity_table.empty:
        if ethnicity_info:
            story.append(Paragraph(
                f"Ethnicity data merged from <i>{ethnicity_info.get('filename', 'uploaded file')}</i> "
                f"using: {ethnicity_info.get('method', 'n/a')}. "
                f"Matched rows: {ethnicity_info.get('matched_rows', 0)} of "
                f"{ethnicity_info.get('matched_rows', 0) + ethnicity_info.get('unmatched_rows', 0)}. "
                f"Groups: {ethnicity_info.get('groups', 0)}.",
                styles["body"],
            ))
            if ethnicity_info.get("demo_labels"):
                story.append(Paragraph(
                    "<b>Important:</b> the ethnicity labels used in this run come from an illustrative "
                    "sample file, not from the UCI dataset. They demonstrate the pipeline and must not be "
                    "reported as real findings.",
                    styles["body"],
                ))
        story.append(_data_table(ethnicity_table, styles, font_size=8.6))
        if best_group:
            story.append(Paragraph("Best performing group", styles["h2"]))
            story.append(Paragraph(
                f"<b>{best_group['group']}</b> records the highest average mark of "
                f"<b>{best_group['average_marks']:.2f}</b> (average {best_group['average_percentage']:.2f}%) "
                f"across {best_group['groups_compared']} groups and {best_group['students']} students"
                + (f", ahead of {best_group['runner_up']} by {best_group['gap_to_second']:.2f} marks."
                   if best_group.get("runner_up") else "."),
                styles["body"],
            ))
        for chart in charts:
            if "ethnicity" in Path(chart["path"]).name:
                flowable = _chart_flowable(chart["path"], width_cm=14.5)
                if flowable is not None:
                    story.append(KeepTogether([
                        flowable,
                        Paragraph(f"Figure: {chart['title']}", styles["caption"]),
                    ]))
    else:
        story.append(Paragraph(
            "The UCI Student Performance dataset does not provide an ethnicity attribute, and presenting "
            "another demographic field (such as mother's education or mother's job) as ethnicity would be "
            "incorrect. To complete this objective, upload a dataset that carries a genuine ethnicity "
            "column keyed by Student ID (for example MAT-001). The application then merges it and repeats "
            "the analysis, ranking groups by average marks per student.",
            styles["body"],
        ))

    # ---- 8. Additional analysis ------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("8. Additional analysis", styles["h1"]))
    if subject_comparison_table is not None and not subject_comparison_table.empty:
        story.append(Paragraph("Subject cohort comparison", styles["h2"]))
        story.append(_data_table(subject_comparison_table, styles, font_size=8.4))
        story.append(Spacer(1, 8))
    if correlation_table is not None and not correlation_table.empty:
        story.append(Paragraph("Strongest correlations with the final grade", styles["h2"]))
        story.append(_data_table(correlation_table, styles, font_size=8.4))
        story.append(Spacer(1, 8))
    for chart in charts:
        if any(key in Path(chart["path"]).name for key in ("07_", "08_", "03_", "04_")):
            flowable = _chart_flowable(chart["path"], width_cm=14.5)
            if flowable is not None:
                story.append(KeepTogether([
                    flowable,
                    Paragraph(f"Figure: {chart['title']}", styles["caption"]),
                ]))

    # ---- 9. Conclusions --------------------------------------------------------------
    story.append(Paragraph("9. Conclusions", styles["h1"]))
    female = gender_table[gender_table["Gender"] == "Female"] if gender_table is not None and not gender_table.empty else pd.DataFrame()
    male = gender_table[gender_table["Gender"] == "Male"] if gender_table is not None and not gender_table.empty else pd.DataFrame()
    conclusion_bits = []
    if not female.empty and not male.empty:
        f_avg = float(female["Average Marks"].iloc[0])
        m_avg = float(male["Average Marks"].iloc[0])
        leader = "female" if f_avg > m_avg else ("male" if m_avg > f_avg else "neither")
        diff = abs(f_avg - m_avg)
        if leader == "neither":
            conclusion_bits.append("Female and male students record identical average marks.")
        else:
            conclusion_bits.append(
                f"{leader.capitalize()} students record the higher average mark "
                f"({max(f_avg, m_avg):.2f} vs {min(f_avg, m_avg):.2f}), a gap of {diff:.2f} marks on "
                f"the {grade_basis_label}."
            )
    conclusion_bits.append(
        f"Across {kpis.get('total_students', 0)} students the overall average is "
        f"{kpis.get('average_marks', float('nan')):.2f} marks "
        f"({kpis.get('average_percentage', float('nan')):.1f}%), with marks spanning "
        f"{kpis.get('lowest_marks', float('nan')):.0f} to {kpis.get('highest_marks', float('nan')):.0f}."
    )
    if top_students is not None and not top_students.empty:
        conclusion_bits.append(
            "Performance bands make the spread explicit, which supports targeted interventions for "
            "students in the lower bands."
        )
    if correlation_table is not None and not correlation_table.empty:
        strongest = correlation_table.iloc[0]
        conclusion_bits.append(
            f"The strongest detected relationship with the final grade is "
            f"{strongest['Variable']} (r = {strongest['Correlation with G3']:.3f})."
        )
    for text in conclusion_bits:
        story.append(Paragraph(text, styles["bullet"], bulletText="\u2022"))

    story.append(Paragraph("Limitations and notes", styles["h2"]))
    for text in [
        "The dataset is observational and drawn from two Portuguese secondary schools; conclusions "
        "describe this sample only and are not causal.",
        "Grades are reported on a 0-20 scale, so percentages are computed against a maximum of 20 per "
        "period and 60 for the combined basis.",
        "No ethnicity attribute exists in the source dataset. Any ethnicity analysis requires an "
        "additional labelled dataset and is reported separately.",
        "Student IDs are generated row identifiers (for example MAT-001) because the original dataset "
        "does not include one.",
    ]:
        story.append(Paragraph(text, styles["bullet"], bulletText="\u2022"))

    _ReportDoc(str(output_path), title="Student Grades Analysis Report").build(story)
    return str(output_path)
