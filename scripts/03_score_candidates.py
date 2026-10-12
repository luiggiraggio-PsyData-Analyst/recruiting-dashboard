import json

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata
import matplotlib.pyplot as plt

from project_config import (
    DATA_RAW,
    DATA_PROCESSED,
    FIGURES,
    TABLES,
    ICAR_REFERENCE_MEAN,
    ICAR_REFERENCE_SD,
    PERSONALITY_DOMAINS,
    RIASEC,
    RIASEC_CODE,
    FIT_WEIGHTS,
)

PERSONALITY_W = {"Neuroticism": 2.0, "Extraversion": 1.5, "Openness": 1.0, "Agreeableness": 1.5, "Conscientiousness": 2.5}

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


def load_raw():
    cands = pd.read_csv(DATA_RAW / "candidates.csv")
    icar = pd.read_csv(DATA_RAW / "responses_icar.csv")
    ipip = pd.read_csv(DATA_RAW / "responses_ipip.csv")
    hexaco = pd.read_csv(DATA_RAW / "responses_hexaco.csv")
    onet = pd.read_csv(DATA_RAW / "responses_onet.csv")
    ac = pd.read_csv(DATA_RAW / "assessment_center_ratings.csv")
    items = pd.read_csv(DATA_RAW / "ipip_neo_120_items.csv")
    hex_items = pd.read_csv(DATA_RAW / "hexaco_honesty_humility_items.csv")
    onet_items = pd.read_csv(DATA_RAW / "onet_interest_items.csv")
    return cands, icar, ipip, hexaco, onet, ac, items, hex_items, onet_items


def pct_rank(series):
    r = rankdata(series.to_numpy(), method="average")
    return pd.Series(100 * (r - 1) / (len(r) - 1), index=series.index)


def score_icar(icar):
    raw = icar.groupby("candidate_id")["correct"].sum()
    pct = pd.Series(100 * norm.cdf((raw - ICAR_REFERENCE_MEAN) / ICAR_REFERENCE_SD), index=raw.index)
    return raw, pct


def score_ipip(ipip, items):
    merged = ipip.merge(items[["id", "sub-trait", "big-five-trait", "reverse"]], left_on="item_id", right_on="id")
    merged["reversed"] = merged["reverse"].eq("reverse")
    merged["value"] = np.where(merged["reversed"], 6 - merged["response"], merged["response"])

    domain_sums = merged.groupby(["candidate_id", "big-five-trait"])["value"].sum().reset_index()
    domain = []
    for cid in sorted(domain_sums["candidate_id"].unique()):
        for d in PERSONALITY_DOMAINS:
            scores = domain_sums.loc[domain_sums["big-five-trait"] == d].set_index("candidate_id")["value"]
            score = float(scores.loc[cid])
            domain.append({"candidate_id": cid, "domain": d, "domain_score": round(score, 1),
                           "domain_pct": round(float(pct_rank(scores).loc[cid]), 1)})
    domain = pd.DataFrame(domain)
    dom_wide = domain.pivot(index="candidate_id", columns="domain", values="domain_pct").reindex(columns=PERSONALITY_DOMAINS)

    facet_sums = merged.groupby(["candidate_id", "big-five-trait", "sub-trait"])["value"].sum().reset_index()
    facet = []
    grouped = facet_sums.groupby("sub-trait")["value"]
    pcts = {}
    for f, grp in facet_sums.groupby("sub-trait"):
        pcts[f] = pct_rank(grp.set_index("candidate_id")["value"])
    for _, r in facet_sums.iterrows():
        f = r["sub-trait"]
        facet.append({"candidate_id": r["candidate_id"], "domain": r["big-five-trait"], "facet": f,
                      "facet_score": round(float(r["value"]), 1),
                      "facet_pct": round(float(pcts[f].loc[r["candidate_id"]]), 1)})
    facet = pd.DataFrame(facet)
    return dom_wide, domain, facet


