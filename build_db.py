"""
GLP-1 Pipeline vs. Accessibility — Database Builder
Loads trial CSVs (from ClinicalTrials.gov) + hand-entered, cited FDA/Lilly
event tables into SQLite.
Outputs: glp1_analysis.db
"""

import sqlite3
import csv
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "glp1_analysis.db")
RAW = os.path.join(ROOT, "data", "raw")

# Last start year kept in the analysis. Trials with planned starts after this
# are dropped. 2026 itself is partial: data/raw/ was pulled on PULL_DATE,
# which data_pull.py records in data/raw/pull_date.txt.
LAST_YEAR = 2026
with open(os.path.join(RAW, "pull_date.txt")) as _f:
    PULL_DATE = _f.read().strip()

# Which GLP-1 peptide each intervention name refers to. A trial is in scope
# only if at least one of its interventions matches one of these patterns
# (generic name, brand name, development code, or a fixed combination that
# contains the peptide). The CT.gov API search also returns trials that only
# mention a GLP-1 elsewhere (diet studies in people taking semaglutide,
# exendin-4 PET imaging tracers, etc.); matching on intervention name keeps
# those out. Misspellings below were found in the registry data itself.
# Orforglipron is excluded by design: it is a small molecule, not a peptide.
DRUG_PATTERNS = {
    "semaglutide":  ["%semaglutid%", "%ozempic%", "%wegovy%", "%rybelsus%",
                     "%nn9535%", "%nn9536%", "%nn9924%", "%cagrisema%", "%icosema%"],
    "tirzepatide":  ["%tirzepatide%", "%tirzapatide%", "%trizepatide%", "%mounjaro%",
                     "%zepbound%", "%ly3298176%"],
    "liraglutide":  ["%liraglutide%", "%victoza%", "%saxenda%", "%nn2211%",
                     "%ideglira%", "%xultophy%"],
    "dulaglutide":  ["%dulaglutide%", "%trulicity%", "%ly2189265%"],
    "exenatide":    ["%exenatide%", "%byetta%", "%bydureon%", "%ac2993%"],
    "lixisenatide": ["%lixisenatide%", "%adlyxin%", "%lyxumia%", "%ave0010%",
                     "%iglarlixi%", "%soliqua%"],
    "retatrutide":  ["%retatrutide%", "%ly3437943%"],
    "survodutide":  ["%survodutide%", "%bi 456906%", "%bi456906%"],
    "pemvidutide":  ["%pemvidutide%", "%alt-801%"],
    "mazdutide":    ["%mazdutide%", "%ly3305677%", "%ibi362%"],
}


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_db():
    for path in (DB, DB + "-journal"):
        if os.path.exists(path):
            os.remove(path)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # ── Trial tables (from data_pull.py / data/raw/ CSVs) ───────────────────

    c.execute("""
        CREATE TABLE studies (
            nct_id          TEXT PRIMARY KEY,
            brief_title     TEXT,
            overall_status  TEXT,
            start_date      TEXT,
            primary_completion_date TEXT,
            phase           TEXT,
            study_type      TEXT
        )
    """)

    c.execute("""
        CREATE TABLE sponsors (
            nct_id              TEXT,
            lead_sponsor_name   TEXT,
            lead_sponsor_class  TEXT,
            FOREIGN KEY (nct_id) REFERENCES studies(nct_id)
        )
    """)

    c.execute("""
        CREATE TABLE conditions (
            nct_id    TEXT,
            condition TEXT,
            FOREIGN KEY (nct_id) REFERENCES studies(nct_id)
        )
    """)

    c.execute("""
        CREATE TABLE interventions (
            nct_id              TEXT,
            intervention_type   TEXT,
            intervention_name   TEXT,
            FOREIGN KEY (nct_id) REFERENCES studies(nct_id)
        )
    """)

    for row in load_csv(f"{RAW}/studies.csv"):
        c.execute("INSERT INTO studies VALUES (?,?,?,?,?,?,?)",
                  (row["nct_id"], row["brief_title"], row["overall_status"],
                   row["start_date"], row["primary_completion_date"], row["phase"], row["study_type"]))

    for row in load_csv(f"{RAW}/sponsors.csv"):
        c.execute("INSERT INTO sponsors VALUES (?,?,?)",
                  (row["nct_id"], row["lead_sponsor_name"], row["lead_sponsor_class"]))

    for row in load_csv(f"{RAW}/conditions.csv"):
        c.execute("INSERT INTO conditions VALUES (?,?)", (row["nct_id"], row["condition"]))

    for row in load_csv(f"{RAW}/interventions.csv"):
        c.execute("INSERT INTO interventions VALUES (?,?,?)",
                  (row["nct_id"], row["intervention_type"], row["intervention_name"]))

    print(f"  Loaded {c.execute('SELECT COUNT(*) FROM studies').fetchone()[0]} studies")
    print(f"  Loaded {c.execute('SELECT COUNT(*) FROM sponsors').fetchone()[0]} sponsor records")
    print(f"  Loaded {c.execute('SELECT COUNT(*) FROM interventions').fetchone()[0]} intervention records")

    # ════════════════════════════════════════════════════════════════════════
    # HAND-ENTERED TABLES
    # Everything below this line is typed in by hand, not pulled from an API.
    # Each row carries the source it was taken from. Nothing here is generated
    # or interpolated: if an event could not be tied to a source, it is not in
    # the table.
    # ════════════════════════════════════════════════════════════════════════

    # ── FDA Shortage Status (hand-entered from FDA declaratory orders) ──────
    # Only semaglutide and tirzepatide are included. Earlier versions also had
    # liraglutide (2022-06 → 2024-06) and dulaglutide (2022-09 → 2023-08), but
    # those dates had no source and contradict FDA's own Dec 2024 status
    # (both still listed as "in shortage"), so they were removed.
    #
    # start_precision: 'month' means FDA's order gives only the month; the
    # date is stored as the 1st of that month.

    c.execute("""
        CREATE TABLE shortage_status (
            drug_name           TEXT,
            shortage_start      TEXT,
            start_precision     TEXT,
            shortage_end        TEXT,
            wind_down_503a_end  TEXT,
            wind_down_503b_end  TEXT,
            notes               TEXT,
            source_url          TEXT
        )
    """)

    shortage_data = [
        ("semaglutide", "2022-03-01", "month", "2025-02-21", "2025-04-22", "2025-05-22",
         "First listed Mar 2022 (Wegovy) and Aug 2022 (Ozempic). FDA order of Feb 21 2025 "
         "declared the shortage resolved; enforcement discretion ran to Apr 22 2025 (503A) "
         "and May 22 2025 (503B).",
         "https://www.fda.gov/media/185526/download"),
        ("tirzepatide", "2022-12-15", "day", "2024-12-19", "2025-02-18", "2025-03-19",
         "Listed Dec 15 2022. FDA first removed it Oct 2 2024; after the Outsourcing "
         "Facilities Association sued, FDA re-evaluated and on Dec 19 2024 issued an order "
         "that revoked and replaced the Oct 2 decision. Enforcement discretion ran to "
         "Feb 18 2025 (503A) and Mar 19 2025 (503B).",
         "https://www.fda.gov/media/184606/download"),
    ]

    c.executemany("INSERT INTO shortage_status VALUES (?,?,?,?,?,?,?,?)", shortage_data)

    # ── Policy and pricing events (hand-entered, each with a source) ────────
    c.execute("""
        CREATE TABLE policy_events (
            event_date  TEXT,
            event_type  TEXT,
            description TEXT,
            source_url  TEXT
        )
    """)

    policy_events = [
        ("2024-01-04", "LILLY_ACCESS",
         "Lilly launches LillyDirect (direct-to-patient telehealth links + home delivery).",
         "https://investor.lilly.com/node/50106"),
        ("2024-08-27", "LILLY_PRICE",
         "Lilly launches Zepbound single-dose vials on LillyDirect for self-pay patients: "
         "$399/mo (2.5 mg), $549/mo (5 mg).",
         "https://www.healthcare-brew.com/stories/2024/08/30/eli-lilly-selling-discounted-single-dose-vials-glp1-drug-zepbound"),
        ("2024-10-02", "SHORTAGE_RESOLVED",
         "FDA removes tirzepatide from the shortage list (decision later revoked and replaced on Dec 19 2024).",
         "https://www.foley.com/insights/publications/2024/10/fda-removes-lillys-zepbound-mounjaro-tirzepatide-injection-drug-shortage-list/"),
        ("2024-12-19", "SHORTAGE_RESOLVED",
         "FDA order reaffirms tirzepatide shortage is resolved.",
         "https://www.fda.gov/media/184606/download"),
        ("2025-02-21", "SHORTAGE_RESOLVED",
         "FDA order declares semaglutide shortage resolved.",
         "https://www.fda.gov/media/185526/download"),
        ("2025-02-25", "LILLY_PRICE",
         "Lilly adds 7.5 mg and 10 mg Zepbound vials at $499/mo; cuts 2.5 mg to $349 and 5 mg to $499.",
         "https://investor.lilly.com/node/52091"),
        ("2025-12-01", "LILLY_PRICE",
         "Lilly cuts Zepbound vial self-pay prices to $299 (2.5 mg), $399 (5 mg), $449 (higher doses).",
         "https://www.fiercepharma.com/marketing/lilly-joins-novo-glp-1-self-pay-price-cuts-lowering-costs-single-dose-zepbound-vials"),
        ("2026-04-30", "FDA_PROPOSED_RULE",
         "FDA proposes excluding semaglutide, tirzepatide and liraglutide from the 503B bulks list.",
         "https://www.fda.gov/news-events/press-announcements/fda-proposes-exclude-semaglutide-tirzepatide-and-liraglutide-503b-bulks-list"),
    ]

    c.executemany("INSERT INTO policy_events VALUES (?,?,?,?)", policy_events)

    # ── FDA enforcement events (hand-entered, each with a source) ───────────
    # This REPLACES the earlier 91-row `warning_letters` table. Those rows were
    # constructed, not compiled: the per-letter dates, recipient types and
    # violation categories were invented to fill out batch totals, and the
    # "Sept 8 2025 press release" they cited does not exist.
    #
    # One row per documented batch of GLP-1 warning letters. Counts are what
    # the cited source reports; count_source says how firm that number is.
    # letter_date = the date printed on the letters in FDA's database.

    c.execute("""
        CREATE TABLE enforcement_events (
            letter_date     TEXT,
            announced_date  TEXT,
            letter_count    INTEGER,
            count_source    TEXT,
            recipients      TEXT,
            description     TEXT,
            source_url      TEXT
        )
    """)

    enforcement_events = [
        ("2025-09-09", "2025-09-09", 50,
         "approx.; Hims & Hers FY2025 10-K says 'approximately 50 companies'; trade press reports 40 to 55+",
         "Telehealth platforms, wellness clinics, compounders",
         "Part of HHS/FDA crackdown on misleading DTC drug ads. Letters (e.g. Hims & Hers, "
         "file 716567) cite claims that compounded semaglutide/tirzepatide is the same as "
         "approved drugs. Posted to FDA database ~Sept 16 2025.",
         "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/hims-hers-health-inc-dba-hims-716567-09092025"),
        ("2026-02-20", "2026-03-03", 30,
         "FDA press release",
         "Telehealth companies",
         "FDA's 'second group' of telehealth GLP-1 letters: sameness claims and telehealth-"
         "branded labels that obscure who compounded the drug.",
         "https://www.fda.gov/news-events/press-announcements/fda-warns-30-telehealth-companies-against-illegal-marketing-compounded-glp-1s"),
        ("2026-06-08", "2026-06-16", 25,
         "secondary source (Mondaq, Jul 9 2026); no FDA press release found",
         "Telehealth companies",
         "Further letters on false/misleading claims for compounded semaglutide and "
         "tirzepatide (e.g. Altru Telehealth, file 728274).",
         "https://www.mondaq.com/unitedstates/healthcare/1814666/fda-takes-aim-at-misleading-online-claims-for-compounded-glp-1-drugs"),
    ]

    c.executemany("INSERT INTO enforcement_events VALUES (?,?,?,?,?,?,?)", enforcement_events)

    print(f"  Loaded {c.execute('SELECT COUNT(*) FROM shortage_status').fetchone()[0]} shortage records")
    print(f"  Loaded {c.execute('SELECT COUNT(*) FROM enforcement_events').fetchone()[0]} enforcement events")

    # ── GLP-1 drug matching ──────────────────────────────────────────────────
    c.execute("CREATE TABLE drug_patterns (drug TEXT, pattern TEXT)")
    c.executemany("INSERT INTO drug_patterns VALUES (?,?)",
                  [(drug, pat) for drug, pats in DRUG_PATTERNS.items() for pat in pats])

    # One row per (trial, GLP-1 drug) pair. A head-to-head trial such as
    # semaglutide vs tirzepatide appears once under each drug.
    c.execute("""
        CREATE VIEW trial_drugs AS
        SELECT DISTINCT i.nct_id, p.drug
        FROM interventions i
        JOIN drug_patterns p ON LOWER(i.intervention_name) LIKE p.pattern
    """)

    # ── Analysis scope ───────────────────────────────────────────────────────
    # The raw pull keeps everything; analysis uses only trials that are:
    #   - interventional (not observational or expanded access)
    #   - testing a GLP-1 peptide (see DRUG_PATTERNS)
    #   - starting by LAST_YEAR (planned 2027+ starts and missing start dates dropped)
    # 2026 is a partial year: it covers registrations up to PULL_DATE and
    # includes trials whose planned start is later in 2026.
    c.execute(f"""
        CREATE VIEW studies_in_scope AS
        SELECT *
        FROM studies
        WHERE study_type = 'INTERVENTIONAL'
          AND nct_id IN (SELECT nct_id FROM trial_drugs)
          AND start_date <> ''
          AND CAST(SUBSTR(start_date, 1, 4) AS INTEGER) <= {LAST_YEAR}
    """)

    # ── Core trial-level view: one row per trial ────────────────────────────
    # phase_group assigns each trial its highest phase, so a Phase 2/3 trial
    # counts as Phase 3 and a Phase 1/2 trial as Phase 2. Early Phase 1 is
    # grouped with Phase 1. Trials with no phase (CT.gov "N/A", e.g. some
    # device or behavioral arms) are kept as "N/A".
    c.execute("""
        CREATE VIEW trials_clean AS
        SELECT
            s.nct_id,
            s.brief_title,
            s.overall_status,
            CAST(SUBSTR(s.start_date, 1, 4) AS INTEGER) AS start_year,
            s.start_date,
            s.primary_completion_date,
            s.phase,
            CASE
                WHEN s.phase LIKE '%3%'             THEN 'Phase 3'
                WHEN s.phase = 'Phase 4'            THEN 'Phase 4'
                WHEN s.phase LIKE '%2%'             THEN 'Phase 2'
                WHEN s.phase LIKE '%1%'             THEN 'Phase 1'
                ELSE 'N/A'
            END AS phase_group,
            sp.lead_sponsor_name,
            sp.lead_sponsor_class
        FROM studies_in_scope s
        JOIN sponsors sp ON s.nct_id = sp.nct_id
    """)

    n_raw = c.execute("SELECT COUNT(*) FROM studies").fetchone()[0]
    n_int = c.execute("SELECT COUNT(*) FROM studies WHERE study_type = 'INTERVENTIONAL'").fetchone()[0]
    n_glp = c.execute("""SELECT COUNT(*) FROM studies WHERE study_type = 'INTERVENTIONAL'
                         AND nct_id IN (SELECT nct_id FROM trial_drugs)""").fetchone()[0]
    n_scope = c.execute("SELECT COUNT(*) FROM studies_in_scope").fetchone()[0]
    print(f"  Scope: {n_raw} pulled -> {n_int} interventional -> {n_glp} testing a GLP-1 peptide "
          f"-> {n_scope} starting <= {LAST_YEAR} (pulled {PULL_DATE})")

    conn.commit()
    conn.close()
    print(f"\nDatabase built: {DB}")


if __name__ == "__main__":
    print("Building SQLite database...")
    build_db()
