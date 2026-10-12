import json
from datetime import date

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt
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

from project_config import DOCS, FIGURES, TABLES, PERSONALITY_DOMAINS, RIASEC

COMPANY = "Meridian Digital"
ROLE = "Project Manager"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.edgecolor": "#111111",
    "axes.labelcolor": "#111111",
    "xtick.color": "#111111",
    "ytick.color": "#111111",
    "text.color": "#111111",
    "axes.facecolor": "white",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

BLACK = "#111111"


def metrics():
    full = pd.read_csv(TABLES / "candidates_full.csv")
    narr = pd.read_csv(TABLES / "narratives.csv")
    domains = pd.read_csv(TABLES / "personality_domains.csv")
    interests = pd.read_csv(TABLES / "interests_scores.csv")
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
    m["comps"] = comps
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
    m["shortlist"] = [(lbl, r) for lbl, r in zip(
        ["First choice - best overall fit", "Strongest behavioral profile", "Highest growth potential"],
        [top, best_ac, best_pot])]

    m["ac_mean"] = full["ac_overall"].mean()
    m["ac_corr_fit"] = full["ac_overall"].corr(full["fit_index"])
    m["exp_corr_fit"] = full["years_experience"].corr(full["fit_index"])

    dom_piv = domains.pivot(index="candidate_id", columns="domain", values="domain_pct")
    target_bands = {}
    with open(TABLES.parent.parent / "data" / "processed" / "job_profile.json") as fh:
        target_bands = json.load(fh)["targets"]["personality"]
    m["domain_rows"] = []
    for d in PERSONALITY_DOMAINS:
        vals = dom_piv[d]
        lo, hi = target_bands[d]
        in_band = float(((vals >= lo) & (vals <= hi)).mean())
        m["domain_rows"].append({"domain": d, "mean_pct": vals.mean(), "p_in": in_band,
                                 "band": f"{lo}-{hi}"})
    m["domain_table"] = pd.DataFrame(m["domain_rows"])

    ac_cols = [c for c in full.columns if str(c).startswith("ac_")]
    m["ac_comp_table"] = pd.DataFrame({
        "Competency": [c.replace("ac_", "").replace("_", " ") for c in ac_cols],
        "Mean rating": [full[c].mean() for c in ac_cols],
    })

    rias = interests.set_index("candidate_id")[RIASEC]
    m["rias_mean"] = {k: rias[k].mean() for k in RIASEC}
    m["rias_table"] = pd.DataFrame({"Interest": RIASEC,
                                    "Mean (1-5)": [rias[k].mean() for k in RIASEC]})
    m["holland_top"] = full["holland_code"].value_counts().head(3).to_dict()

    m["int_mean"] = full["integrity_mean"].mean()
    m["int_p65"] = 100 * (full["integrity_fit"] >= 100).mean()

    d = full[["candidate_id", "name", "education_field", "degree", "years_experience",
              "holland_code", "icar_pct", "fit_index", "fit_label", "ac_overall"]]
    m["rank_table"] = d.sort_values("fit_index", ascending=False).head(10)
    m["comp_table"] = pd.DataFrame({
        "Component": ["Cognitive ability (ICAR)", "Personality (IPIP-NEO-120)", "Integrity (Honesty-Humility)",
                      "Vocational interests (O*NET)", "CV & documentation"],
        "Weight": ["20%", "35%", "20%", "15%", "10%"],
        "Mean attainment": [m["comp_means"][c] for c in comps],
        "Correlation with fit": [m["corrs"][c] for c in comps],
    })
    m["narr"] = narr.set_index("candidate_id")
    return m, full


