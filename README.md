# Recruiting Dashboard — Project Manager Selection Process

An end-to-end candidate evaluation and selection dashboard for a Project Manager role in a digital marketing
agency, built entirely with free and open-source tools. It demonstrates the full pipeline of a modern,
evidence-based hiring process: document/CV review, four psychometric instruments, structured interviews,
assessment center, a weighted **fit index** and an interactive decision dashboard.

> This repository uses a hypothetical applicant dataset generated for portfolio/demonstration purposes; the
> methodology, instruments, scoring rules and target profile follow the published open-access documentation cited
> in the Methodological notes.

## What this project does

- **Job profile first**: a full job description (`docs/job_description_PM.docx`) and an explicit *target profile*
  (ideal zones per construct) anchor every decision.
- **Four psychometric instruments**, all public-domain / open-access, scored against published rules:
  - **Cognitive ability — ICAR** (16 items, 2-PL IRT, four item types).
  - **Personality — IPIP-NEO-120** (5 domains, 30 facets, reverse-coded summation).
  - **Integrity — IPIP-HEXACO Honesty-Humility** (10 items, 4 facets).
  - **Vocational interests — O\*NET Interest Profiler** (RIASEC, ESC-congruence).
- **Weighted fit index (0-100)**: cognitive 20% · personality 35% · integrity 20% · interests 15% · CV 10%,
  with High/Medium/Low labels and per-indicator attainment bars.
- **Interactive Streamlit dashboard** (3 views):
  - *Overview* — KPIs, fit distribution, component attainment, personality vs target bands, interest heatmap,
    filterable candidate table.
  - *Candidate detail* — documentation summary, psychometric indicators with progress bars and qualitative
    labels per profile, facet drill-down, interview and assessment-center narratives.
  - *Shortlist* — three distinct recommendations for the decision maker.
- **Executive report** (`docs/executive_report.docx` and `.pdf`): executive summary, business problem,
  methodology, stack, results with charts/tables/interpretations, conclusions and recommendations.

## Key findings (demonstration sample, n = 30)

| Metric | Value |
|---|---|
| Candidates evaluated | 30 |
| Fit index — mean / SD / range | 68.4 / 13.7 / 42.8–91.7 |
| High-fit share (>= 72) | 47% (14 candidates) |
| Top-3 by fit index (mean fit) | **90.2** |
| Top-3 by experience (mean fit) | 77.3 → **+16.7% higher expected fit** |
| Selection by fit vs pool average | **+31.8% average uplift** |
| Strongest predictor of fit | Cognitive ability (r = 0.72), personality (r = 0.64) |
| CV/documentation alone (r with fit) | 0.32 (weak predictor alone) |
| Screening value | 8/30 applicants (27%) flagged below profile (fit < 55) |

## Repository structure

```
recruiting-dashboard/
├── .streamlit/config.toml        minimalist black/white/gray monospace theme
├── data/
│   ├── raw/                      person-item banks (ICAR, IPIP-NEO-120, HEXACO H-H, O*NET),
│   │                             candidates, item-level responses, AC ratings
│   └── processed/                job profile target (json), derived tables
├── docs/
│   ├── job_description_PM.docx
│   ├── executive_report.docx
│   └── executive_report.pdf
├── outputs/
│   ├── figures/                  report figures (matplotlib, grayscale)
│   └── tables/                   scored candidates, indicators, facets, narratives, ...
├── scripts/
│   ├── project_config.py         paths + tuning constants
│   ├── 01_build_job_profile.py   target profile (json) + job description (docx)
│   ├── 02_simulate_candidates.py generate 30 candidate responses and CV data
│   ├── 03_score_candidates.py    instrument scoring, fit index, labels, narratives, outputs
│   ├── 04_dashboard.py           Streamlit app (3 views)
│   └── 05_executive_report.py    executive report (docx + pdf)
├── requirements.txt              dashboard-only dependencies
├── requirements-dev.txt          full pipeline dependencies
└── README.md
```

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

python scripts/01_build_job_profile.py   # target profile + job description docx
python scripts/02_simulate_candidates.py # 30 synthetic candidates (item-level responses)
python scripts/03_score_candidates.py    # scoring, fit index, labels, figures/tables
python scripts/05_executive_report.py    # docs/executive_report.docx + .pdf

streamlit run scripts/04_dashboard.py     # interactive dashboard
```

To run only the dashboard (e.g., on Streamlit Community Cloud): `pip install -r requirements.txt`.

## Stack (free / open-source)

Python 3.12 · pandas · numpy · scipy · matplotlib · Streamlit + Plotly · python-docx · reportlab ·
openpyxl · Git/GitHub.

## Methodological notes

- **ICAR** — International Cognitive Ability Resource (Condon & Revelle, 2014, *Intelligence 43*, 52–64),
  public-domain item bank. Short form: 16 items over four item types; scores expressed as percentiles of the
  published reference distribution.
- **IPIP-NEO-120** — Johnson, J. A. (2014). *Journal of Research in Personality, 51*, 78–89. Public-domain items
  (International Personality Item Pool, Goldberg et al.); facets are sums of 4 items, domains of 24, with
  reverse-coded items per the published key.
- **IPIP-HEXACO Honesty-Humility** — Ashton, M. C., Lee, K., & Goldberg, L. R. (2007). *Personality and
  Individual Differences, 42*, 1515–1526. Subscale: Sincerity, Fairness, Greed-Avoidance, Modesty.
- **O\*NET Interest Profiler** — U.S. Department of Labor, Employment & Training Administration (public domain).
  RIASEC scales; role congruence computed as position-weighted agreement with the role's ESC-dominant code.

Construct scores in the dashboard are reported as sample percentiles within the applicant pool (norm-referenced
relative ranking), which is the standard frame for selection among multiple candidates; the target bands define
what "fits" the profile at each construct.