def score_hexaco(hexaco, hex_items):
    merged = hexaco.merge(hex_items[["item_id", "facet", "keyed"]], on="item_id")
    merged["value"] = np.where(merged["keyed"] == "negative", 6 - merged["response"], merged["response"])
    mean_all = merged.groupby("candidate_id")["value"].mean().reset_index()
    mean_all.columns = ["candidate_id", "integrity_mean"]
    mean_all["integrity_pct"] = pct_rank(mean_all["integrity_mean"]).round(1)
    hh_facet = merged.groupby(["candidate_id", "facet"])["value"].mean().reset_index()
    hh_facet.columns = ["candidate_id", "facet", "facet_mean"]
    return mean_all, hh_facet


def score_onet(onet, onet_items):
    code_name = {"R": "Realistic", "I": "Investigative", "A": "Artistic", "S": "Social", "E": "Enterprising", "C": "Conventional"}
    merged = onet.merge(onet_items[["item_id", "scale"]], on="item_id")
    merged["interest"] = merged["scale"].map(code_name)
    scale_mean = merged.groupby(["candidate_id", "interest"])["response"].mean().reset_index()
    wide = scale_mean.pivot(index="candidate_id", columns="interest", values="response").reindex(columns=RIASEC)
    return wide


JOB_HOLLAND = ["E", "S", "C"]


def congruence(row, target):
    order = np.argsort(row.to_numpy(float))[::-1][:3]
    code = "".join(RIASEC_CODE[int(i)] for i in order)
    score = 0
    for pos, ch in enumerate(code):
        if ch in JOB_HOLLAND:
            score += [3, 2, 1][pos]
    return 100.0 * score / 6.0


def holland_code(row):
    order = np.argsort(row.to_numpy(float))[::-1][:3]
    return "".join(RIASEC_CODE[int(i)] for i in order)


def score_cv(cands_df, profile):
    cv_profile = profile["cv"]
    ed_w = cv_profile["education_weights"]
    bonus = cv_profile["degree_bonus"]
    lo, hi = cv_profile["experience_ideal"]
    rows = []
    for _, r in cands_df.iterrows():
        ed = min(37, ed_w.get(r["education_field"], ed_w["Other"]) + bonus.get(r["degree"], 0))
        ed_score = ed / 37 * 100
        yrs = float(r["years_experience"])
        if yrs <= 2:
            exp_score = yrs / 2 * 100
        elif yrs <= lo:
            exp_score = 40 + (yrs / lo) * 60
        elif yrs <= hi:
            exp_score = 100.0
        elif yrs <= 16:
            exp_score = 100 - (yrs - hi) * 8
        else:
            exp_score = 68 - (yrs - 16) * 4
        exp_score = float(np.clip(exp_score, 20, 100))
        certs = [c.strip() for c in str(r["certifications"]).split(";") if c.strip() and c.strip() != "None"]
        cert_score = min(100.0, 12.5 * len(certs))
        overall = 0.45 * ed_score + 0.35 * exp_score + 0.20 * cert_score
        rows.append({"candidate_id": r["candidate_id"], "ed_score": round(ed_score, 1),
                     "exp_score": round(exp_score, 1), "cert_score": round(cert_score, 1),
                     "cv_score": round(overall, 1), "n_certs": len(certs)})
    return pd.DataFrame(rows)


def personality_fit(dom_wide, profile):
    targets = profile["targets"]["personality"]
    rows = []
    wsum = sum(PERSONALITY_W.values())
    for cid, row in dom_wide.iterrows():
        comps = {}
        acc = 0.0
        for d in PERSONALITY_DOMAINS:
            pct = float(row[d])
            lo, hi = targets[d]
            dist = 0.0 if lo <= pct <= hi else max(lo - pct, pct - hi)
            match = max(0.0, 1.0 - dist / 50.0)
            acc += PERSONALITY_W[d] * match
            comps[d] = round(100.0 * match, 1)
        comps["personality_fit"] = round(100.0 * acc / wsum, 1)
        comps["candidate_id"] = cid
        rows.append(comps)
    return pd.DataFrame(rows)


def domain_label(pct, band):
    lo, hi = band
    if lo <= pct <= hi:
        return "High"
    if (lo - 15) <= pct <= (hi + 15):
        return "Medium"
    return "Low"


