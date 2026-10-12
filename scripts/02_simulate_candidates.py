import numpy as np
import pandas as pd

from project_config import (
    DATA_RAW,
    N_CANDIDATES,
    RANDOM_SEED,
)

CITIES = [
    "Madrid", "Barcelona", "Valencia", "Sevilla", "Bogota", "Medellin",
    "Mexico City", "Buenos Aires", "Santiago", "Lima", "Quito", "Lisbon",
    "Montevideo", "Guadalajara", "San Jose", "Panama City",
]

FIRST_NAMES = [
    "Lucia", "Mateo", "Valentina", "Santiago", "Camila", "Nicolas", "Isabella",
    "Sebastian", "Daniela", "Andres", "Carolina", "Felipe", "Gabriela", "Diego",
    "Mariana", "Ricardo", "Alejandra", "Tomas", "Antonia", "Joaquin", "Fernanda",
    "Emilio", "Regina", "Pablo", "Elena", "Bruno", "Clara", "Adrian", "Natalia",
    "Ivan",
]

LAST_NAMES = [
    "Garcia", "Rodriguez", "Martinez", "Fernandez", "Lopez", "Sanchez", "Perez",
    "Gomez", "Ramirez", "Torres", "Flores", "Rivera", "Morales", "Rojas", "Castillo",
    "Vargas", "Silva", "Cruz", "Romero", "Mendoza", "Ortiz", "Herrera", "Aguilar",
    "Medina", "Castro", "Gutierrez", "Reyes", "Nunez", "Vera", "Salazar",
]

PREVIOUS_ROLES = {
    "Digital Account Manager",
    "SEO Specialist",
    "Campaign Coordinator",
    "Marketing Analyst",
    "Content Lead",
    "Paid Media Specialist",
    "Senior Account Executive",
    "Product Owner",
    "Marketing Coordinator",
    "Brand Manager",
    "E-commerce Manager",
    "Data Analyst",
    "Customer Success Manager",
    "Junior Project Manager",
}

EDUCATION_FIELDS = [
    "Marketing", "Business Administration", "Industrial Engineering", "Advertising",
    "Communications", "Economics", "Software Engineering", "Psychology", "Design", "Other",
]

DEGREES = ["Bachelor", "Bachelor", "Bachelor", "Master", "Master", "MBA", "PhD"]

CERTIFICATIONS = [
    "PMP", "PRINCE2", "Certified ScrumMaster", "SAFe Agilist", "Google Analytics",
    "Meta Certified", "HubSpot Inbound", "Lean Six Sigma",
]

AC_COMPETENCIES = [
    "Stakeholder Communication",
    "Planning & Organization",
    "Team Leadership",
    "Problem Solving",
    "Financial Awareness",
    "Client Orientation",
    "Adaptability",
]

PERSONAS = {
    "strong": {
        "prob": 0.34,
        "theta_offset": 0.65,
        "domains": {"Neuroticism": 2.45, "Extraversion": 3.40, "Openness": 3.40, "Agreeableness": 3.50, "Conscientiousness": 3.95},
        "hh": 3.95,
        "riasec": {"Realistic": 2.05, "Investigative": 3.15, "Artistic": 2.55, "Social": 3.30, "Enterprising": 3.75, "Conventional": 3.30},
    },
    "typical": {
        "prob": 0.41,
        "theta_offset": 0.15,
        "domains": {"Neuroticism": 2.90, "Extraversion": 3.20, "Openness": 3.30, "Agreeableness": 3.35, "Conscientiousness": 3.50},
        "hh": 3.65,
        "riasec": {"Realistic": 2.35, "Investigative": 2.95, "Artistic": 2.70, "Social": 3.10, "Enterprising": 3.30, "Conventional": 3.00},
    },
    "weak": {
        "prob": 0.25,
        "theta_offset": -0.55,
        "domains": {"Neuroticism": 3.35, "Extraversion": 2.95, "Openness": 3.15, "Agreeableness": 3.10, "Conscientiousness": 3.05},
        "hh": 3.30,
        "riasec": {"Realistic": 2.75, "Investigative": 2.60, "Artistic": 2.90, "Social": 2.80, "Enterprising": 2.85, "Conventional": 2.55},
    },
}

