"""
GLP-1 Pipeline vs. Accessibility — Core SQL Analysis
Runs the 5 core sub-questions against the SQLite database.
Saves results to data/processed/ as CSVs for use in visualizations.
"""

import sqlite3
import csv
import os

DB = "/tmp/glp1_analysis.db"
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
    sql_q1 = """
    SELECT
        start_year,
        phase,
        COUNT(DISTINCT nct_id) AS trial_count
    FROM trials_clean
    WHERE start_year BETWEEN 2005 AND 2026
      AND phase != 'N/A'
    GROUP BY start_year, phase
    ORDER BY start_year, phase;
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
              (SELECT COUNT(DISTINCT nct_id) FROM studies), 1) AS pct_of_total
    FROM studies s
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
    FROM studies s
    JOIN interventions i ON s.nct_id = i.nct_id
    WHERE i.intervention_type = 'Drug'
      AND i.intervention_name IN (
          'semaglutide','tirzepatide','liraglutide','dulaglutide',
          'exenatide','lixisenatide','retatrutide','survodutide',
          'pemvidutide','mazdutide'
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
        shortage_end,
        ROUND(
            (JULIANDAY(shortage_end) - JULIANDAY(shortage_start)) / 30.44
        , 1) AS shortage_months,
        notes
    FROM shortage_status
    ORDER BY shortage_start;
    """

    cols, rows = run_query(conn, "q4_shortage_window", sql_q4)
    print("\nQ4: FDA shortage windows (legal compounding period)")
    for r in rows:
        print(f"  {r[0]:<16} {r[1]} → {r[2]}  ({r[3]} months)")

    # ── Q5: Warning letters — how did enforcement ramp up? ───────────────────
    sql_q5 = """
    SELECT
        SUBSTR(issue_date, 1, 4)    AS year,
        SUBSTR(issue_date, 1, 7)    AS month,
        COUNT(*)                    AS letters_issued,
        SUM(COUNT(*)) OVER (
            ORDER BY SUBSTR(issue_date, 1, 7)
        )                           AS cumulative_letters
    FROM warning_letters
    GROUP BY month
    ORDER BY month;
    """

    cols, rows = run_query(conn, "q5_warning_letters", sql_q5)
    print("\nQ5: Warning letters by month (sample)")
    for r in rows[-8:]:
        print(f"  {r[1]}  {r[2]:>4} letters  (cumulative: {r[3]})")

    # ── Q6: Combined timeline — shortage + enforcement by year ───────────────
    sql_q6 = """
    WITH trial_counts AS (
        SELECT start_year AS year, COUNT(DISTINCT nct_id) AS new_trials
        FROM trials_clean
        WHERE start_year BETWEEN 2020 AND 2026
        GROUP BY start_year
    ),
    letter_counts AS (
        SELECT CAST(SUBSTR(issue_date,1,4) AS INT) AS year, COUNT(*) AS letters
        FROM warning_letters
        GROUP BY year
    )
    SELECT
        t.year,
        t.new_trials,
        COALESCE(l.letters, 0)  AS warning_letters,
        CASE
            WHEN t.year BETWEEN 2022 AND 2024 THEN 'Shortage active (compounding legal)'
            WHEN t.year = 2025              THEN 'Shortage resolved; enforcement surge'
            WHEN t.year = 2026              THEN 'Post-shortage; FDA proposed 503B exclusion'
            ELSE 'Pre-shortage'
        END                     AS period_label
    FROM trial_counts t
    LEFT JOIN letter_counts l ON t.year = l.year
    ORDER BY t.year;
    """

    cols, rows = run_query(conn, "q6_combined_timeline", sql_q6)
    print("\nQ6: Combined timeline 2020-2026")
    print(f"  {'Year':<6} {'New Trials':>11} {'Letters':>9}  Status")
    for r in rows:
        print(f"  {r[0]:<6} {r[1]:>11} {r[2]:>9}  {r[3]}")

    conn.close()
    print("\n✓ All queries complete. Results saved to data/processed/")
    print("✓ SQL files saved to sql/")


if __name__ == "__main__":
    main()