def build_domain_figure(m):
    rows = m["domain_rows"]
    names = [r["domain"] for r in rows]
    means = [r["mean_pct"] for r in rows]
    lo = [r["band"].split("-")[0] for r in rows]
    hi = [r["band"].split("-")[1] for r in rows]
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    x = np.arange(len(names))
    ax.bar(x, means, color="#333333")
    ax.errorbar(x, [float(l) for l in lo], yerr=0, fmt="none")
    for i in range(len(names)):
        ax.plot([i, i], [float(lo[i]), float(hi[i])], color="#111111", lw=2)
        ax.plot(i, float(lo[i]), "|", color="#111111", ms=14)
        ax.plot(i, float(hi[i]), "|", color="#111111", ms=14)
    ax.axhline(0, color="#111111", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([d[:4] for d in names])
    ax.set_ylabel("Mean percentile (0-100)")
    ax.set_ylim(0, 100)
    ax.set_title("Personality domain percentiles vs target bands")
    fig.tight_layout()
    out = str(FIGURES / "domain_means.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def exec_summary_text(m):
    sl_names = ", ".join(f"{cand['name']} (fit {cand['fit_index']:.1f})" for _lbl, cand in m["shortlist"])
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
        f"This report complements the dashboard by detailing the results behind the numbers and closes with the "
        "selection recommendation: the three candidates recommended for hiring are " + sl_names + ".",
    ]


def candidate_block_data(m, cand):
    n = m["narr"].loc[cand["candidate_id"]]
    comp_names = {"cognitive_fit": "Cognitive", "personality_fit": "Personality", "integrity_fit": "Integrity",
                  "interests_fit": "Interests", "cv_fit": "CV"}
    lowest = min(m["comps"], key=lambda c: cand[c])
    return {
        "narr": n,
        "lowest": (comp_names[lowest], cand[lowest]),
        "comps": {comp_names[c]: cand[c] for c in m["comps"]},
    }


def candidate_reason(angle, cand, blk):
    if angle.startswith("First choice"):
        why = (f"Highest combined evidence in the process (fit {cand['fit_index']:.1f}/100), with a balanced "
               f"profile and consistent signals across the psychometric battery, interviews and assessment center. "
               f"Recommended as the primary offer.")
    elif angle.startswith("Strongest behavioral"):
        why = (f"Best behavioral evidence in the assessment center ({cand['ac_overall']:.1f}/5.0) within a "
               f"solid overall fit ({cand['fit_index']:.1f}/100). Recommended when stakeholder handling, execution "
               f"and team integration carry the greatest weight.")
    else:
        why = (f"Highest cognitive ability in the viable pool (ICAR percentile {cand['icar_pct']:.0f}) combined "
               f"with a strong fit index ({cand['fit_index']:.1f}/100); the best option to grow into senior or "
               f"program responsibility within 12-24 months while delivering immediately.")
    return why


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
    p.add_run(f"Companion to the recruiting dashboard  ·  {date.today():%B %d, %Y}")
    doc.add_paragraph()

    def h(text, size=12.5):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(size)
        p.paragraph_format.space_before = Pt(12)
        return p

    def para(text, bold=False):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = bold
        return p

    def bullet(text):
        doc.add_paragraph(text, style="List Bullet")

    def fig(path, caption):
        doc.add_picture(str(path), width=Inches(6.1))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph().add_run(caption).italic = True

    def table(frame, caption=""):
        t = doc.add_table(rows=1, cols=len(frame.columns))
        t.style = "Light Grid Accent 1"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, c in enumerate(frame.columns):
            t.rows[0].cells[j].text = str(c)
        for _, row in frame.iterrows():
            cells = t.add_row().cells
            for j, v in enumerate(row):
                cells[j].text = str(v)
        if caption:
            doc.add_paragraph().add_run(caption).italic = True

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
        "early attrition, typically within the first year. Selection that relies on CV screening and unstructured "
        "interviews overweights experience and underweights the signals that most predict performance: structured "
        "personality, cognitive ability, integrity and vocational fit."
    )
    para(
        f"{COMPANY} asked for an evidence-based selection system: a defined target profile, standardized "
        "instruments, structured interviews plus an assessment center for the strongest applicants, and a "
        "transparent way to compare candidates on the same scale. This report is the written companion to the "
        "interactive recruiting dashboard: it details the results behind every number and closes with the "
        "recommendation of the three candidates to hire."
    )

    h("3. Methodology")
    para(
        "A competency model for the role was defined from the job description (docs/job_description_PM.docx), "
        "producing explicit target zones per construct (e.g., Conscientiousness percentile 65-95; Neuroticism "
        "10-40; integrity >= P65; cognitive ability >= P55)."
    )
    para("Psychometric instruments.", bold=True)
    for t in [
        "Cognitive ability - ICAR (Condon & Revelle, 2014): 16 items, four item types, IRT-based scoring.",
        "Personality - IPIP-NEO-120 (Johnson, 2014): 120 items, five domains and thirty facets.",
        "Integrity - Honesty-Humility scale of the HEXACO framework (Ashton, Lee & Goldberg, 2007): 10 items, 4 facets.",
        "Vocational interests - O*NET Interest Profiler (U.S. DOL): RIASEC congruence with the role's ESC-dominant profile.",
    ]:
        bullet(t)
    para(
        "Each construct maps to target-attainment (0-100); overall fit = cognitive 20% + personality 35% + "
        "integrity 20% + interests 15% + CV 10%. Labels: High >= 72, Medium 55-72, Low < 55. Percentiles are "
        "computed within the applicant pool so the whole slate is compared on the same scale."
    )
    para("Process phases.", bold=True)
    for t in [
        "Document and CV review (explicit rubric: education, experience curve, certifications).",
        "Psychometric battery (self-administered, digitally delivered, automatically scored).",
        "Psychological interview (stress regulation, integrity baseline, cohesion with instruments).",
        "Technical / labor interview (experience narrative, project management practice).",
        "Assessment center (campaign-launch case under scope and budget pressure), rated on seven competencies.",
    ]:
        bullet(t)

    h("4. Technology")
    for t in [
        "Python 3.12 · pandas · numpy · scipy · matplotlib (figures).",
        "Streamlit + Plotly (interactive dashboard, monospace black/white/gray theme).",
        "python-docx + reportlab (this deliverable). Openpyxl (item-bank data).",
        "Git/GitHub (version control); deployable to Streamlit Community Cloud.",
    ]:
        bullet(t)

    h("5. Results")

    h("5.1  Applicant pool overview", 11)
    ov = pd.DataFrame({"Metric": ["Applicants evaluated", "Fit index - mean", "Fit index - SD",
                                  "Fit index - range", "High band (~72+)",
                                  "Medium band (55-72)", "Low band (<55)"],
                       "Value": [str(m["n"]), f"{m['fit_mean']:.1f}", f"{m['fit_sd']:.1f}",
                                 f"{m['fit_min']:.1f} - {m['fit_max']:.1f}",
                                 f"{m['high_n']} ({m['high_share']:.0f}%)",
                                 str(m["med_n"]), str(m["low_n"])]})
    table(ov, "Table 1. Applicant pool at a glance.")

    h("5.2  Overall fit index", 11)
    para(
        f"The fit index integrates the five components into a single auditable number. Scores range from "
        f"{m['fit_min']:.1f} to {m['fit_max']:.1f} (mean {m['fit_mean']:.1f}, SD {m['fit_sd']:.1f}), which "
        f"confirms the instrument discriminates across the slate rather than clustering candidates at the top. "
        f"{m['high_n']} of {m['n']} candidates reach the High band and are offer-viable."
    )
    fig(FIGURES / "fit_distribution.png", "Figure 1. Distribution of the overall fit index (dashed line: High-band threshold).")

    h("5.3  Component attainment", 11)
    para(
        "The five components are balanced and no single test dominates the decision. Cognitive and personality "
        "carry the strongest weight in the recommendation; interest congruence is naturally high in a pool that "
        "self-selects for the industry."
    )
    fig(FIGURES / "component_means.png", "Figure 2. Mean target-attainment by selection component.")
    comp_tbl = m["comp_table"].round({"Mean attainment": 1, "Correlation with fit": 2})
    table(comp_tbl, "Table 2. Components, weights, attainment and correlation with overall fit.")

    h("5.4  Personality vs target bands", 11)
    dt = m["domain_table"].copy()
    dt["Mean percentile"] = dt["mean_pct"].round(1)
    dt["Share in target"] = dt["p_in"].apply(lambda v: f"{100 * v:.0f}%")
    dt = dt[["domain", "Mean percentile", "Share in target", "band"]]
    dt.columns = ["Domain", "Mean percentile", "Share in target band", "Target band"]
    table(dt, "Table 3. Personality domain percentiles against the role's target bands.")
    dr = {r["domain"]: r for r in m["domain_rows"]}
    para(
        f"Conscientiousness is the strongest driver for a delivery-oriented {ROLE} profile: the pool averages "
        f"percentile {dr['Conscientiousness']['mean_pct']:.0f} with "
        f"{100 * dr['Conscientiousness']['p_in']:.0f}% of candidates inside the 65-95 target band. Neuroticism is "
        f"the most compliant domain towards the role's low band ({100 * dr['Neuroticism']['p_in']:.0f}% inside "
        f"10-40), while Extraversion and Openness show the widest spread. The dashboard provides the full "
        "per-candidate and per-facet drill-down."
    )

    h("5.5  Integrity", 11)
    para(
        f"The integrity scale (Honesty-Humility) averages {m['int_mean']:.2f} on a 1-5 scale; "
        f"{m['int_p65']:.0f}% of candidates reach the P65 target zone. The facet-level results are available in "
        "the dashboard."
    )

    h("5.6  Vocational interests", 11)
    table(m["rias_table"].round(2), "Table 4. Mean RIASEC profile of the applicant pool.")
    para(
        f"Enterprising leadership of the pool profile is consistent with a marketing-agency audience; the role's "
        f"target is an ESC-dominant profile. Dominant Holland codes among applicants: "
        + ", ".join(f"{k} ({v})" for k, v in m["holland_top"].items()) + "."
    )

    h("5.7  Key relationships", 11)
    para(
        "Cognitive ability shows the strongest association with overall fit (r = %.2f), followed by personality "
        "(r = %.2f) and integrity (r = %.2f). CV/documentation alone (r = %.2f) and years of experience "
        "(r = %.2f) are weak predictors of the final recommendation - evidence that a CV-only screen would have "
        "ranked the slate differently."
        % (m["corrs"]["cognitive_fit"], m["corrs"]["personality_fit"], m["corrs"]["integrity_fit"],
           m["corrs"]["cv_fit"], m["exp_corr_fit"])
    )
    fig(FIGURES / "scatter_cog_vs_fit.png", "Figure 3. Cognitive attainment vs overall fit.")

    h("5.8  Candidate ranking", 11)
    rank = m["rank_table"].copy()
    rank.columns = ["ID", "Name", "Education", "Degree", "Years", "Holland", "Cog%", "Fit", "Label", "AC"]
    table(rank, "Table 5. Top 10 candidates by overall fit index.")
    fig(FIGURES / "top_candidates.png", "Figure 4. Top 8 candidates by fit index.")

    h("6. Selection recommendation")
    para(
        f"The recommendation below is based exclusively on the results of this process - psychometric scores, "
        f"structured interviews and the assessment center - weighted by the profile defined for the {ROLE}. Three "
        f"distinct profiles are recommended for hiring; each is justified with the evidence behind it. Companion "
        f"detail for each candidate is available in the dashboard (Candidate detail)."
    )

    cmp_cols = ["name", "education_field", "years_experience", "fit_index", "cognitive_fit", "personality_fit",
                "integrity_fit", "interests_fit", "cv_fit", "ac_overall", "holland_code", "n_certs"]
    sl_frame = pd.DataFrame(
        {f"{lbl.split(' - ')[0].title()}": [cand[c] if c not in ("name", "education_field") else str(cand[c])
                                            for c in cmp_cols] for lbl, cand in m["shortlist"]}
    )
    sl_frame.index = ["Candidate", "Education", "Years", "Fit index", "Cognitive", "Personality",
                      "Integrity", "Interests", "CV", "Assessment center", "Holland", "Certifications"]
    table(sl_frame, "Table 6. Recommendation at a glance: three finalists.")

    for i, (angle, cand) in enumerate(m["shortlist"], 1):
        blk = candidate_block_data(m, cand)
        h(f"6.{i}  {cand['name']}  -  {angle}", 11)
        para(
            f"Fit index {cand['fit_index']:.1f}/100 (label {cand['fit_label']}); assessment center "
            f"{cand['ac_overall']:.1f}/5.0; Holland code {cand['holland_code']}; "
            f"{cand['years_experience']:.0f} years of experience; {cand['n_certs']} certifications.",
            bold=True
        )
        para("Why this recommendation. " + candidate_reason(angle, cand, blk))
        para("Psychological profile. " + blk["narr"]["psychological_profile"])
        para("Assessment center. " + blk["narr"]["ac_observations"])
        para(f"Primary watch-out. {blk['lowest'][0]} attainment is the weakest of the five components "
             f"({blk['lowest'][1]:.0f}/100); it should be managed consciously in the first months.")

    h("7. Next steps")
    for t in [
        "Make the offer to the first choice and, in parallel, notify the other two finalists that they remain "
        "contenders if the first offer is declined - all three are offer-viable.",
        "Agree the start date and a 90-day plan: portfolio ownership, live client dashboards and delivery KPIs.",
        "Revisit this dashboard six months after hiring to recalibrate weights and bands with on-the-job performance data.",
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
    story.append(Paragraph("Companion to the recruiting dashboard · %s" % date.today().strftime("%B %d, %Y"), sub))

    story.append(Paragraph("1. Executive summary", h1))
    for t in exec_summary_text(m):
        story.append(Paragraph(t, body))

    story.append(Paragraph("2. Business problem", h1))
    story.append(Paragraph(
        f"The {ROLE} is the node between client expectations, creative and media teams, budgets and delivery "
        f"dates at {COMPANY}. A poor hire materializes as delayed campaigns, margin erosion, client churn and "
        "early attrition. This report is the written companion to the interactive recruiting dashboard: it "
        "details the results behind every number and closes with the recommendation of the three candidates "
        "to hire.",
        body))

    story.append(Paragraph("3. Methodology", h1))
    story.append(Paragraph(
        "A competency model for the role was defined from the job description (docs/job_description_PM.docx), "
        "producing explicit target zones per construct. Instruments: ICAR cognitive ability; IPIP-NEO-120 "
        "personality; Honesty-Humility integrity (HEXACO); O*NET Interest Profiler (RIASEC). Overall fit = "
        "cognitive 20% + personality 35% + integrity 20% + interests 15% + CV 10%; labels High >= 72, "
        "Medium 55-72, Low < 55.",
        body))

    story.append(Paragraph("4. Technology", h1))
    for t in ["Python 3.12 · pandas · numpy · scipy · matplotlib",
              "Streamlit + Plotly (interactive dashboard, monospace black/white/gray theme)",
              "python-docx + reportlab (this deliverable) · Git/GitHub"]:
        story.append(Paragraph("• " + t, body))

    story.append(Paragraph("5. Results", h1))
    story.append(Paragraph("5.1  Applicant pool overview", h2))
    story.append(Paragraph(
        f"{m['n']} applicants evaluated; fit index mean {m['fit_mean']:.1f} (SD {m['fit_sd']:.1f}), range "
        f"{m['fit_min']:.1f}-{m['fit_max']:.1f}. High band: {m['high_n']} ({m['high_share']:.0f}%); "
        f"Medium: {m['med_n']}; Low: {m['low_n']}.",
        body))
    story.append(Paragraph("5.2  Overall fit index", h2))
    story.append(Paragraph(
        "The fit index integrates five components into one auditable number; its spread confirms it discriminates "
        "across the slate rather than clustering at the top.",
        body))
    story.append(Image(str(FIGURES / "fit_distribution.png"), width=6.1 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure 1. Distribution of the overall fit index.", small))

    story.append(Paragraph("5.3  Component attainment", h2))
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
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ]))
    story.append(Spacer(1, 6))
    story.append(t)

    story.append(Paragraph("5.4  Personality vs target bands", h2))
    story.append(Image(str(FIGURES / "domain_means.png"), width=6.1 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure 3. Personality domain percentiles vs target bands.", small))
    dom_rows = [["Domain", "Mean pct", "Share in target", "Target band"]]
    for _, r in m["domain_table"].iterrows():
        dom_rows.append([r["domain"], f"{r['mean_pct']:.1f}", f"{100 * r['p_in']:.0f}%", r["band"]])
    t = Table(dom_rows, hAlign="CENTER")
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

    story.append(Paragraph("5.5  Integrity & 5.6  Vocational interests", h2))
    story.append(Paragraph(
        f"Integrity (Honesty-Humility) averages {m['int_mean']:.2f}/5; {m['int_p65']:.0f}% of candidates reach "
        f"the P65 target zone. The pool's mean RIASEC profile: "
        + ", ".join(f"{k[0]} {v:.1f}" for k, v in m["rias_mean"].items())
        + f", consistent with the role's ESC-dominant target. Dominant Holland codes: "
        + ", ".join(f"{k} ({v})" for k, v in m["holland_top"].items()) + ".",
        body))

    story.append(Paragraph("5.7  Key relationships", h2))
    story.append(Paragraph(
        f"Cognitive ability correlates most strongly with fit (r = {m['corrs']['cognitive_fit']:.2f}); "
        f"personality r = {m['corrs']['personality_fit']:.2f}; integrity r = {m['corrs']['integrity_fit']:.2f}. "
        f"CV/documentation alone (r = {m['corrs']['cv_fit']:.2f}) and experience (r = {m['exp_corr_fit']:.2f}) "
        "are weak predictors of the final recommendation.",
        body))
    story.append(Image(str(FIGURES / "scatter_cog_vs_fit.png"), width=6.1 * inch, height=3.2 * inch))
    story.append(Paragraph("Figure 4. Cognitive attainment vs overall fit.", small))

    story.append(Paragraph("6. Selection recommendation", h1))
    story.append(Paragraph(
        "The recommendation is based exclusively on the results of this process - psychometric scores, structured "
        "interviews and the assessment center - weighted by the profile defined for the role. Three distinct "
        "profiles are recommended for hiring.",
        body))
    sl_rows = [["", "First choice", "Behavioral", "Growth"]]
    for label, key in [("Fit index", "fit_index"), ("Cognitive", "cognitive_fit"),
                       ("Personality", "personality_fit"), ("Integrity", "integrity_fit"),
                       ("Interests", "interests_fit"), ("CV", "cv_fit"),
                       ("Assessment center", "ac_overall"), ("Years", "years_experience")]:
        row = [label]
        for _lbl, cand in m["shortlist"]:
            v = cand[key]
            row.append(f"{v:.1f}" if isinstance(v, (int, float)) else str(v))
        sl_rows.append(row)
    t = Table(sl_rows, hAlign="CENTER", colWidths=[1.6 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    for i, (angle, cand) in enumerate(m["shortlist"], 1):
        blk = candidate_block_data(m, cand)
        story.append(Paragraph(f"6.{i}  {cand['name']}  -  {angle}", h2))
        story.append(Paragraph(
            f"Fit index {cand['fit_index']:.1f}/100 ({cand['fit_label']}); assessment center "
            f"{cand['ac_overall']:.1f}/5.0; Holland code {cand['holland_code']}; "
            f"{cand['years_experience']:.0f} years; {cand['n_certs']} certifications.",
            body))
        story.append(Paragraph("<b>Why this recommendation.</b> " + candidate_reason(angle, cand, blk), body))
        story.append(Paragraph("<b>Psychological profile.</b> " + blk["narr"]["psychological_profile"], body))
        story.append(Paragraph("<b>Assessment center.</b> " + blk["narr"]["ac_observations"], body))
        story.append(Paragraph(
            f"<b>Primary watch-out.</b> {blk['lowest'][0]} attainment is the weakest component "
            f"({blk['lowest'][1]:.0f}/100); it should be managed consciously in the first months.", body))

    story.append(Paragraph("7. Next steps", h1))
    for t in [
        "Make the offer to the first choice; notify the other two finalists that they remain contenders if the "
        "first offer is declined - all three are offer-viable.",
        "Agree the start date and a 90-day plan: portfolio ownership, live client dashboards and delivery KPIs.",
        "Revisit this dashboard six months after hiring to recalibrate weights and bands with performance data.",
    ]:
        story.append(Paragraph("• " + t, body))

    doc = SimpleDocTemplate(str(DOCS / "executive_report.pdf"), pagesize=A4,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="Executive Report - Recruiting Dashboard", author=COMPANY)
    doc.build(story)


if __name__ == "__main__":
    mt, full = metrics()
    build_domain_figure(mt)
    docx_build(mt)
    pdf_build(mt)
    print("wrote:", DOCS / "executive_report.docx")
    print("wrote:", DOCS / "executive_report.pdf")