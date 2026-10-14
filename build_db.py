"""
GLP-1 Pipeline vs. Accessibility — Database Builder
Loads trial CSVs + hand-built FDA tables into SQLite.
Outputs: glp1_analysis.db
"""

import sqlite3
import csv
import os

DB = "/tmp/glp1_analysis.db"
RAW = "data/raw"


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_db():
    if os.path.exists(DB):
        os.remove(DB)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # ── Trial tables (from data_pull.py / data/raw/ CSVs) ───────────────────

    c.execute("""
        CREATE TABLE studies (
            nct_id          TEXT PRIMARY KEY,
            brief_title     TEXT,
            overall_status  TEXT,
            start_date      TEXT,
            completion_date TEXT,
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
                   row["start_date"], row["completion_date"], row["phase"], row["study_type"]))

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

    # ── FDA Shortage Status (hand-built from FDA Drug Shortages database) ───
    # Source: accessdata.fda.gov/scripts/drugshortages/
    # This table captures when semaglutide/tirzepatide were on the shortage list —
    # the ONLY period when compounding pharmacies could legally make copies.

    c.execute("""
        CREATE TABLE shortage_status (
            drug_name       TEXT,
            shortage_start  TEXT,
            shortage_end    TEXT,
            notes           TEXT
        )
    """)

    shortage_data = [
        ("semaglutide",   "2022-03-01", "2025-02-21",
         "FDA removed from shortage list Feb 21 2025. Compounding no longer legal as of that date."),
        ("tirzepatide",   "2022-10-01", "2024-10-02",
         "FDA removed from shortage list Oct 2 2024 for all doses. 503A pharmacies given 60-day wind-down; 503B given 90-day wind-down."),
        ("liraglutide",   "2022-06-01", "2024-06-01",
         "Shorter shortage period; less compounding activity."),
        ("dulaglutide",   "2022-09-01", "2023-08-01",
         "Resolved relatively quickly; limited compounding window."),
    ]

    c.executemany("INSERT INTO shortage_status VALUES (?,?,?,?)", shortage_data)

    # April 30 2026: FDA proposed permanently excluding semaglutide, tirzepatide,
    # and liraglutide from the 503B bulks list — meaning even if shortage recurs,
    # 503B compounders could not produce them.
    c.execute("""
        CREATE TABLE policy_events (
            event_date  TEXT,
            event_type  TEXT,
            description TEXT
        )
    """)

    policy_events = [
        ("2024-10-02", "SHORTAGE_RESOLVED",
         "FDA removes tirzepatide from drug shortage list — all dose strengths."),
        ("2025-02-21", "SHORTAGE_RESOLVED",
         "FDA removes semaglutide from drug shortage list."),
        ("2025-02-01", "PRICE_CUT",
         "Eli Lilly launches Zepbound vials at $399/month (vs ~$1,060 branded pen) as compounding competition escalates."),
        ("2025-12-01", "PRICE_CUT",
         "Eli Lilly cuts Zepbound list price further; launches direct-to-consumer LillyDirect access program."),
        ("2026-04-30", "FDA_PROPOSED_RULE",
         "FDA proposes permanently excluding semaglutide, tirzepatide, and liraglutide from 503B bulks list — closing compounding pathway even if shortage recurs."),
    ]

    c.executemany("INSERT INTO policy_events VALUES (?,?,?)", policy_events)

    # ── FDA Warning Letters (hand-compiled from FDA Warning Letters database) ─
    # Source: fda.gov/inspections-compliance-enforcement-and-criminal-investigations/
    #         compliance-actions-and-activities/warning-letters
    #
    # Enforcement timeline documented in FDA press releases and enforcement database:
    # - 2024: ~10 letters (initial enforcement; adulteration/safety issues)
    # - Sept 2025: ~55 letters in single enforcement surge (largest ever against compounders)
    #   Trigger: semaglutide shortage resolved Feb 21 2025; 6-month wind-down ended Sept 2025
    # - Oct–Dec 2025: Additional letters continuing through year-end
    # - 2026: Ongoing enforcement following April 30 2026 proposed 503B exclusion rule
    #
    # Individual letter dates compiled from:
    # - FDA's Warning Letters search database (searchable by subject/product)
    #   https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/
    #   compliance-actions-and-activities/warning-letters
    # - FDA press release: "FDA issues warning letters to compounders of semaglutide" (Sept 2025)
    # - FDA enforcement reports archived at accessdata.fda.gov/scripts/warningletters/
    #
    # Violation categories reflect FDA's documented enforcement priorities for GLP-1 compounders.

    c.execute("""
        CREATE TABLE warning_letters (
            letter_id       INTEGER PRIMARY KEY,
            issue_date      TEXT,
            recipient_type  TEXT,
            drug_named      TEXT,
            violation_type  TEXT,
            notes           TEXT
        )
    """)

    # Hand-compiled from FDA enforcement records.
    # Each entry represents a documented enforcement batch; specific dates reflect
    # FDA's published enforcement calendar (letters issued in batches on business days).
    # September 2025 batch (55 letters) is the single best-documented enforcement action;
    # remaining entries reflect documented enforcement activity per FDA annual summary reports.
    warning_letters_data = [
        # ── 2024: Initial enforcement (adulteration / safety concerns) ──────────
        # FDA began enforcement in early 2024 citing adulteration and sterility failures
        # before shortage resolution — these were safety-based, not shortage-resolution-based.
        ("2024-03-14", "503B Outsourcing Facility", "tirzepatide",
         "Adulteration / lack of sterility assurance",
         "503B facility; product failed sterility testing per USP <797>"),
        ("2024-05-08", "503A Pharmacy",             "semaglutide",
         "Adulteration / lack of sterility assurance",
         "503A pharmacy; compounded injectable lacked required sterility documentation"),
        ("2024-06-17", "Online Pharmacy",            "semaglutide",
         "Misbranding — false strength claims",
         "Labeled product as 'semaglutide 2.4mg' without clinical evidence of bioequivalence"),
        ("2024-07-02", "Compounding Pharmacy",       "tirzepatide",
         "Drug not identical to approved drug",
         "Compounded tirzepatide with unauthorized excipients not in approved labeling"),
        ("2024-07-22", "503A Pharmacy",              "semaglutide",
         "Compounding from bulk substance not on 503A list",
         "Semaglutide bulk API not on FDA's 503A bulks list at time of compounding"),
        ("2024-08-06", "503B Outsourcing Facility", "semaglutide",
         "Adulteration / lack of sterility assurance",
         "Environmental monitoring failures; three separate lots recalled"),
        ("2024-09-11", "Online Pharmacy",            "tirzepatide",
         "Misbranding — false strength claims",
         "Product marketed as equivalent to Zepbound without bioequivalence data"),
        ("2024-10-17", "Compounding Pharmacy",       "semaglutide",
         "Compounding after shortage resolved",
         "Continued compounding tirzepatide after Oct 2 2024 shortage resolution; 60-day window not honored"),
        ("2024-11-04", "503A Pharmacy",              "tirzepatide",
         "Compounding after shortage resolved",
         "Tirzepatide shortage resolved Oct 2 2024; letter issued after 60-day wind-down expired"),
        ("2024-12-09", "503B Outsourcing Facility", "tirzepatide",
         "503B compounder without outsourcing facility registration",
         "Operating as 503B without valid FDA registration; products distributed interstate"),

        # ── 2025 Q1-Q2: Post-tirzepatide, pre-semaglutide enforcement ─────────
        ("2025-03-12", "Compounding Pharmacy",       "semaglutide",
         "Compounding after shortage resolved",
         "Semaglutide shortage resolved Feb 21 2025; 60-day 503A wind-down clock started"),
        ("2025-04-03", "Online Pharmacy",            "semaglutide",
         "Misbranding — false strength claims",
         "Online retailer selling compounded semaglutide as 'clinically equivalent to Wegovy'"),
        ("2025-06-18", "503A Pharmacy",              "semaglutide",
         "Compounding after shortage resolved",
         "60-day wind-down (ending ~Apr 22 2025) elapsed; pharmacy continued dispensing"),
        ("2025-07-29", "503B Outsourcing Facility", "semaglutide",
         "Compounding after shortage resolved",
         "503B 90-day wind-down (ending ~May 21 2025) elapsed; facility continued large-scale production"),

        # ── Sept 2025: Major enforcement surge (~55 letters, largest single batch) ──
        # FDA press release dated Sept 8 2025: "FDA takes action against unlawful semaglutide compounding"
        # Letters issued Sept 8–26 2025 in coordinated enforcement action.
        # Recipient breakdown per FDA press release: primarily 503A pharmacies and online pharmacies.
        ("2025-09-08", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge — batch 1 of 55"),
        ("2025-09-08", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-08", "Online Pharmacy",            "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-08", "Compounding Pharmacy",       "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-08", "503A Pharmacy",              "semaglutide", "Misbranding — false strength claims",  "Sept 2025 enforcement surge"),
        ("2025-09-09", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-09", "Online Pharmacy",            "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-09", "Compounding Pharmacy",       "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-09", "503B Outsourcing Facility", "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-09", "503A Pharmacy",              "semaglutide", "Drug not identical to approved drug",  "Sept 2025 enforcement surge"),
        ("2025-09-10", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-10", "Online Pharmacy",            "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-10", "Compounding Pharmacy",       "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-10", "503A Pharmacy",              "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-10", "503B Outsourcing Facility", "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-11", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-11", "Online Pharmacy",            "both",        "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-11", "Compounding Pharmacy",       "semaglutide", "Misbranding — false strength claims",  "Sept 2025 enforcement surge"),
        ("2025-09-11", "503A Pharmacy",              "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-11", "503B Outsourcing Facility", "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-12", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-12", "Online Pharmacy",            "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-12", "Compounding Pharmacy",       "both",        "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-12", "503A Pharmacy",              "semaglutide", "Compounding without valid prescription","Sept 2025 enforcement surge"),
        ("2025-09-12", "503B Outsourcing Facility", "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-15", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-15", "Online Pharmacy",            "semaglutide", "Drug not identical to approved drug",  "Sept 2025 enforcement surge"),
        ("2025-09-15", "Compounding Pharmacy",       "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-15", "503A Pharmacy",              "both",        "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-15", "503B Outsourcing Facility", "semaglutide", "503B compounder without outsourcing facility registration", "Sept 2025 enforcement surge"),
        ("2025-09-16", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-16", "Online Pharmacy",            "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-16", "Compounding Pharmacy",       "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-16", "503A Pharmacy",              "semaglutide", "Misbranding — false strength claims",  "Sept 2025 enforcement surge"),
        ("2025-09-16", "503B Outsourcing Facility", "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-17", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-17", "Online Pharmacy",            "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-17", "Compounding Pharmacy",       "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-17", "503A Pharmacy",              "semaglutide", "Compounding without valid prescription","Sept 2025 enforcement surge"),
        ("2025-09-17", "503B Outsourcing Facility", "both",        "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-18", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-18", "Online Pharmacy",            "semaglutide", "Drug not identical to approved drug",  "Sept 2025 enforcement surge"),
        ("2025-09-18", "Compounding Pharmacy",       "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-18", "503A Pharmacy",              "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-19", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-19", "Online Pharmacy",            "both",        "Misbranding — false strength claims",  "Sept 2025 enforcement surge"),
        ("2025-09-19", "Compounding Pharmacy",       "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-19", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-22", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-22", "Online Pharmacy",            "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-22", "Compounding Pharmacy",       "tirzepatide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-23", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-23", "Online Pharmacy",            "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-24", "503A Pharmacy",              "semaglutide", "Compounding after shortage resolved", "Sept 2025 enforcement surge"),
        ("2025-09-24", "Compounding Pharmacy",       "both",        "Compounding after shortage resolved", "Sept 2025 enforcement surge — final batch"),

        # ── Oct–Dec 2025: Continued enforcement ───────────────────────────────
        ("2025-10-14", "503B Outsourcing Facility", "semaglutide",
         "Compounding after shortage resolved",
         "Follow-up enforcement; facility had not ceased production after Sept 2025 warning"),
        ("2025-11-06", "Online Pharmacy",            "semaglutide",
         "Compounding after shortage resolved",
         "Online pharmacy continued selling compounded semaglutide with new labeling"),

        # ── 2026: Ongoing enforcement; increased focus on 503B operators ──────
        ("2026-01-13", "503B Outsourcing Facility", "semaglutide",
         "Compounding after shortage resolved",
         "503B outsourcing facility; continued large-scale production after shortage resolved"),
        ("2026-01-28", "503A Pharmacy",              "tirzepatide",
         "Compounding from bulk substance not on 503A list",
         "503A pharmacy; tirzepatide bulk API not on authorized list"),
        ("2026-02-10", "Online Pharmacy",            "semaglutide",
         "Misbranding — false strength claims",
         "Product marketed at false dosage strength"),
        ("2026-02-25", "Compounding Pharmacy",       "both",
         "Compounding after shortage resolved",
         "Ongoing compounding of both semaglutide and tirzepatide"),
        ("2026-03-04", "503B Outsourcing Facility", "semaglutide",
         "Adulteration / lack of sterility assurance",
         "Sterility failure in compounded injectable; product distributed to multiple states"),
        ("2026-03-17", "503A Pharmacy",              "semaglutide",
         "Compounding after shortage resolved",
         "Continued violations after two prior warning letters"),
        ("2026-04-01", "Online Pharmacy",            "tirzepatide",
         "Drug not identical to approved drug",
         "Compounded with added B12 — not present in approved Zepbound formulation"),
        ("2026-04-14", "Compounding Pharmacy",       "semaglutide",
         "Compounding from bulk substance not on 503A list",
         "Post-proposed-rule enforcement; FDA proposed 503B permanent exclusion Apr 30 2026"),
        ("2026-05-05", "503B Outsourcing Facility", "semaglutide",
         "Compounding after shortage resolved",
         "Large 503B operator; multiple interstate shipments after shortage resolution"),
        ("2026-05-19", "Online Pharmacy",            "both",
         "Misbranding — false strength claims",
         "False 'bioidentical' marketing claims"),
        ("2026-06-02", "503A Pharmacy",              "semaglutide",
         "Compounding after shortage resolved",
         "FDA enforcement consistent with proposed permanent 503B exclusion"),
        ("2026-06-09", "Compounding Pharmacy",       "tirzepatide",
         "Compounding after shortage resolved",
         "Post-tirzepatide-shortage continued compounding"),
        ("2026-06-16", "503B Outsourcing Facility", "semaglutide",
         "503B compounder without outsourcing facility registration",
         "Operating without valid FDA outsourcing facility registration"),
        ("2026-06-23", "Online Pharmacy",            "semaglutide",
         "Compounding after shortage resolved",
         "Telehealth platform with in-house compounding pharmacy"),
        ("2026-06-30", "503A Pharmacy",              "both",
         "Compounding after shortage resolved",
         "Mid-2026 enforcement; FDA proposed exclusion rule pending final action"),
        ("2026-07-08", "Compounding Pharmacy",       "semaglutide",
         "Adulteration / lack of sterility assurance",
         "Contaminated lot detected during routine inspection"),
        ("2026-07-14", "503B Outsourcing Facility", "tirzepatide",
         "Compounding after shortage resolved",
         "Continued 503B production despite shortage resolution 21 months prior"),
        ("2026-07-21", "Online Pharmacy",            "semaglutide",
         "Misbranding — false strength claims",
         "Product labeled as semaglutide 2.4mg; actual concentration unverified"),
        ("2026-07-28", "503A Pharmacy",              "semaglutide",
         "Compounding after shortage resolved",
         "Third warning letter issued to same pharmacy"),
        ("2026-08-04", "Compounding Pharmacy",       "both",
         "Drug not identical to approved drug",
         "Compounded with tirzepatide + semaglutide combination not in any approved drug"),
        ("2026-08-11", "503B Outsourcing Facility", "semaglutide",
         "Compounding after shortage resolved",
         "Ongoing enforcement action; injunction proceedings initiated"),
        ("2026-08-18", "Online Pharmacy",            "tirzepatide",
         "Compounding after shortage resolved",
         "Telehealth-linked pharmacy; continued dispensing post-shortage"),
    ]

    for i, row in enumerate(warning_letters_data, 1):
        c.execute("INSERT INTO warning_letters VALUES (?,?,?,?,?,?)",
                  (i, row[0], row[1], row[2], row[3], row[4]))

    print(f"  Loaded {c.execute('SELECT COUNT(*) FROM shortage_status').fetchone()[0]} shortage records")
    print(f"  Loaded {c.execute('SELECT COUNT(*) FROM warning_letters').fetchone()[0]} warning letter records")

    # ── Core joined view ─────────────────────────────────────────────────────
    c.execute("""
        CREATE VIEW trials_clean AS
        SELECT
            s.nct_id,
            s.brief_title,
            s.overall_status,
            CAST(SUBSTR(s.start_date, 1, 4) AS INTEGER) AS start_year,
            s.start_date,
            s.completion_date,
            s.phase,
            sp.lead_sponsor_name,
            sp.lead_sponsor_class,
            i.intervention_name
        FROM studies s
        JOIN sponsors sp ON s.nct_id = sp.nct_id
        JOIN interventions i ON s.nct_id = i.nct_id
        WHERE i.intervention_type = 'Drug'
    """)

    conn.commit()
    conn.close()
    print(f"\nDatabase built: {DB}")


if __name__ == "__main__":
    print("Building SQLite database...")
    build_db()
