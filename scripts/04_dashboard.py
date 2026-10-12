import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from project_config import (
    TABLES,
    DATA_PROCESSED,
    PERSONALITY_DOMAINS,
    RIASEC,
)

import json

st.set_page_config(page_title="Recruiting Dashboard", layout="wide", initial_sidebar_state="expanded")

BLACK = "#111111"
DARK = "#333333"
MID = "#777777"
LIGHT = "#D9D9D9"
BAND = "#E6E6E6"

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1240px;}
    [data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #D9D9D9; padding: 10px 14px;}
    [data-testid="stMetricLabel"] {font-size: .75rem; letter-spacing: .06em;}
    h1 {letter-spacing: .02em;}
    .chip {display: inline-block; font-size: .68rem; letter-spacing: .08em; padding: 2px 8px; border-radius: 2px;
           text-transform: uppercase; vertical-align: middle;}
    .chip-high {background: #111111; color: #FFFFFF;}
    .chip-medium {background: #D9D9D9; color: #111111;}
    .chip-low {background: #FFFFFF; color: #111111; border: 1px solid #111111;}
    .doc-card {border: 1px solid #D9D9D9; padding: 12px 14px; margin-bottom: 10px;}
    .doc-label {font-size: .68rem; letter-spacing: .1em; color: #777777; text-transform: uppercase;}
    .doc-value {font-size: .92rem; color: #111111;}
    .section-title {font-size: .8rem; letter-spacing: .14em; color: #111111; border-bottom: 1px solid #111111;
                    padding-bottom: 3px; margin: 14px 0 8px 0; text-transform: uppercase;}
    .small {font-size: .72rem; color: #555555;}
    .rec-card {border: 1px solid #111111; padding: 14px 16px; margin-bottom: 12px; background: #FFFFFF;}
    .rec-angle {font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; color: #777777;}
    .shortlist-title {font-size: 1rem; color: #111111;}
    .app-hdr {font-size: .78rem; letter-spacing: .22em; color: #FFFFFF; background: #111111;
              padding: 8px 14px; text-transform: uppercase; margin-bottom: 6px;}
    .page-hdr {font-size: 1.05rem; letter-spacing: .12em; color: #111111; border: 1px solid #111111;
               padding: 8px 14px; margin: 4px 0 14px 0; background: #FFFFFF;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data():
    full = pd.read_csv(TABLES / "candidates_full.csv")
    indicators = pd.read_csv(TABLES / "indicators.csv")
    facets = pd.read_csv(TABLES / "personality_facets.csv")
    domains = pd.read_csv(TABLES / "personality_domains.csv")
    narr = pd.read_csv(TABLES / "narratives.csv")
    interests = pd.read_csv(TABLES / "interests_scores.csv")
    with open(DATA_PROCESSED / "job_profile.json") as fh:
        profile = json.load(fh)
    return full, indicators, facets, domains, narr, interests, profile


def gray_template():
    tmp = go.layout.Template()
    tmp.layout.font = {"family": "monospace", "color": BLACK, "size": 12}
    tmp.layout.paper_bgcolor = "white"
    tmp.layout.plot_bgcolor = "white"
    tmp.layout.colorway = [BLACK, MID, "#555555", "#999999", "#BBBBBB"]
    tmp.layout.xaxis = {"gridcolor": "#ECECEC", "linecolor": BLACK, "ticks": "outside", "showline": True}
    tmp.layout.yaxis = {"gridcolor": "#ECECEC", "linecolor": BLACK, "ticks": "outside", "showline": True}
    return tmp


TEMPLATE = gray_template()


def plotly_defaults(fig):
    fig.update_layout(template=TEMPLATE, margin=dict(l=10, r=10, t=34, b=10), height=340)
    return fig


def kpis(full):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Candidates", str(len(full)), help="Applicants evaluated")
    c2.metric("Mean fit index", f"{full['fit_index'].mean():.1f}", help="0-100 weighted composite")
    c3.metric("High-fit share", f"{100 * (full['fit_label'] == 'High').mean():.0f}%", help="Fit index >= 72")
    c4.metric("Top fit", f"{full['fit_index'].max():.1f}", help="Best candidate")
    c5.metric("Mean AC rating", f"{full['ac_overall'].mean():.1f}", help="Assessment center, 1-5")


def overview_page(full, indicators, domains, interests, profile):
    st.markdown(f"### Selection results — Project Manager (Digital Marketing)")
    st.markdown('<span class="small">Multi-phase process: document review, psychometric assessment '
                '(cognitive, personality, integrity, vocational interests), psychological and labor interviews, '
                'assessment center. Percentiles are sample-based unless noted.</span>', unsafe_allow_html=True)

    st.sidebar.markdown("### Filters")
    exp_min, exp_max = st.sidebar.slider("Years of experience", 0, 20, (0, 20))
    fit_min, fit_max = st.sidebar.slider("Fit index band", 40, 100, (40, 100))
    labels = st.sidebar.multiselect("Fit label", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
    fields = st.sidebar.multiselect("Education field", sorted(full["education_field"].unique()),
                                    default=sorted(full["education_field"].unique()))
    with_certs = st.sidebar.selectbox("Certifications", ["Any", "At least one", "None"], index=0)

    m = (full["years_experience"].between(exp_min, exp_max)
         & full["fit_index"].between(fit_min, fit_max)
         & full["fit_label"].isin(labels)
         & full["education_field"].isin(fields))
    if with_certs == "At least one":
        m &= full["n_certs"] > 0
    elif with_certs == "None":
        m &= full["n_certs"] == 0
    f = full[m]
    st.sidebar.markdown(f'<span class="small">{len(f)} / {len(full)} candidates match the filters</span>', unsafe_allow_html=True)

    if f.empty:
        st.warning("No candidates match the current filters.")
        st.stop()

    kpis(f)

    st.markdown('<div class="section-title">Fit index distribution</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_vrect(x0=72, x1=100, fillcolor=BAND, line_width=0)
    fig.add_vrect(x0=55, x1=72, fillcolor="#F5F5F5", line_width=0)
    fig.add_trace(go.Histogram(x=f["fit_index"], nbinsx=10, marker=dict(color=DARK, line=dict(color="white", width=1))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                             marker=dict(size=8, color=BAND), name="High zone (>=72)"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                             marker=dict(size=8, color="#F5F5F5", line=dict(color="#888888", width=1)), name="Medium zone (55-72)"))
    fig.update_xaxes(title="Fit index (0-100)", range=[40, 100])
    fig.update_yaxes(title="Candidates")
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.12, x=0))
    st.plotly_chart(plotly_defaults(fig), width="stretch", height=340)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="section-title">Target attainment by component</div>', unsafe_allow_html=True)
        comps = ["cognitive_fit", "personality_fit", "integrity_fit", "interests_fit", "cv_fit"]
        nlab = ["Cognitive", "Personality", "Integrity", "Interests", "CV"]
        vals = [f[c].mean() for c in comps]
        fig = go.Figure(go.Bar(x=vals, y=nlab, orientation="h",
                               marker=dict(color=[DARK] * len(vals), line=dict(color="white", width=0.5)),
                               text=[f"{v:.0f}" for v in vals], textposition="outside"))
        fig.add_vline(x=72, line=dict(color=BLACK, width=1, dash="dash"))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(title="Mean attainment (0-100)", range=[0, 105])
        st.plotly_chart(plotly_defaults(fig), width="stretch", height=300)
    with col_b:
        st.markdown('<div class="section-title">Cognitive ability vs overall fit</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_hline(y=72, line=dict(color=BLACK, width=1, dash="dash"))
        fig.add_trace(go.Scatter(x=f["cognitive_fit"], y=f["fit_index"], mode="markers",
                                 marker=dict(size=9, color=DARK,
                                             line=dict(color="white", width=1)),
                                 customdata=f["name"], hovertemplate="%{customdata}<br>cog %{x:.0f} | fit %{y:.0f}<extra></extra>"))
        fig.update_xaxes(title="Cognitive attainment (0-100)", range=[20, 100])
        fig.update_yaxes(title="Fit index (0-100)", range=[40, 100])
        st.plotly_chart(plotly_defaults(fig), width="stretch", height=300)

    st.markdown('<div class="section-title">Personality domains vs target bands</div>', unsafe_allow_html=True)
    dom_piv = domains.pivot(index="candidate_id", columns="domain", values="domain_pct")
    dom_f = dom_piv.loc[f["candidate_id"]]
    pfig = go.Figure()
    for i, d in enumerate(PERSONALITY_DOMAINS):
        lo, hi = profile["targets"]["personality"][d]
        pfig.add_trace(go.Box(y=dom_f[d], name=d, boxpoints="all", jitter=0.35, pointpos=0,
                              marker=dict(size=5, color=MID), line=dict(color=BLACK),
                              fillcolor="#FFFFFF", width=0.35))
        pfig.add_hline(y=lo, line=dict(color="#BBBBBB", width=1, dash="dot"))
        pfig.add_hline(y=hi, line=dict(color="#BBBBBB", width=1, dash="dot"))
    pfig.update_yaxes(title="Sample percentile (0-100)", range=[0, 100])
    pfig.update_layout(showlegend=False)
    st.plotly_chart(plotly_defaults(pfig), width="stretch", height=360)

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown('<div class="section-title">Interest profile heatmap (RIASEC)</div>', unsafe_allow_html=True)
        idx = interests.set_index("candidate_id")
        sub = idx.loc[f["candidate_id"]]
        zfig = go.Figure(go.Heatmap(
            z=sub[RIASEC].to_numpy(), x=RIASEC,
            y=[f"{c} {n[:1]}." for c, n in zip(sub.index, f["name"])],
            colorscale=[[0, "#FFFFFF"], [0.5, "#A6A6A6"], [1, "#111111"]],
            showscale=False, zmin=1, zmax=5,
            hovertemplate="%{y} · %{x}: %{z:.1f}<extra></extra>"))
        zfig.update_layout(margin=dict(l=80, r=10, t=10, b=10))
        st.plotly_chart(plotly_defaults(zfig), width="stretch", height=380)

    with col_d:
        st.markdown('<div class="section-title">Top candidates (fit)</div>', unsafe_allow_html=True)
        top = f.sort_values("fit_index", ascending=False).head(8)
        names = [f"{r['name'].split()[0]} {r['name'].split()[1][0]}." for _, r in top.iterrows()]
        fig = go.Figure(go.Bar(x=top["fit_index"][::-1], y=names[::-1], orientation="h",
                               marker=dict(color=[DARK] * len(top)), text=top["fit_index"][::-1].round(0).astype(int),
                               textposition="outside"))
        fig.update_layout(margin=dict(l=80, r=30, t=10, b=10))
        fig.update_xaxes(title="Fit index", range=[0, 105])
        st.plotly_chart(plotly_defaults(fig), width="stretch", height=380)

    st.markdown('<div class="section-title">Candidate table</div>', unsafe_allow_html=True)
    table = f[["candidate_id", "name", "education_field", "degree", "years_experience",
               "holland_code", "icar_pct", "fit_index", "fit_label", "ac_overall"]].sort_values("fit_index", ascending=False)
    table.columns = ["ID", "Name", "Education", "Degree", "Years", "Holland",
                     "Cog%", "Fit", "Label", "AC"]
    st.dataframe(table.style.format({"Cog%": "{:.0f}", "Fit": "{:.0f}", "AC": "{:.1f}"}),
                 hide_index=True, width="stretch")
    csv = table.to_csv(index=False).encode()
    st.download_button("Download filtered table (.csv)", csv, "recruiting_results.csv",
                       mime="text/csv", width="stretch")


def chip(label):
    cls = {"High": "chip-high", "Medium": "chip-medium", "Low": "chip-low"}.get(label, "chip-medium")
    return f'<span class="chip {cls}">{label}</span>'


def doc_card(label, value):
    return f'<div class="doc-card"><div class="doc-label">{label}</div><div class="doc-value">{value}</div></div>'


def candidate_page(full, indicators, facets, narr, interests, profile):
    st.markdown("### Candidate detail")
    ordered = full.sort_values("fit_index", ascending=False)
    options = {f"{r['candidate_id']} — {r['name'].split()[0]} {r['name'].split()[1][0]}.": r["candidate_id"]
               for _, r in ordered.iterrows()}
    sel = st.selectbox("Select participant", list(options.keys()), index=0, label_visibility="collapsed")
    cid = options[sel]
    row = full[full["candidate_id"] == cid].iloc[0]
    nrow = narr[narr["candidate_id"] == cid].iloc[0]
    ind = indicators[indicators["candidate_id"] == cid]

    col1, col2, col3 = st.columns([1.0, 1.25, 1.1])
    with col1:
        st.markdown('<div class="section-title">Documentation</div>', unsafe_allow_html=True)
        st.markdown(doc_card("Name", row["name"]), unsafe_allow_html=True)
        st.markdown(doc_card("Education", f"{row['education_field']} · {row['degree']}"), unsafe_allow_html=True)
        st.markdown(doc_card("Experience", f"{row['years_experience']:.0f} years"), unsafe_allow_html=True)
        st.markdown(doc_card("City", row["city"]), unsafe_allow_html=True)
        st.markdown(doc_card("Holland code", row["holland_code"]), unsafe_allow_html=True)
        st.markdown(doc_card("Previous roles", row["previous_roles"].replace(";", "; ")), unsafe_allow_html=True)
        certs = row["certifications"]
        st.markdown(doc_card("Certifications", certs if certs else "None"), unsafe_allow_html=True)
        st.markdown(doc_card("Assessment center", f"{row['ac_overall']:.1f} / 5.0"), unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-title">Psychometric indicators (vs profile)</div>', unsafe_allow_html=True)
        for _, r in ind.iterrows():
            sublab = r["label"]
            txt = (f'<div style="display:flex;align-items:center;justify-content:space-between;margin-top:7px;">'
                   f'<span class="small">{r["indicator"]}</span>{chip(sublab)}</div>')
            st.markdown(txt, unsafe_allow_html=True)
            st.progress(min(1.0, r["bar"] / 100.0))
            st.caption(f'score {r["value"]:.0f}  ·  target {r["band"]}' if not pd.isna(r["value"]) else "")
        st.markdown('<div class="section-title">Facets detail</div>', unsafe_allow_html=True)
        for d in PERSONALITY_DOMAINS:
            fsub = facets[(facets["candidate_id"] == cid) & (facets["domain"] == d)]
            if fsub.empty:
                continue
            with st.expander(f"{d} facets"):
                for _, fr in fsub.iterrows():
                    st.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                                f'<span class="small">{fr["facet"]}</span>{chip(fr["facet_label"])}</div>',
                                unsafe_allow_html=True)
                    st.progress(min(1.0, fr["facet_pct"] / 100.0))
                    st.caption(f'percentile {fr["facet_pct"]:.0f}')

    with col3:
        st.markdown('<div class="section-title">Qualitative evaluation</div>', unsafe_allow_html=True)
        st.markdown('<div class="doc-label">Psychological interview</div>', unsafe_allow_html=True)
        st.write(nrow["psych_interview"])
        st.markdown('<div class="doc-label" style="margin-top:10px;">Labor interview</div>', unsafe_allow_html=True)
        st.write(nrow["laboral_interview"])
        st.markdown('<div class="doc-label" style="margin-top:10px;">Assessment center</div>', unsafe_allow_html=True)
        st.write(nrow["ac_observations"])
        ac_cols = [c for c in full.columns if str(c).startswith("ac_")]
        acr = {c.replace("ac_", "").replace("_", " "): float(row[c]) for c in ac_cols}
        fig = go.Figure(go.Bar(x=list(acr.values()), y=list(acr.keys()), orientation="h",
                               marker=dict(color=[DARK] * len(acr)), text=[f"{v:.1f}" for v in acr.values()],
                               textposition="outside"))
        fig.update_xaxes(title="Rating (1-5)", range=[0, 5.6])
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(plotly_defaults(fig), width="stretch", height=300)


def shortlist_page(full, narr, profile):
    st.markdown("### Proposed shortlist")
    st.markdown('<span class="small">Three distinct alternatives for the decision maker, each recommended '
                'on different evidence. All three passed the full process.</span>', unsafe_allow_html=True)

    top = full.sort_values("fit_index", ascending=False).iloc[0]
    best_ac = full[(full["fit_index"] >= 65) & (full["candidate_id"] != top["candidate_id"])] \
        .sort_values("ac_overall", ascending=False).iloc[0]
    pool_pot = full[(full["candidate_id"] != top["candidate_id"])
                    & (full["candidate_id"] != best_ac["candidate_id"]) & (full["fit_index"] >= 55)]
    best_pot = pool_pot.sort_values(["icar_pct", "years_experience"], ascending=[False, True]).iloc[0]

    narr_map = narr.set_index("candidate_id")
    picks = [
        ("First choice & best overall fit", top),
        ("Strongest behavioral profile", best_ac),
        ("Highest growth potential", best_pot),
    ]

    cols = st.columns(3)
    for col, (angle, r) in zip(cols, picks):
        n = narr_map.loc[r["candidate_id"]]
        with col:
            st.markdown(f'<div class="rec-card">'
                        f'<div class="rec-angle">{angle}</div>'
                        f'<div class="shortlist-title">{r["name"]}</div>'
                        f'<div class="small">ID {r["candidate_id"]} · {r["city"]} · {r["education_field"]} '
                        f'({r["degree"]})</div>'
                        f'<div class="small">{r["years_experience"]:.0f} years · {r["holland_code"]} · '
                        f'{len([c for c in str(r["certifications"]).split(";") if c.strip() and c.strip() != "None"])} certifications</div>'
                        f'</div>', unsafe_allow_html=True)
            st.markdown('<div class="doc-label">Fit index</div>', unsafe_allow_html=True)
            st.progress(min(1.0, r["fit_index"] / 100.0))
            st.caption(f'{r["fit_index"]:.1f} / 100  ·  label {r["fit_label"]}')
            st.markdown('<div class="doc-label">Psychological profile</div>', unsafe_allow_html=True)
            st.write(n["psychological_profile"])
            st.markdown('<div class="doc-label">Work profile</div>', unsafe_allow_html=True)
            st.write(n["laboral_profile"])
            st.markdown('<div class="doc-label">Why recommended</div>', unsafe_allow_html=True)
            reason = shortlist_reason(angle, r, n)
            st.write(reason)

    st.markdown('<div class="section-title">Recommendation matrix</div>', unsafe_allow_html=True)
    rec_table = full[["candidate_id", "name", "fit_index", "ac_overall", "cognitive_fit",
                      "personality_fit", "integrity_fit", "interests_fit", "cv_fit"]].sort_values("fit_index", ascending=False).head(6)
    rec_table = rec_table.rename(columns={"candidate_id": "ID", "name": "Name", "fit_index": "Fit",
                                          "ac_overall": "AC", "cognitive_fit": "Cog", "personality_fit": "Pers",
                                          "integrity_fit": "Integ", "interests_fit": "Inter", "cv_fit": "CV"})
    st.dataframe(rec_table.round(1), hide_index=True, width="stretch")


def shortlist_reason(angle, r, n):
    if angle.startswith("First choice"):
        return (f"Highest combined evidence: fit index {r['fit_index']:.0f}/100, consistent assessment center "
                f"({r['ac_overall']:.1f}/5.0) and equilibrium across all five selection components. "
                "Recommended as the primary offer.")
    if angle.startswith("Strongest behavioral"):
        return (f"Top behavioral evidence in the assessment center ({r['ac_overall']:.1f}/5.0) with solid overall "
                f"fit ({r['fit_index']:.0f}/100). Recommended when execution, stakeholder handling and team "
                "integration weigh most heavily.")
    return (f"Highest cognitive ability in the viable pool (cognitive attainment {r['cognitive_fit']:.0f}/100) with "
            f"fit index {r['fit_index']:.0f}/100; best option to develop into a senior or program role within "
            "12-24 months while delivering immediately.")


PAGE_LABELS = ["Overview", "Candidate detail", "Shortlist"]


def paginate():
    if "page" not in st.session_state:
        st.session_state.page = 0
    cur = st.session_state.page
    st.markdown('<div class="app-hdr">Recruiting Dashboard · Project Manager · Meridian Digital</div>',
                unsafe_allow_html=True)
    c_prev, c1, c2, c3, c_next = st.columns([1, 2, 2, 2, 1])
    if c_prev.button("◀ Prev", key="p_prev", width="stretch"):
        st.session_state.page = (cur - 1) % 3
    for idx, (col, lab) in enumerate(zip([c1, c2, c3],
                                         ["1 · Overview", "2 · Candidate detail", "3 · Shortlist"])):
        if col.button(lab, key=f"p_{idx}", width="stretch",
                      type="primary" if idx == cur else "secondary"):
            st.session_state.page = idx
    if c_next.button("Next ▶", key="p_next", width="stretch"):
        st.session_state.page = (cur + 1) % 3
    page = st.session_state.page
    st.markdown(f'<div class="page-hdr">PAGE {page + 1} / 3 — {PAGE_LABELS[page].upper()}</div>',
                unsafe_allow_html=True)
    return page


def main():
    full, indicators, facets, domains, narr, interests, profile = load_data()
    page = paginate()
    if page == 0:
        overview_page(full, indicators, domains, interests, profile)
    elif page == 1:
        candidate_page(full, indicators, facets, narr, interests, profile)
    else:
        shortlist_page(full, narr, profile)


if __name__ == "__main__":
    main()