DOMAIN_MEANS = {
    "Neuroticism": 2.80,
    "Extraversion": 3.20,
    "Openness": 3.30,
    "Agreeableness": 3.35,
    "Conscientiousness": 3.55,
}
DOMAIN_SD = 0.45

RIASEC_MEANS = {
    "Realistic": 2.30,
    "Investigative": 2.90,
    "Artistic": 2.70,
    "Social": 3.10,
    "Enterprising": 3.30,
    "Conventional": 3.00,
}
RIASEC_SD = 0.50


def _rng():
    return np.random.default_rng(RANDOM_SEED)


def generate_candidates(rng):
    certs = CERTIFICATIONS
    rows = []
    cert_probs = {
        "PMP": 0.30, "PRINCE2": 0.18, "Certified ScrumMaster": 0.45,
        "SAFe Agilist": 0.15, "Google Analytics": 0.40, "Meta Certified": 0.35,
        "HubSpot Inbound": 0.30, "Lean Six Sigma": 0.20,
    }
    for i in range(N_CANDIDATES):
        cid = f"PM-{i + 1:03d}"
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        city = str(rng.choice(CITIES))
        field = str(rng.choice(EDUCATION_FIELDS))
        degree = str(rng.choice(DEGREES))
        years = float(np.clip(np.random.default_rng(RANDOM_SEED + i).normal(7.0, 4.0), 1.0, 20.0))
        persona = rng.choice(list(PERSONAS.keys()), p=[PERSONAS[k]["prob"] for k in PERSONAS])
        n_certs = int(rng.choice([0, 1, 1, 2, 2, 3, 4]))
        cand_certs = [c for c in certs if rng.random() < cert_probs[c]]
        cand_certs = cand_certs[:n_certs]
        rng.shuffle(cand_certs)
        prev0 = str(rng.choice(sorted(PREVIOUS_ROLES)))
        prev1 = str(rng.choice(sorted(PREVIOUS_ROLES - {prev0})))
        row = {
            "candidate_id": cid,
            "name": name,
            "city": city,
            "education_field": field,
            "degree": degree,
            "years_experience": round(years, 1),
            "persona": persona,
            "previous_roles": f"{prev0}; {prev1}",
            "certifications": "; ".join(sorted(cand_certs)) if cand_certs else "None",
        }
        for comp in AC_COMPETENCIES:
            row[f"ac_{comp.replace(' ', '_').replace('&', 'and')}"] = None
        rows.append(row)
    return pd.DataFrame(rows)


def generate_icar(rng, persons):
    items = pd.read_csv(DATA_RAW / "icar_items.csv")
    records = []
    for p in persons:
        theta = float(rng.normal(PERSONAS[p["persona"]]["theta_offset"], 0.85))
        p["theta_cog"] = theta
        for _, it in items.iterrows():
            p_correct = 1.0 / (1.0 + np.exp(-it["discrimination_a"] * (theta - it["difficulty_b"])))
            correct = int(rng.random() < p_correct)
            records.append({"candidate_id": p["candidate_id"], "item_id": it["item_id"], "correct": correct})
    return pd.DataFrame(records)


def generate_ipip(rng, persons):
    items = pd.read_csv(DATA_RAW / "ipip_neo_120_items.csv")
    facets = items["sub-trait"].unique()
    records = []
    for p in persons:
        means = PERSONAS[p["persona"]]["domains"]
        domain_scores = {
            d: rng.normal(means[d], DOMAIN_SD * 0.9) for d in DOMAIN_MEANS
        }
        facet_scores = {}
        for f in facets:
            dom = items.loc[items["sub-trait"] == f, "big-five-trait"].iloc[0]
            facet_scores[f] = domain_scores[dom] + rng.normal(0, 0.35)
        for _, it in items.iterrows():
            latent = facet_scores[it["sub-trait"]]
            resp = int(np.clip(round(latent + rng.normal(0, 0.45)), 1, 5))
            records.append({"candidate_id": p["candidate_id"], "item_id": it["id"], "response": resp})
    return pd.DataFrame(records)


