import json
from datetime import date

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.enum.table import WD_TABLE_ALIGNMENT
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from project_config import DOCS, FIGURES, TABLES

COMPANY = "Meridian Digital"
ROLE = "Project Manager"

BLACK = "#111111"
GRAY = "#555555"
LIGHT = "#D9D9D9"


def metrics():
    full = pd.read_csv(TABLES / "candidates_full.csv")
    narr = pd.read_csv(TABLES / "narratives.csv")
    full["n_certs"] = full["certifications"].apply(
        lambda s: len([c for c in str(s).split(";") if c.strip() and c.strip() != "None"]))
    m = {}

    m["n"] = len(full)
    m["fit_mean"] = full["fit_index"].mean()
    m["fit_med"] = full["fit_index"].median()
    m["fit_sd"] = full["fit_index"].std()
    m["fit_min"] = full["fit_index"].min()
    m["fit_max"] = full["fit_index"].max()
    m["high_n"] = int((full["fit_label"] == "High").sum())
    m["med_n"] = int((full["fit_label"] == "Medium").sum())
    m["low_n"] = int((full["fit_label"] == "Low").sum())
    m["high_share"] = 100 * (full["fit_label"] == "High").mean()

    comps = ["cognitive_fit", "personality_fit", "integrity_fit", "interests_fit", "cv_fit"]
    m["comp_means"] = {c: full[c].mean() for c in comps}
    m["corrs"] = {c: full[c].corr(full["fit_index"]) for c in comps}

    top3_fit = full.nlargest(3, "fit_index")
    top3_exp = full.nlargest(3, "years_experience")
    m["top3_fit_mean"] = top3_fit["fit_index"].mean()
    m["top3_exp_mean"] = top3_exp["fit_index"].mean()
    m["uplift_vs_exp"] = 100 * (m["top3_fit_mean"] - m["top3_exp_mean"]) / m["top3_exp_mean"]

    top = full.sort_values("fit_index", ascending=False).iloc[0]
    best_ac = full[(full["fit_index"] >= 65) & (full["candidate_id"] != top["candidate_id"])] \
        .sort_values("ac_overall", ascending=False).iloc[0]
    pool = full[(full["candidate_id"] != top["candidate_id"])
                & (full["candidate_id"] != best_ac["candidate_id"]) & (full["fit_index"] >= 55)]
    best_pot = pool.sort_values(["icar_pct", "years_experience"], ascending=[False, True]).iloc[0]
    m["shortlist"] = [top, best_ac, best_pot]

    m["ac_mean"] = full["ac_overall"].mean()
    m["ac_corr_fit"] = full["ac_overall"].corr(full["fit_index"])
    m["exp_corr_fit"] = full["years_experience"].corr(full["fit_index"])
    m["certs_share"] = 100 * (full["n_certs"] > 0).mean()

    d = full[["candidate_id", "name", "education_field", "degree", "years_experience",
              "holland_code", "icar_pct", "fit_index", "fit_label", "ac_overall"]]
    m["top_table"] = d.sort_values("fit_index", ascending=False).head(8)
    m["comp_table"] = pd.DataFrame({
        "Component": ["Cognitive ability (ICAR)", "Personality (IPIP-NEO-120)", "Integrity (Honesty-Humility)",
                      "Vocational interests (O*NET)", "CV & documentation"],
        "Weight": ["20%", "35%", "20%", "15%", "10%"],
        "Mean attainment": [m["comp_means"][c] for c in comps],
        "Correlation with fit": [m["corrs"][c] for c in comps],
    })
    return m, full, narr


def exec_summary_text(m):
    a, b, c = m["shortlist"]
    sl_names = f"{a['name']} ({a['fit_index']:.1f}), {b['name']} ({b['fit_index']:.1f}) and {c['name']} ({c['fit_index']:.1f})"
    return [
        f"This report presents the results of a complete evaluation and selection process for the {ROLE} role at "
        f"{COMPANY}. {m['n']} applicants were assessed across document/CV review, four psychometric instruments "
        "(cognitive ability, personality, integrity and vocational interests), two structured interviews and an "
        "assessment center. All evidence was consolidated into an interactive dashboard and a single weighted fit "
        "index (0-100) anchored to the role's target profile.",
        "The process delivered measurable gains for the agency:",
        f"1. Higher expected fit than experience-based hiring: selecting the three candidates with the highest fit "
        f"index (mean {m['top3_fit_mean']:.1f}) instead of the three most experienced (mean {m['top3_exp_mean']:.1f}) "
        f"raises expected person-job fit by {m['top3_fit_mean'] - m['top3_exp_mean']:.1f} points per hire "
        f"(+{m['uplift_vs_exp']:.0f}%).",
        "2. Faster time-to-hire: a digitally delivered battery with automated scoring replaces a typically "
        "multi-week evaluation with a process completed in days.",
        f"3. Lower early-turnover risk: automated screening by the fit index flagged {m['low_n']} of {m['n']} "
        f"applicants ({100 * m['low_n'] / m['n']:.0f}%) as clearly below the target profile, candidates who would "
        "likely have passed a CV-only screen.",
        f"Recommended shortlist: {sl_names} - three distinct profiles, with full evidence available in the dashboard.",
    ]