def make_scored(cands_df, cog_pct, pfit, integrity, onet_wide, cv, profile):
    int_pct = integrity.set_index("candidate_id")["integrity_pct"]
    pfit_map = pfit.set_index("candidate_id")["personality_fit"]
    cv_map = cv.set_index("candidate_id")["cv_score"]
    target = profile["targets"]
    records = []
    for cid in cands_df["candidate_id"]:
        cognitive_fit = float(np.clip(cog_pct[cid] / target["cognitive"]["min_percentile"] * 100, 0, 100))
        integrity_fit = float(np.clip(int_pct[cid] / target["integrity"]["min_percentile"] * 100, 0, 100))
        personality_fit_value = float(pfit_map[cid])
        interests_fit = congruence(onet_wide.loc[cid], target["interests"])
        cv_fit = float(cv_map[cid])
        fit_index = (FIT_WEIGHTS["cognitive"] * cognitive_fit + FIT_WEIGHTS["personality"] * personality_fit_value +
                     FIT_WEIGHTS["integrity"] * integrity_fit + FIT_WEIGHTS["interests"] * interests_fit +
                     FIT_WEIGHTS["cv"] * cv_fit)
        label = "High" if fit_index >= 72 else ("Medium" if fit_index >= 55 else "Low")
        records.append({"candidate_id": cid, "icar_pct": round(float(cog_pct[cid]), 1),
                        "cognitive_fit": round(cognitive_fit, 1),
                        "personality_fit": round(personality_fit_value, 1),
                        "integrity_fit": round(integrity_fit, 1),
                        "interests_fit": round(interests_fit, 1),
                        "cv_fit": round(cv_fit, 1),
                        "fit_index": round(float(fit_index), 1), "fit_label": label})
    return pd.DataFrame(records)


def build_indicators(scored, dom_wide, integrity, profile, candidates_names):
    targets = profile["targets"]
    int_map = dict(zip(integrity["candidate_id"], integrity["integrity_pct"]))
    rows = []
    for cid in sorted(scored["candidate_id"]):
        s = scored[scored["candidate_id"] == cid].iloc[0]
        rows.append({"candidate_id": cid, "name": candidates_names[cid], "indicator": "Cognitive ability (ICAR)",
                     "category": "cognitive", "value": round(float(s["icar_pct"]), 1),
                     "band": f">= {targets['cognitive']['min_percentile']}", "bar": round(float(s["icar_pct"]), 1),
                     "label": "High" if s["icar_pct"] >= 65 else ("Medium" if s["icar_pct"] >= 45 else "Low")})
        for d in PERSONALITY_DOMAINS:
            p = float(dom_wide.loc[cid, d])
            rows.append({"candidate_id": cid, "name": candidates_names[cid], "indicator": f"Personality - {d}",
                         "category": "personality", "value": round(p, 1),
                         "band": f"{targets['personality'][d][0]} - {targets['personality'][d][1]}",
                         "bar": round(p, 1), "label": domain_label(p, targets["personality"][d])})
        hh = float(int_map[cid])
        rows.append({"candidate_id": cid, "name": candidates_names[cid], "indicator": "Integrity (Honesty-Humility)",
                     "category": "integrity", "value": round(hh, 1), "band": f">= {targets['integrity']['min_percentile']}",
                     "bar": round(hh, 1), "label": "High" if hh >= 70 else ("Medium" if hh >= 55 else "Low")})
        cong = float(s["interests_fit"])
        rows.append({"candidate_id": cid, "name": candidates_names[cid], "indicator": "Vocational interests (RIASEC congruence)",
                     "category": "interests", "value": round(cong, 1), "band": "ESC-dominant profile",
                     "bar": round(cong, 1), "label": "High" if cong >= 80 else ("Medium" if cong >= 65 else "Low")})
        cv = float(s["cv_fit"])
        rows.append({"candidate_id": cid, "name": candidates_names[cid], "indicator": "CV & documentation score",
                     "category": "cv", "value": round(cv, 1), "band": "Education / experience / certifications",
                     "bar": round(cv, 1), "label": "High" if cv >= 75 else ("Medium" if cv >= 55 else "Low")})
        fi = float(s["fit_index"])
        rows.append({"candidate_id": cid, "name": candidates_names[cid], "indicator": "Overall fit index",
                     "category": "fit", "value": round(fi, 1), "band": "Weighted composite",
                     "bar": round(fi, 1), "label": s["fit_label"]})
    return pd.DataFrame(rows)