def generate_hexaco(rng, persons):
    items = pd.read_csv(DATA_RAW / "hexaco_honesty_humility_items.csv")
    records = []
    for p in persons:
        hh = float(np.clip(rng.normal(PERSONAS[p["persona"]]["hh"], 0.5), 1.0, 5.0))
        for _, it in items.iterrows():
            resp = int(np.clip(round(hh + rng.normal(0, 0.5)), 1, 5))
            records.append({"candidate_id": p["candidate_id"], "item_id": it["item_id"], "response": resp})
        p["theta_integrity"] = hh
    return pd.DataFrame(records)


def generate_onet(rng, persons):
    items = pd.read_csv(DATA_RAW / "onet_interest_items.csv")
    code_name = {"R": "Realistic", "I": "Investigative", "A": "Artistic",
                 "S": "Social", "E": "Enterprising", "C": "Conventional"}
    scales = items["scale"].unique()
    records = []
    for p in persons:
        means = PERSONAS[p["persona"]]["riasec"]
        scale_scores = {}
        for s in scales:
            nm = code_name[s]
            scale_scores[nm] = float(np.clip(rng.normal(means[nm], RIASEC_SD * 0.9), 1.0, 5.0))
        for _, it in items.iterrows():
            latent = scale_scores[code_name[it["scale"]]]
            resp = int(np.clip(round(latent + rng.normal(0, 0.55)), 1, 5))
            records.append({"candidate_id": p["candidate_id"], "item_id": it["item_id"], "response": resp})
        p["riasec_traits"] = scale_scores
    return pd.DataFrame(records)


def generate_ac_ratings(rng, persons):
    rows = []
    for p in persons:
        base = {
            "Stakeholder Communication": np.clip(rng.normal(3.2, 0.8), 1, 5),
            "Planning & Organization": np.clip(rng.normal(3.3, 0.8), 1, 5),
            "Team Leadership": np.clip(rng.normal(3.1, 0.8), 1, 5),
            "Problem Solving": np.clip(rng.normal(3.2, 0.8), 1, 5),
            "Financial Awareness": np.clip(rng.normal(3.0, 0.75), 1, 5),
            "Client Orientation": np.clip(rng.normal(3.3, 0.8), 1, 5),
            "Adaptability": np.clip(rng.normal(3.3, 0.8), 1, 5),
        }
        row = {"candidate_id": p["candidate_id"]}
        for comp, v in base.items():
            row[f"ac_{comp.replace(' ', '_').replace('&', 'and')}"] = round(v, 2)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    rng = _rng()
    cands = generate_candidates(rng)
    persons = cands.to_dict("records")

    icar_resp = generate_icar(rng, persons)
    ipip_resp = generate_ipip(rng, persons)
    hexaco_resp = generate_hexaco(rng, persons)
    onet_resp = generate_onet(rng, persons)
    ac = generate_ac_ratings(rng, persons)

    theta_map = {p["candidate_id"]: p.get("theta_cog", None) for p in persons}
    cands["theta_cog"] = cands["candidate_id"].map(theta_map)

    cands.to_csv(DATA_RAW / "candidates.csv", index=False)
    icar_resp.to_csv(DATA_RAW / "responses_icar.csv", index=False)
    ipip_resp.to_csv(DATA_RAW / "responses_ipip.csv", index=False)
    hexaco_resp.to_csv(DATA_RAW / "responses_hexaco.csv", index=False)
    onet_resp.to_csv(DATA_RAW / "responses_onet.csv", index=False)
    ac.to_csv(DATA_RAW / "assessment_center_ratings.csv", index=False)

    print("candidates:", DATA_RAW / "candidates.csv")
    print("icar responses:", len(icar_resp))
    print("ipip responses:", len(ipip_resp))
    print("hexaco responses:", len(hexaco_resp))
    print("onet responses:", len(onet_resp))
    print("ac ratings:", len(ac))


if __name__ == "__main__":
    main()