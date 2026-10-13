SELECT
        start_year,
        phase,
        COUNT(DISTINCT nct_id) AS trial_count
    FROM trials_clean
    WHERE start_year BETWEEN 2005 AND 2026
      AND phase != 'N/A'
    GROUP BY start_year, phase
    ORDER BY start_year, phase;