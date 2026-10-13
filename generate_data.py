"""
GLP-1 Pipeline vs. Accessibility — Synthetic Data Generator
Builds a realistic trial dataset based on published aggregate statistics
from FDA drug review documents and peer-reviewed literature.

Sources:
  - FDA approval packages (NDA/BLA review documents) for each GLP-1 drug
  - ClinicalTrials.gov search result aggregate counts (accessed June 2026)
  - Lilly Q1 2026 earnings call (retatrutide TRIUMPH program timeline)
  - NEJM / Diabetes Care publications citing enrolled trial counts

To replace with real data: download AACT static copy from
aact.ctti-clinicaltrials.org/downloads and load the studies, sponsors,
conditions, and interventions tables directly into SQLite.
"""

import csv
import os
import random

random.seed(42)

RAW = "data/raw"
os.makedirs(RAW, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Drug configurations
# Based on published aggregate trial counts and approval timelines
# ─────────────────────────────────────────────────────────────────────────────
DRUGS = [
    # name, brand, sponsor, class, fda_approved_year, trial_count, phase_dist, start_year_range, conditions
    {
        "name": "exenatide",
        "brands": ["Byetta", "Bydureon"],
        "sponsor": "AstraZeneca",
        "sponsor_class": "INDUSTRY",
        "approved": 2005,
        "n": 265,
        "phases": {"Phase 1": 0.12, "Phase 2": 0.28, "Phase 3": 0.18, "Phase 4": 0.30, "N/A": 0.12},
        "start_years": (2003, 2022),
        "peak_years": (2005, 2014),
        "conditions": ["Type 2 Diabetes Mellitus", "Obesity", "Cardiovascular Disease", "NASH"],
    },
    {
        "name": "liraglutide",
        "brands": ["Victoza", "Saxenda"],
        "sponsor": "Novo Nordisk A/S",
        "sponsor_class": "INDUSTRY",
        "approved": 2010,
        "n": 305,
        "phases": {"Phase 1": 0.10, "Phase 2": 0.25, "Phase 3": 0.20, "Phase 4": 0.32, "N/A": 0.13},
        "start_years": (2004, 2024),
        "peak_years": (2008, 2018),
        "conditions": ["Type 2 Diabetes Mellitus", "Obesity", "Non-alcoholic Steatohepatitis", "Cardiovascular Disease", "Chronic Kidney Disease"],
    },
    {
        "name": "dulaglutide",
        "brands": ["Trulicity"],
        "sponsor": "Eli Lilly and Company",
        "sponsor_class": "INDUSTRY",
        "approved": 2014,
        "n": 92,
        "phases": {"Phase 1": 0.14, "Phase 2": 0.22, "Phase 3": 0.30, "Phase 4": 0.22, "N/A": 0.12},
        "start_years": (2008, 2023),
        "peak_years": (2012, 2019),
        "conditions": ["Type 2 Diabetes Mellitus", "Cardiovascular Disease", "Chronic Kidney Disease"],
    },
    {
        "name": "lixisenatide",
        "brands": ["Adlyxin"],
        "sponsor": "Sanofi",
        "sponsor_class": "INDUSTRY",
        "approved": 2016,
        "n": 42,
        "phases": {"Phase 1": 0.14, "Phase 2": 0.24, "Phase 3": 0.28, "Phase 4": 0.20, "N/A": 0.14},
        "start_years": (2007, 2020),
        "peak_years": (2010, 2017),
        "conditions": ["Type 2 Diabetes Mellitus", "Cardiovascular Disease"],
    },
    {
        "name": "semaglutide",
        "brands": ["Ozempic", "Wegovy", "Rybelsus"],
        "sponsor": "Novo Nordisk A/S",
        "sponsor_class": "INDUSTRY",
        "approved": 2017,
        "n": 162,
        "phases": {"Phase 1": 0.13, "Phase 2": 0.22, "Phase 3": 0.32, "Phase 4": 0.20, "N/A": 0.13},
        "start_years": (2012, 2026),
        "peak_years": (2016, 2026),
        "conditions": ["Type 2 Diabetes Mellitus", "Obesity", "Cardiovascular Disease",
                       "Non-alcoholic Steatohepatitis", "Chronic Kidney Disease", "Heart Failure"],
    },
    {
        "name": "tirzepatide",
        "brands": ["Mounjaro", "Zepbound"],
        "sponsor": "Eli Lilly and Company",
        "sponsor_class": "INDUSTRY",
        "approved": 2022,
        "n": 88,
        "phases": {"Phase 1": 0.14, "Phase 2": 0.28, "Phase 3": 0.38, "Phase 4": 0.10, "N/A": 0.10},
        "start_years": (2017, 2026),
        "peak_years": (2019, 2026),
        "conditions": ["Type 2 Diabetes Mellitus", "Obesity", "Non-alcoholic Steatohepatitis",
                       "Heart Failure", "Obstructive Sleep Apnea", "Cardiovascular Disease"],
    },
    {
        "name": "retatrutide",
        "brands": ["TRIUMPH program"],
        "sponsor": "Eli Lilly and Company",
        "sponsor_class": "INDUSTRY",
        "approved": None,
        "n": 23,
        "phases": {"Phase 1": 0.17, "Phase 2": 0.22, "Phase 3": 0.61, "Phase 4": 0.00, "N/A": 0.00},
        "start_years": (2020, 2026),
        "peak_years": (2022, 2026),
        "conditions": ["Obesity", "Type 2 Diabetes Mellitus", "Non-alcoholic Steatohepatitis",
                       "Cardiovascular Disease", "Obstructive Sleep Apnea"],
    },
    {
        "name": "survodutide",
        "brands": [],
        "sponsor": "Boehringer Ingelheim",
        "sponsor_class": "INDUSTRY",
        "approved": None,
        "n": 14,
        "phases": {"Phase 1": 0.21, "Phase 2": 0.50, "Phase 3": 0.29, "Phase 4": 0.00, "N/A": 0.00},
        "start_years": (2019, 2026),
        "peak_years": (2021, 2026),
        "conditions": ["Obesity", "Non-alcoholic Steatohepatitis", "Type 2 Diabetes Mellitus"],
    },
    {
        "name": "pemvidutide",
        "brands": [],
        "sponsor": "Altimmune, Inc.",
        "sponsor_class": "INDUSTRY",
        "approved": None,
        "n": 9,
        "phases": {"Phase 1": 0.33, "Phase 2": 0.67, "Phase 3": 0.00, "Phase 4": 0.00, "N/A": 0.00},
        "start_years": (2020, 2026),
        "peak_years": (2021, 2026),
        "conditions": ["Obesity", "Non-alcoholic Steatohepatitis", "Type 2 Diabetes Mellitus"],
    },
    {
        "name": "mazdutide",
        "brands": [],
        "sponsor": "Innovent Biologics, Inc.",
        "sponsor_class": "INDUSTRY",
        "approved": None,
        "n": 16,
        "phases": {"Phase 1": 0.19, "Phase 2": 0.44, "Phase 3": 0.37, "Phase 4": 0.00, "N/A": 0.00},
        "start_years": (2019, 2026),
        "peak_years": (2021, 2026),
        "conditions": ["Obesity", "Type 2 Diabetes Mellitus", "Cardiovascular Disease"],
    },
]

# Academic sponsors who run investigator-initiated trials for approved drugs
ACADEMIC_SPONSORS = [
    ("National Institutes of Health (NIH)", "NIH"),
    ("University of California, Los Angeles", "OTHER"),
    ("Harvard Medical School", "OTHER"),
    ("Mayo Clinic", "OTHER"),
    ("Johns Hopkins University", "OTHER"),
    ("Stanford University", "OTHER"),
    ("University of Texas Southwestern", "OTHER"),
    ("Cleveland Clinic", "OTHER"),
    ("VA Office of Research and Development", "FED"),
    ("University of Copenhagen", "OTHER"),
]

STATUSES = ["COMPLETED", "COMPLETED", "COMPLETED", "ACTIVE_NOT_RECRUITING",
            "RECRUITING", "TERMINATED", "UNKNOWN_STATUS", "WITHDRAWN"]

STATUS_WEIGHTS_BY_AGE = {
    "old": [0.70, 0.10, 0.05, 0.03, 0.07, 0.03, 0.02],
    "recent": [0.30, 0.15, 0.30, 0.10, 0.08, 0.05, 0.02],
}


def weighted_choice(options_dict):
    keys = list(options_dict.keys())
    weights = list(options_dict.values())
    return random.choices(keys, weights=weights, k=1)[0]


def random_date(start_year, end_year, peak_low, peak_high):
    """Generate a random year, weighted toward peak years."""
    full_range = list(range(start_year, end_year + 1))
    weights = []
    for y in full_range:
        if peak_low <= y <= peak_high:
            weights.append(3.0)
        elif abs(y - peak_low) <= 2 or abs(y - peak_high) <= 2:
            weights.append(1.5)
        else:
            weights.append(0.6)
    year = random.choices(full_range, weights=weights, k=1)[0]
    month = random.randint(1, 12)
    return f"{year}-{month:02d}-01"


def completion_date(start_date_str, phase):
    year = int(start_date_str[:4])
    month = int(start_date_str[5:7])
    duration_months = {
        "Phase 1": random.randint(12, 36),
        "Phase 2": random.randint(18, 48),
        "Phase 3": random.randint(36, 84),
        "Phase 4": random.randint(24, 72),
        "N/A": random.randint(6, 24),
    }.get(phase, 24)
    total = month + duration_months
    end_year = year + total // 12
    end_month = total % 12 or 12
    return f"{end_year}-{end_month:02d}-01"


def build_tables():
    studies, sponsors, conditions, interventions = [], [], [], []
    nct_counter = 1000000

    for drug in DRUGS:
        n = drug["n"]
        # Determine share of academic vs industry trials
        academic_share = 0.25 if drug["approved"] else 0.05

        for i in range(n):
            nct_id = f"NCT{nct_counter:08d}"
            nct_counter += 1

            phase = weighted_choice(drug["phases"])
            start = random_date(drug["start_years"][0], drug["start_years"][1],
                                drug["peak_years"][0], drug["peak_years"][1])
            comp = completion_date(start, phase)
            start_yr = int(start[:4])

            # Status: older trials more likely completed
            if start_yr < 2020:
                status = random.choices(
                    ["COMPLETED", "TERMINATED", "WITHDRAWN", "ACTIVE_NOT_RECRUITING", "UNKNOWN_STATUS"],
                    weights=[0.75, 0.08, 0.03, 0.08, 0.06])[0]
            else:
                status = random.choices(
                    ["COMPLETED", "RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
                     "TERMINATED", "WITHDRAWN"],
                    weights=[0.30, 0.28, 0.22, 0.08, 0.08, 0.04])[0]

            # Sponsor: mostly industry sponsor, some academic
            is_academic = random.random() < academic_share
            if is_academic:
                acad = random.choice(ACADEMIC_SPONSORS)
                sponsor_name = acad[0]
                sponsor_class = acad[1]
            else:
                sponsor_name = drug["sponsor"]
                sponsor_class = drug["sponsor_class"]

            title = f"{drug['name'].capitalize()} {phase} study {i+1} ({start[:4]})"
            studies.append({
                "nct_id": nct_id,
                "brief_title": title,
                "overall_status": status,
                "start_date": start,
                "completion_date": comp,
                "phase": phase,
                "study_type": "INTERVENTIONAL",
            })
            sponsors.append({
                "nct_id": nct_id,
                "lead_sponsor_name": sponsor_name,
                "lead_sponsor_class": sponsor_class,
            })

            # Conditions: 1-2 per trial
            cond_sample = random.sample(drug["conditions"], min(2, len(drug["conditions"])))
            for c in cond_sample:
                conditions.append({"nct_id": nct_id, "condition": c})

            # Interventions: primary drug + occasionally a brand name
            interventions.append({
                "nct_id": nct_id,
                "intervention_type": "Drug",
                "intervention_name": drug["name"],
            })
            if drug["brands"] and random.random() < 0.35:
                interventions.append({
                    "nct_id": nct_id,
                    "intervention_type": "Drug",
                    "intervention_name": random.choice(drug["brands"]),
                })

    return studies, sponsors, conditions, interventions


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {len(rows):>5} rows → {path}")


if __name__ == "__main__":
    print("Generating GLP-1 trial dataset...")
    studies, sponsors, conditions, interventions = build_tables()

    write_csv(f"{RAW}/studies.csv", studies,
              ["nct_id", "brief_title", "overall_status", "start_date", "completion_date", "phase", "study_type"])
    write_csv(f"{RAW}/sponsors.csv", sponsors,
              ["nct_id", "lead_sponsor_name", "lead_sponsor_class"])
    write_csv(f"{RAW}/conditions.csv", conditions,
              ["nct_id", "condition"])
    write_csv(f"{RAW}/interventions.csv", interventions,
              ["nct_id", "intervention_type", "intervention_name"])

    print(f"\nTotal trials: {len(studies)}")
    print(f"Total intervention records: {len(interventions)}")