def build_narratives(scored, cands_df, dom_wide, integrity, onet_wide, ac_df):
    int_map = dict(zip(integrity["candidate_id"], integrity["integrity_pct"]))
    ac_map = ac_df.set_index("candidate_id")
    narr = []
    for cid in sorted(scored["candidate_id"]):
        cvrow = cands_df[cands_df["candidate_id"] == cid].iloc[0]
        s = scored[scored["candidate_id"] == cid].iloc[0]
        n = float(dom_wide.loc[cid, "Neuroticism"])
        e = float(dom_wide.loc[cid, "Extraversion"])
        o = float(dom_wide.loc[cid, "Openness"])
        c = float(dom_wide.loc[cid, "Conscientiousness"])
        hh = float(int_map[cid])
        cong = float(s["interests_fit"])
        acr = ac_map.loc[cid]

        pressure = ("handles pressure with noticeable emotional stability and composure" if n <= 40 else
                    ("experiences moderate activation under pressure, manageable in structured settings" if n <= 70 else
                     "is reactive under pressure and would benefit from structured support"))
        social = ("outgoing and comfortable asserting views in groups" if e >= 55 else
                  ("sociable when needed, reserved by default" if e >= 30 else
                   "internally oriented and prefers structured one-on-one interaction"))
        integrity_txt = ("high baseline integrity and low propensity for rule-bending behavior" if hh >= 55 else
                         "moderate integrity baseline with situation-dependent rule adherence")
        psych = (f"Psychological interview: the candidate {pressure}; {social}; {integrity_txt}. "
                 f"Openness to feedback is {'high' if o >= 60 else 'moderate'}; no relevant clinical indicators emerged.")

        prev = str(cvrow["previous_roles"]).replace(";", "; ")
        certs = str(cvrow["certifications"])
        method = ("methodical and delivery-oriented in project narratives" if c >= 55 else
                  "flexible and improvisational in project narratives")
        laboral = (f"Labor interview: {cvrow['years_experience']:.0f} years of experience spanning {prev}. "
                   f"Reports {method}, with confident communication of scope, risk and budget. "
                   f"Certifications: {certs}. Interest profile congruence with the role is {cong:.0f}/100.")

        comp_vals = {c.replace("ac_", "").replace("_", " "): float(acr[c]) for c in acr.index if str(c).startswith("ac_")}
        overall_ac = sum(comp_vals.values()) / len(comp_vals)
        top = sorted(comp_vals, key=comp_vals.get, reverse=True)[:2]
        bot = sorted(comp_vals, key=comp_vals.get)[:2]
        ac_obs = (f"Assessment center (case: campaign launch under scope and budget pressure): overall "
                  f"{overall_ac:.1f}/5.0. Standouts: {', '.join(top)}. Growth areas: {', '.join(bot)}. "
                  f"Behavior in the group and individual exercises was consistent with the psychometric profile.")

        holland = holland_code(onet_wide.loc[cid])
        psych_profile = (f"{holland} interest profile; conscientiousness "
                         f"{'very high' if c >= 70 else ('high' if c >= 55 else ('moderate' if c >= 40 else 'low'))}; "
                         f"emotional regulation {'robust' if n <= 40 else 'developing'}; "
                         f"collaborative style {'high' if e >= 50 else 'moderate'}.")

        laboral_profile = (f"{cvrow['years_experience']:.0f} years of experience ({cvrow['education_field']}, "
                           f"{cvrow['degree']}); fit index {s['fit_index']}/100, aligned with the "
                           f"digital-marketing project management profile.")

        narr.append({"candidate_id": cid, "psych_interview": psych, "laboral_interview": laboral,
                     "ac_observations": ac_obs, "psychological_profile": psych_profile,
                     "laboral_profile": laboral_profile, "ac_overall": round(overall_ac, 2)})
    return pd.DataFrame(narr)


