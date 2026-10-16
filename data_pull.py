"""
GLP-1 Pipeline vs. Accessibility — Data Acquisition
Pulls real clinical trial data from the ClinicalTrials.gov v2 API.
Outputs: data/raw/studies.csv, sponsors.csv, conditions.csv, interventions.csv

Run this FIRST before build_db.py:
    python data_pull.py

Requires internet access. No external dependencies (uses stdlib urllib only).
Typical runtime: 2–4 minutes (API rate limiting + pagination).

Data source: ClinicalTrials.gov v2 API (clinicaltrials.gov/api/v2/studies)
  - Official NIH registry; includes all GLP-1 drug trials publicly registered
  - Returns real NCT IDs, sponsor names, phases, start dates
  - Accessed via ClinicalTrials.gov public API (no API key required)
"""

import urllib.request
import urllib.parse
import json
import csv
import time
import os
from datetime import date

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "raw")

GLP1_DRUGS = [
    # Approved peptides
    "semaglutide", "tirzepatide", "liraglutide", "dulaglutide",
    "exenatide", "lixisenatide",
    # Pipeline peptides
    "retatrutide", "survodutide", "pemvidutide", "mazdutide",
    # Brand names
    "Ozempic", "Wegovy", "Mounjaro", "Zepbound",
    "Victoza", "Saxenda", "Trulicity", "Byetta",
]
# Trial-program names such as "TRIUMPH" are deliberately not searched: the
# API treats them as free text, and "TRIUMPH" alone matched ~1,270 trials,
# almost none of them GLP-1 trials. "retatrutide" already finds the TRIUMPH
# trials.

FIELDS = ",".join([
    "NCTId", "BriefTitle", "OverallStatus",
    "StartDate", "PrimaryCompletionDate",
    "Phase", "StudyType",
    "LeadSponsorName", "LeadSponsorClass",
    "Condition",
    "InterventionType", "InterventionName",
])


def phase_label(phases):
    """["PHASE2", "PHASE3"] -> "Phase 2/3"; ["EARLY_PHASE1"] -> "Early Phase 1"; [] or ["NA"] -> "N/A"."""
    phases = [p for p in phases if p != "NA"]
    if not phases:
        return "N/A"
    if phases == ["EARLY_PHASE1"]:
        return "Early Phase 1"
    return "Phase " + "/".join(p.replace("PHASE", "") for p in phases)


def fetch_page(drug, page_token=None, retries=3):
    params = {
        "query.intr": drug,
        "pageSize": "200",   # CT.gov allows up to 1000; 200 is safer for timeout avoidance
        "fields": FIELDS,
    }
    if page_token:
        params["pageToken"] = page_token
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "research-pipeline/1.0"})
    # Retry transient failures, then fail loudly: a silently skipped page would
    # leave the dataset incomplete without anyone noticing.
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to fetch {drug} after {retries} attempts: {e}") from e
            time.sleep(2 ** attempt)


def extract_list(data, key):
    """Safely extract a list from CT.gov JSON that may be a list or None."""
    val = data.get(key)
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def pull_all_trials():
    seen_nct = set()
    studies_rows = []
    sponsors_rows = []
    conditions_rows = []
    interventions_rows = []

    for drug in GLP1_DRUGS:
        print(f"  Fetching: {drug}")
        page_token = None
        while True:
            data = fetch_page(drug, page_token)

            for s in data.get("studies", []):
                proto = s.get("protocolSection", {})
                id_mod = proto.get("identificationModule", {})
                status_mod = proto.get("statusModule", {})
                design_mod = proto.get("designModule", {})
                sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
                cond_mod = proto.get("conditionsModule", {})
                arms_mod = proto.get("armsInterventionsModule", {})

                nct_id = id_mod.get("nctId", "")
                if not nct_id or nct_id in seen_nct:
                    continue
                seen_nct.add(nct_id)

                # Keep every listed phase: a Phase 2/3 trial is "Phase 2/3", not "Phase 2"
                phase = phase_label(design_mod.get("phases") or [])

                start_date = (status_mod.get("startDateStruct") or {}).get("date", "")
                primary_completion_date = (status_mod.get("primaryCompletionDateStruct") or {}).get("date", "")

                studies_rows.append({
                    "nct_id": nct_id,
                    "brief_title": id_mod.get("briefTitle", ""),
                    "overall_status": status_mod.get("overallStatus", ""),
                    "start_date": start_date,
                    "primary_completion_date": primary_completion_date,
                    "phase": phase,
                    "study_type": design_mod.get("studyType", ""),
                })

                lead = sponsor_mod.get("leadSponsor", {})
                sponsors_rows.append({
                    "nct_id": nct_id,
                    "lead_sponsor_name": lead.get("name", ""),
                    "lead_sponsor_class": lead.get("class", ""),
                })

                for cond in extract_list(cond_mod, "conditions"):
                    conditions_rows.append({"nct_id": nct_id, "condition": cond})

                for iv in arms_mod.get("interventions", []):
                    interventions_rows.append({
                        "nct_id": nct_id,
                        "intervention_type": iv.get("type", ""),
                        "intervention_name": iv.get("name", ""),
                    })

            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(0.3)  # be polite to the API

        time.sleep(0.5)

    return studies_rows, sponsors_rows, conditions_rows, interventions_rows


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows)} rows → {path}")


if __name__ == "__main__":
    print("Pulling GLP-1 trial data from ClinicalTrials.gov API...")
    studies, sponsors, conditions, interventions = pull_all_trials()

    write_csv(f"{RAW}/studies.csv", studies,
              ["nct_id", "brief_title", "overall_status", "start_date", "primary_completion_date", "phase", "study_type"])
    write_csv(f"{RAW}/sponsors.csv", sponsors,
              ["nct_id", "lead_sponsor_name", "lead_sponsor_class"])
    write_csv(f"{RAW}/conditions.csv", conditions,
              ["nct_id", "condition"])
    write_csv(f"{RAW}/interventions.csv", interventions,
              ["nct_id", "intervention_type", "intervention_name"])

    with open(f"{RAW}/pull_date.txt", "w") as f:
        f.write(date.today().isoformat() + "\n")

    print(f"\nDone. {len(studies)} unique trials pulled.")
