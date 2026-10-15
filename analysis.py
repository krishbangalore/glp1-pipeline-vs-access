"""
GLP-1 Pipeline vs. Accessibility — Core SQL Analysis
Runs the core sub-questions against the SQLite database.
Trial queries use studies_in_scope / trials_clean (interventional only, starts
through LAST_YEAR). LAST_YEAR is partial — data pulled PULL_DATE.
Saves results to data/processed/ as CSVs for use in visualizations.
"""

import sqlite3
import csv
import os

from build_db import DB, LAST_YEAR, PULL_DATE
OUT = "data/processed"
SQL_DIR = "sql"
os.makedirs(OUT, exist_ok=True)
os.makedirs(SQL_DIR, exist_ok=True)


def run_query(conn, name, sql):
    """Run a query, print results, save to CSV, and save SQL to file."""
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]

    # Save SQL file
    with open(f"{SQL_DIR}/{name}.sql", "w") as f:
        f.write(sql.strip())

    # Save results CSV
    with open(f"{OUT}/{name}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    return cols, rows


def main():
    conn = sqlite3.connect(DB)
    print("=" * 60)

    # ── Q1: Pipeline growth — trials started per year by phase ───────────────
    # GROUP BY 1, 2 groups on the relabelled phase, so EARLY_Phase 1 is merged
    # into Phase 1 (grouping on the bare `phase` name left two Phase 1 rows).
    sql_q1 = f"""
    SELECT
        start_year,
        CASE phase
            WHEN 'EARLY_Phase 1' THEN 'Phase 1'
            WHEN 'NA'            THEN 'N/A'
            ELSE phase
        END AS phase,
        COUNT(DISTINCT nct_id) AS trial_count
    FROM trials_clean
    WHERE start_year BETWEEN 2005 AND {LAST_YEAR}
      AND phase NOT IN ('N/A', 'NA', '')
    GROUP BY 1, 2
    ORDER BY 1, 2;
    """

    cols, rows = run_query(conn, "q1_pipeline_growth", sql_q1)
    print("\nQ1: Pipeline growth by year and phase (sample)")
    print(f"  {'Year':<8} {'Phase':<12} {'Trials':>8}")
    for r in rows[-12:]:
        print(f"  {r[0]:<8} {r[1]:<12} {r[2]:>8}")

    # ── Q2: Sponsor landscape — which companies dominate? ────────────────────
    sql_q2 = """
    SELECT
        sp.lead_sponsor_name,
        sp.lead_sponsor_class,
        COUNT(DISTINCT s.nct_id)                               AS total_trials,
        SUM(CASE WHEN s.phase = 'Phase 3' THEN 1 ELSE 0 END)  AS phase3_trials,
        ROUND(100.0 * COUNT(DISTINCT s.nct_id) /
              (SELECT COUNT(DISTINCT nct_id) FROM studies_in_scope), 1) AS pct_of_total
    FROM studies_in_scope s
    JOIN sponsors sp ON s.nct_id = sp.nct_id
    GROUP BY sp.lead_sponsor_name
    HAVING total_trials >= 5
    ORDER BY total_trials DESC
    LIMIT 15;
    """

    cols, rows = run_query(conn, "q2_sponsor_landscape", sql_q2)
    print("\nQ2: Top sponsors by trial count")
    print(f"  {'Sponsor':<40} {'Total':>7} {'Ph3':>5} {'%':>6}")
    for r in rows[:10]:
        print(f"  {r[0][:38]:<40} {r[2]:>7} {r[3]:>5} {r[4]:>5}%")

    # ── Q3: Drug-level breakdown — each GLP-1 peptide by phase ──────────────
    sql_q3 = """
    SELECT
        i.intervention_name                                      AS drug,
        s.phase,
        COUNT(DISTINCT s.nct_id)                                 AS trial_count,
        MIN(CAST(SUBSTR(s.start_date,1,4) AS INT))               AS first_trial_year,
        MAX(CAST(SUBSTR(s.start_date,1,4) AS INT))               AS latest_trial_year
    FROM studies_in_scope s
    JOIN interventions i ON s.nct_id = i.nct_id
    WHERE LOWER(i.intervention_type) = 'drug'
      AND LOWER(i.intervention_name) IN (
          'semaglutide','tirzepatide','liraglutide','dulaglutide',
          'exenatide','lixisenatide','retatrutide','ly3437943',
          'survodutide','pemvidutide','mazdutide'
      )
    GROUP BY i.intervention_name, s.phase
    ORDER BY i.intervention_name, s.phase;
    """

    cols, rows = run_query(conn, "q3_drug_phase_breakdown", sql_q3)
    print("\nQ3: Trial count by drug and phase (sample — retatrutide)")
    for r in rows:
        if r[0] == "retatrutide":
            print(f"  {r[0]:<16} {r[1]:<12} {r[2]:>5} trials  ({r[3]}–{r[4]})")

    # ── Q4: Shortage window — when was compounding legal? ───────────────────
    sql_q4 = """
    SELECT
        drug_name,
        shortage_start,
        start_precision,
        shortage_end,
        ROUND(
            (JULIANDAY(shortage_end) - JULIANDAY(shortage_start)) / 30.44
        , 1) AS shortage_months,
        wind_down_503a_end,
        wind_down_503b_end,
        notes,
        source_url
    FROM shortage_status
    ORDER BY shortage_start;
    """

    cols, rows = run_query(conn, "q4_shortage_window", sql_q4)
    print("\nQ4: FDA shortage windows (legal compounding period)")
    for r in rows:
        print(f"  {r[0]:<16} {r[1]} → {r[3]}  ({r[4]} months; 503B wind-down to {r[6]})")

    # ── Q5: Enforcement — documented FDA warning-letter batches ─────────────
    # One row per cited batch (hand-entered in build_db.py). Counts are as
    # reported by the source; see count_source for how firm each one is.
    sql_q5 = """
    SELECT
        letter_date,
        announced_date,
        letter_count,
        SUM(letter_count) OVER (ORDER BY letter_date) AS cumulative_letters,
        count_source,
        recipients,
        source_url
    FROM enforcement_events
    ORDER BY letter_date;
    """

    cols, rows = run_query(conn, "q5_enforcement_events", sql_q5)
    print("\nQ5: Documented FDA warning-letter batches (GLP-1 compounding/marketing)")
    for r in rows:
        print(f"  {r[0]}  {r[2]:>3} letters  (cumulative: {r[3]})  [{r[4][:40]}]")

    # ── Q6: Combined timeline — shortage + enforcement by year ───────────────
    sql_q6 = f"""
    WITH trial_counts AS (
        SELECT start_year AS year, COUNT(DISTINCT nct_id) AS new_trials
        FROM trials_clean
        WHERE start_year BETWEEN 2020 AND {LAST_YEAR}
        GROUP BY start_year
    ),
    letter_counts AS (
        SELECT CAST(SUBSTR(letter_date,1,4) AS INT) AS year, SUM(letter_count) AS letters
        FROM enforcement_events
        GROUP BY year
    )
    SELECT
        t.year,
        t.new_trials,
        COALESCE(l.letters, 0)  AS warning_letters,
        CASE
            WHEN t.year BETWEEN 2022 AND 2024 THEN 'Shortage active (compounding legal)'
            WHEN t.year = 2025              THEN 'Shortages resolved; wind-downs end; Sept letter batch'
            WHEN t.year = 2026              THEN 'Post-shortage; FDA proposes 503B exclusion'
            ELSE 'Pre-shortage'
        END                     AS period_label,
        CASE WHEN t.year = {LAST_YEAR} THEN 'partial (through {PULL_DATE})'
             ELSE 'full'
        END                     AS year_coverage
    FROM trial_counts t
    LEFT JOIN letter_counts l ON t.year = l.year
    ORDER BY t.year;
    """

    cols, rows = run_query(conn, "q6_combined_timeline", sql_q6)
    print(f"\nQ6: Combined timeline 2020-{LAST_YEAR} ({LAST_YEAR} partial, through {PULL_DATE})")
    print(f"  {'Year':<6} {'New Trials':>11} {'Letters':>9}  Status")
    for r in rows:
        print(f"  {r[0]:<6} {r[1]:>11} {r[2]:>9}  {r[3]}")

    conn.close()
    print("\n✓ All queries complete. Results saved to data/processed/")
    print("✓ SQL files saved to sql/")


if __name__ == "__main__":
    main()