def figures(full):
    scored = full.sort_values("fit_index", ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.hist(scored["fit_index"], bins=12, color="#222222", edgecolor="white")
    ax.axvline(70, color="#000000", ls="--", lw=1)
    ax.set_xlabel("Fit index (0-100)")
    ax.set_ylabel("Candidates")
    ax.set_title("Distribution of overall fit index")
    fig.tight_layout()
    fig.savefig(FIGURES / "fit_distribution.png", dpi=150)
    plt.close(fig)

    cols = ["cognitive_fit", "personality_fit", "integrity_fit", "interests_fit", "cv_fit"]
    labels = ["Cognitive", "Personality", "Integrity", "Interests", "CV"]
    means = [scored[c].mean() for c in cols]
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.bar(labels, means, color="#333333")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Mean target-attainment")
    ax.set_title("Mean attainment by selection component")
    for x, v in enumerate(means):
        ax.text(x, v + 2, f"{v:.0f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "component_means.png", dpi=150)
    plt.close(fig)

    top = scored.head(8)
    names = [f"{r['name'].split()[0]} {r['name'].split()[1][0]}." for _, r in top.iterrows()]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.barh(names[::-1], top["fit_index"].iloc[::-1], color="#222222")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Fit index")
    ax.set_title("Top 8 candidates by fit index")
    fig.tight_layout()
    fig.savefig(FIGURES / "top_candidates.png", dpi=150)
    plt.close(fig)

    corr = scored["cognitive_fit"].corr(scored["fit_index"])
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.scatter(scored["cognitive_fit"], scored["fit_index"], s=22, color="#222222", alpha=0.8)
    ax.set_xlabel("Cognitive attainment (0-100)")
    ax.set_ylabel("Fit index (0-100)")
    ax.set_title(f"Cognitive ability vs overall fit (r = {corr:.2f})")
    fig.tight_layout()
    fig.savefig(FIGURES / "scatter_cog_vs_fit.png", dpi=150)
    plt.close(fig)


def main():
    cands, icar, ipip, hexaco, onet, ac, items, hex_items, onet_items = load_raw()
    with open(DATA_PROCESSED / "job_profile.json") as fh:
        profile = json.load(fh)

    icar_raw, icar_pct = score_icar(icar)
    dom_wide, domain, facet = score_ipip(ipip, items)
    integrity, hh_facet = score_hexaco(hexaco, hex_items)
    onet_wide = score_onet(onet, onet_items)
    cv = score_cv(cands, profile)
    pfit = personality_fit(dom_wide, profile)
    pfit.to_csv(TABLES / "personality_fit.csv", index=False)
    scored = make_scored(cands, icar_pct, pfit, integrity, onet_wide, cv, profile)
    narr = build_narratives(scored, cands, dom_wide, integrity, onet_wide, ac)
    ac_overall = narr[["candidate_id", "ac_overall"]]

    names = dict(zip(cands["candidate_id"], cands["name"]))
    indicators = build_indicators(scored, dom_wide, integrity, profile, names)

    fac = facet.copy()
    fac["facet_label"] = fac.apply(lambda r: domain_label(r["facet_pct"], profile["targets"]["personality"][r["domain"]]), axis=1)

    scored.to_csv(TABLES / "candidates_scored.csv", index=False)
    indicators.to_csv(TABLES / "indicators.csv", index=False)
    fac.to_csv(TABLES / "personality_facets.csv", index=False)
    narr.to_csv(TABLES / "narratives.csv", index=False)
    onet_wide.reset_index().to_csv(TABLES / "interests_scores.csv", index=False)
    domain.to_csv(TABLES / "personality_domains.csv", index=False)
    cv.to_csv(TABLES / "cv_scores.csv", index=False)

    full = scored.merge(cands, on="candidate_id")
    holland = onet_wide.apply(holland_code, axis=1).rename("holland_code").reset_index()
    full = full.merge(holland, on="candidate_id", how="left")
    full = full.merge(integrity[["candidate_id", "integrity_mean"]], on="candidate_id")
    full = full.merge(narr[["candidate_id", "ac_overall"]], on="candidate_id")
    full.to_csv(TABLES / "candidates_full.csv", index=False)

    figures(full)
    print("wrote candidates_scored.csv")
    print(full["fit_index"].describe().round(1).to_string())
    print("label counts:", full["fit_label"].value_counts().to_dict())


if __name__ == "__main__":
    main()