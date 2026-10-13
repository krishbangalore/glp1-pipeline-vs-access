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