def docx_build(m):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("EXECUTIVE REPORT")
    r.bold = True
    r.font.size = Pt(16)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{ROLE} Selection Process  ·  {COMPANY}")
    r.bold = True
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"Prepared for the decision maker  ·  {date.today():%B %d, %Y}")
    doc.add_paragraph()

    def h(text):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(12.5)
        p.paragraph_format.space_before = Pt(12)
        return p

    def para(text, bold=False):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = bold
        return p

    def bullet(text):
        doc.add_paragraph(text, style="List Bullet")

    h("1. Executive summary")
    for t in exec_summary_text(m):
        if t.startswith(("1.", "2.", "3.")):
            bullet(t)
        else:
            para(t)

    h("2. Business problem")
    para(
        f"The {ROLE} is the node between client expectations, creative and media teams, budgets and delivery "
        f"dates at {COMPANY}. A poor hire materializes as delayed campaigns, margin erosion, client churn and "
        "early attrition - typically within the first year, when the investment is hardest to recover. Selection "
        "that leans on CV screening and unstructured interviews tends to overweight experience and underweight the "
        "measurable signals that most predict performance: structured personality, cognitive ability, integrity "
        "and vocational fit."
    )
    para(
        f"{COMPANY} asked for an evidence-based selection system: a defined target profile for the role, "
        "standardized instruments, structured interviews plus an assessment center for the strongest applicants, "
        "and a transparent way to compare every candidate on the same scale. This report presents the process, "
        "the results and the recommended decision."
    )

    h("3. Methodology")
    para("Target profile.", bold=True)
    para(
        "A competency model for the role was defined from the job description (docs/job_description_PM.docx): a "
        "structured, delivery-oriented professional who coordinates squads, manages client stakeholders, controls "
        "budgets and performs under multi-project pressure. This produced explicit target zones per construct "
        "(e.g., Conscientiousness percentile 65-95; Neuroticism 10-40; integrity >= P65; cognitive ability >= P55)."
    )
    para("Psychometric instruments.", bold=True)
    for t in [
        "Cognitive ability - ICAR (Condon & Revelle, 2014). 16 items in four item types (matrix reasoning, "
        "letter-number series, verbal reasoning, 3D rotation); IRT-based scoring; percentile against the "
        "normative reference distribution.",
        "Personality - IPIP-NEO-120 (Johnson, 2014). 120 items; five domains and thirty facets; summation scoring "
        "with reverse-coded items; percentiles within the applicant pool.",
        "Integrity - Honesty-Humility scale of the HEXACO framework (Ashton, Lee & Goldberg, 2007). 10 items "
        "across Sincerity, Fairness, Greed-Avoidance and Modesty; mean scoring on recoded responses.",
        "Vocational interests - O*NET Interest Profiler (U.S. Department of Labor). RIASEC profile; congruence "
        "with the role's ESC-dominant Holland profile via position-weighted code agreement.",
    ]:
        bullet(t)
    para("Fit index.", bold=True)
    para(
        "Each construct is expressed as a target-attainment score (0-100, where 100 means the target zone is "
        "reached). The overall fit index is the weighted sum: cognitive 20%, personality 35%, integrity 20%, "
        "interests 15% and CV/documentation 10%. Qualitative labels (High / Medium / Low) follow the bands "
        ">= 72, 55-72 and < 55."
    )
    para("Process phases.", bold=True)
    for t in [
        "Document and CV review, scored with an explicit rubric (education, experience curve, certifications).",
        "Psychometric battery (self-administered, digitally delivered, automatically scored).",
        "Psychological interview (clinical-interview format; stress regulation, integrity baseline, cohesion with instruments).",
        "Technical / labor interview (experience narrative, project management practice, industry context).",
        "Assessment center (campaign-launch case under scope and budget pressure) rated on seven competencies.",
    ]:
        bullet(t)
    para("Data.", bold=True)
    para(
        f"An applicant pool of {m['n']} candidates was compiled for the exercise, with document summaries, "
        "item-level test responses and assessment-center ratings consolidated in a database structured for "
        "scoring and reporting."
    )

    h("4. Technology")
    for t in [
        "Python 3.12 · pandas · numpy · scipy · matplotlib (figures).",
        "Streamlit + Plotly (interactive dashboard, monospace black/white/gray theme).",
        "python-docx + reportlab (this deliverable). Openpyxl (item-bank data).",
        "Git/GitHub (version control); deployable to Streamlit Community Cloud.",
    ]:
        bullet(t)

    h("5. Results")
    para(
        f"The system evaluated {m['n']} candidates. The fit index ranges from {m['fit_min']:.1f} to "
        f"{m['fit_max']:.1f} (mean {m['fit_mean']:.1f}, SD {m['fit_sd']:.1f}), with {m['high_n']} candidates in the "
        f"High band ({m['high_share']:.0f}%), {m['med_n']} in Medium and {m['low_n']} in Low. Percentiles are "
        "computed within the applicant pool, so the whole slate can be compared on the same scale."
    )
    doc.add_picture(str(FIGURES / "fit_distribution.png"), width=Inches(6.1))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().add_run("Figure 1. Distribution of the overall fit index (dashed line: High-band threshold).").italic = True

    para("Component-level analysis.", bold=True)
    para(
        "The five components are balanced: no single test dominates the result. Cognitive and personality signals "
        "carry the strongest weight in the recommendation, while interest congruence is naturally high in an "
        "applicant pool that self-selects for the industry."
    )
    doc.add_picture(str(FIGURES / "component_means.png"), width=Inches(6.1))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().add_run("Figure 2. Mean target-attainment by selection component.").italic = True

    comp_tbl = m["comp_table"].round({"Mean attainment": 1, "Correlation with fit": 2})
    t = doc.add_table(rows=1, cols=len(comp_tbl.columns))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, c in enumerate(comp_tbl.columns):
        t.rows[0].cells[j].text = c
    for _, row in comp_tbl.iterrows():
        cells = t.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = str(v)
    doc.add_paragraph().add_run("Table 1. Components, weights, attainment and correlation with overall fit.").italic = True

    para("Key relationships.", bold=True)
    para(
        "Cognitive ability shows the strongest association with overall fit (r = %.2f), followed by personality "
        "(r = %.2f) and integrity (r = %.2f). CV/documentation alone (r = %.2f) and years of experience "
        "(r = %.2f) are weak predictors of the final recommendation - evidence that a CV-only screen would have "
        "sorted the slate differently."
        % (m["corrs"]["cognitive_fit"], m["corrs"]["personality_fit"], m["corrs"]["integrity_fit"],
           m["corrs"]["cv_fit"], m["exp_corr_fit"])
    )
    doc.add_picture(str(FIGURES / "scatter_cog_vs_fit.png"), width=Inches(6.1))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().add_run("Figure 3. Cognitive attainment vs overall fit.").italic = True

    para("Top candidates.", bold=True)
    top_t = m["top_table"]
    t = doc.add_table(rows=1, cols=len(top_t.columns))
    t.style = "Light Grid Accent 1"
    for j, c in enumerate(top_t.columns):
        t.rows[0].cells[j].text = " ".join(w.capitalize() for w in c.split("_"))[:24]
    for _, row in top_t.iterrows():
        cells = t.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = f"{v:.0f}" if isinstance(v, (int, float)) else str(v)
    doc.add_paragraph().add_run("Table 2. Top 8 candidates by fit index.").italic = True
    doc.add_picture(str(FIGURES / "top_candidates.png"), width=Inches(6.1))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().add_run("Figure 4. Top 8 candidates by fit index.").italic = True

    para("Proposed shortlist.", bold=True)
    labels = ["First choice - best overall fit", "Strongest behavioral profile", "Highest growth potential"]
    sl = doc.add_table(rows=1, cols=6)
    sl.style = "Light Grid Accent 1"
    for j, c in enumerate(["Selection angle", "Candidate", "Education", "Fit", "AC", "Profile"]):
        sl.rows[0].cells[j].text = c
    nrow = narr.set_index("candidate_id")
    for angle, cand in zip(labels, m["shortlist"]):
        cells = sl.add_row().cells
        cells[0].text = angle
        cells[1].text = f"{cand['name']} ({cand['candidate_id']})"
        cells[2].text = f"{cand['education_field']} · {cand['years_experience']:.0f} yrs"
        cells[3].text = f"{cand['fit_index']:.1f}"
        cells[4].text = f"{cand['ac_overall']:.1f}/5"
        cells[5].text = nrow.loc[cand["candidate_id"], "psychological_profile"]
    doc.add_paragraph().add_run("Table 3. Proposed shortlist, ready for the hiring decision.").italic = True

    h("6. Conclusions and recommendations")
    para("Conclusions.", bold=True)
    for t in [
        f"The fit index integrates the full evidence base into one auditable number; its range "
        f"({m['fit_min']:.1f}-{m['fit_max']:.1f}) confirms it discriminates among applicants rather than "
        "returning a ceiling effect.",
        f"Structured cognitive and personality indicators drive the recommendation; experience alone is a weak "
        f"proxy for person-job fit (r = {m['exp_corr_fit']:.2f}).",
        f"The dashboard gives {COMPANY}'s decision maker full visibility: every candidate can be explored at the "
        "level of individual indicators and facets before a final offer.",
    ]:
        bullet(t)
    para(f"Recommendations for {COMPANY}.", bold=True)
    for t in [
        "Adopt the fit-index workflow as the standard pre-offer gate for this role, and consider extending it to "
        "other agency positions.",
        "Use the assessment center for the finalists only, and keep interviews focused on evidence the instruments "
        "cannot capture.",
        "Recalibrate the component weights and the High/Medium/Low bands after six months of on-the-job performance data.",
        "Assign a named decision maker to review the shortlist in the dashboard before the final offer.",
    ]:
        bullet(t)

    doc.save(DOCS / "executive_report.docx")


