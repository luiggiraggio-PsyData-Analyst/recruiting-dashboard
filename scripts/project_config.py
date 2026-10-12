from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_RAW = REPO / "data" / "raw"
DATA_PROCESSED = REPO / "data" / "processed"
OUTPUTS = REPO / "outputs"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"
DOCS = REPO / "docs"
SCRIPTS = REPO / "scripts"

for _d in (DATA_RAW, DATA_PROCESSED, FIGURES, TABLES, DOCS):
    _d.mkdir(parents=True, exist_ok=True)

N_CANDIDATES = 30
RANDOM_SEED = 20261012

LOW_BAND = 30
HIGH_BAND = 70

ICAR_REFERENCE_MEAN = 9.5
ICAR_REFERENCE_SD = 3.4

PERSONALITY_DOMAINS = [
    "Neuroticism",
    "Extraversion",
    "Openness",
    "Agreeableness",
    "Conscientiousness",
]

HEXACO_HH_FACETS = ["Sincerity", "Fairness", "Greed Avoidance", "Modesty"]

RIASEC = ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"]
RIASEC_CODE = ["R", "I", "A", "S", "E", "C"]

JOB_RIASEC_TARGET = {
    "Realistic": 0.15,
    "Investigative": 0.55,
    "Artistic": 0.30,
    "Social": 0.60,
    "Enterprising": 1.00,
    "Conventional": 0.80,
}

FIT_WEIGHTS = {
    "cognitive": 0.20,
    "personality": 0.35,
    "integrity": 0.20,
    "interests": 0.15,
    "cv": 0.10,
}

CV_MAX_EXP = 25.0