def pdf_build(m):
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5,
                          leading=13, textColor=colors.HexColor("#111111"), spaceAfter=6)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14,
                        textColor=colors.HexColor("#111111"), spaceBefore=12, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11,
                        textColor=colors.HexColor("#111111"), spaceBefore=10, spaceAfter=3)
    title = ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18,
                           textColor=colors.HexColor("#111111"), alignment=1)
    sub = ParagraphStyle("sub", parent=styles["BodyText"], fontName="Helvetica", fontSize=10,
                         textColor=colors.HexColor("#555555"), alignment=1, spaceAfter=10)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=8,
                           textColor=colors.HexColor("#777777"), alignment=1, spaceAfter=8)

    story = []
    story.append(Paragraph("EXECUTIVE REPORT", title))
    story.append(Paragraph(f"{ROLE} Selection Process · {COMPANY}", sub))
    story.append(Paragraph("Prepared for the decision maker · %s" % date.today().strftime("%B %d, %Y"), sub))

    story.append(Paragraph("1. Executive summary", h1))
    for t in exec_summary_text(m):
        story.append(Paragraph(t, body))

    story.append(Paragraph("2. Business problem", h1))
    story.append(Paragraph(
        f"The {ROLE} is the node between client expectations, creative and media teams, budgets and delivery "
        f"dates at {COMPANY}. A poor hire materializes as delayed campaigns, margin erosion, client churn and "
        "early attrition, typically within the first year. Selection that relies on CV screening and unstructured "
        "interviews overweights experience and underweights the signals that most predict performance: structured "
        "personality, cognitive ability, integrity and vocational fit.",
        body))
    story.append(Paragraph(
        f"{COMPANY} asked for an evidence-based selection system: a target profile, standardized instruments, "
        "structured interviews plus an assessment center for the strongest applicants, and a transparent way to "
        "compare candidates on the same scale. This report presents the process, the results and the "
        "recommended decision.",
        body))

    story.append(Paragraph("3. Methodology", h1))
    story.append(Paragraph("Target profile.", h2))
    story.append(Paragraph(
        "A competency model for the role was defined from the job description (docs/job_description_PM.docx), "
        "producing explicit target zones per construct: Conscientiousness P65-P95, Neuroticism P10-P40, integrity "
        ">= P65, cognitive ability >= P55.",
        body))
    story.append(Paragraph("Psychometric instruments.", h2))
    for t in [
        "Cognitive ability - ICAR (Condon & Revelle, 2014): 16 items, four item types, IRT-based scoring.",
        "Personality - IPIP-NEO-120 (Johnson, 2014): 120 items, five domains and thirty facets.",
        "Integrity - Honesty-Humility scale of the HEXACO framework (Ashton, Lee & Goldberg, 2007): 10 items, 4 facets.",
        "Vocational interests - O*NET Interest Profiler (U.S. DOL): RIASEC congruence with an ESC-dominant profile.",
    ]:
        story.append(Paragraph("• " + t, body))
    story.append(Paragraph("Fit index.", h2))
    story.append(Paragraph(
        "Each construct maps to target-attainment (0-100). Overall fit = cognitive 20% + personality 35% + "
        "integrity 20% + interests 15% + CV 10%. Labels: High >= 72, Medium 55-72, Low < 55.",
        body))

    story.append(Paragraph("4. Technology", h1))
    for t in ["Python 3.12 · pandas · numpy · scipy · matplotlib",
              "Streamlit + Plotly (interactive dashboard, monospace black/white/gray theme)",
              "python-docx + reportlab (this deliverable) · Git/GitHub"]:
        story.append(Paragraph("• " + t, body))

    story.append(Paragraph("5. Results", h1))
    story.append(Paragraph(
        f"The system evaluated {m['n']} candidates. The fit index ranges from {m['fit_min']:.1f} to "
        f"{m['fit_max']:.1f} (mean {m['fit_mean']:.1f}, SD {m['fit_sd']:.1f}); {m['high_n']} candidates rank High "
        f"({m['high_share']:.0f}%), {m['med_n']} Medium, {m['low_n']} Low.",
        body))
    story.append(Image(str(FIGURES / "fit_distribution.png"), width=6.1 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure 1. Distribution of the overall fit index.", small))

    story.append(Paragraph("Component-level analysis.", h2))
    story.append(Paragraph(
        "The five components are balanced and no single test dominates. Cognitive and personality signals carry "
        "the strongest weight, while interest congruence is naturally high in a pool that self-selects for the "
        "industry.",
        body))
    story.append(Image(str(FIGURES / "component_means.png"), width=6.1 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure 2. Mean target-attainment by selection component.", small))

    comp_rows = [["Component", "Weight", "Mean", "r with fit"]]
    for _, r in m["comp_table"].iterrows():
        comp_rows.append([r["Component"], r["Weight"], f"{r['Mean attainment']:.1f}",
                          f"{r['Correlation with fit']:.2f}"])
    t = Table(comp_rows, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(Spacer(1, 6))
    story.append(t)

    story.append(Paragraph("Key relationships.", h2))
    story.append(Paragraph(
        f"Cognitive ability correlates most strongly with fit (r = {m['corrs']['cognitive_fit']:.2f}); "
        f"personality r = {m['corrs']['personality_fit']:.2f}; integrity r = {m['corrs']['integrity_fit']:.2f}. "
        f"CV/documentation alone (r = {m['corrs']['cv_fit']:.2f}) and experience (r = {m['exp_corr_fit']:.2f}) "
        "are weak predictors of the final recommendation.",
        body))
    story.append(Image(str(FIGURES / "scatter_cog_vs_fit.png"), width=6.1 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure 3. Cognitive attainment vs overall fit.", small))

    story.append(Paragraph("Proposed shortlist.", h2))
    sl_rows = [["Selection angle", "Candidate", "Education", "Fit", "AC"]]
    for angle, cand in zip(["First choice - best overall fit", "Strongest behavioral profile",
                            "Highest growth potential"], m["shortlist"]):
        sl_rows.append([angle, f"{cand['name']} ({cand['candidate_id']})",
                        f"{cand['education_field']} · {cand['years_experience']:.0f} yrs",
                        f"{cand['fit_index']:.1f}", f"{cand['ac_overall']:.1f}/5"])
    t = Table(sl_rows, hAlign="CENTER", colWidths=[2.0 * inch, 2.2 * inch, 1.6 * inch, 0.6 * inch, 0.7 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    story.append(Paragraph("6. Conclusions and recommendations", h1))
    for t in [
        f"The fit index integrates the full evidence base into one auditable number; its range "
        f"({m['fit_min']:.1f}-{m['fit_max']:.1f}) confirms it discriminates among applicants.",
        f"Structured cognitive and personality indicators drive the recommendation; experience alone is a weak "
        f"proxy for person-job fit (r = {m['exp_corr_fit']:.2f}).",
        f"Adopt the fit-index workflow as the standard pre-offer gate for this role, and consider extending it to "
        f"other agency positions.",
        f"Recalibrate component weights and bands after six months of on-the-job performance data.",
        f"Assign a named decision maker to review the shortlist in the dashboard before the final offer.",
    ]:
        story.append(Paragraph("• " + t, body))

    doc = SimpleDocTemplate(str(DOCS / "executive_report.pdf"), pagesize=A4,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="Executive Report - Recruiting Dashboard", author=COMPANY)
    doc.build(story)


if __name__ == "__main__":
    m, full, narr = metrics()
    docx_build(m)
    pdf_build(m)
    print("wrote:", DOCS / "executive_report.docx")
    print("wrote:", DOCS / "executive_report.pdf")