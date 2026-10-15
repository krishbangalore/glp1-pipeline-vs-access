SELECT
        start_year,
        CASE phase
            WHEN 'EARLY_Phase 1' THEN 'Phase 1'
            WHEN 'NA'            THEN 'N/A'
            ELSE phase
        END AS phase,
        COUNT(DISTINCT nct_id) AS trial_count
    FROM trials_clean
    WHERE start_year BETWEEN 2005 AND 2026
      AND phase NOT IN ('N/A', 'NA', '')
    GROUP BY 1, 2
    ORDER BY 1, 2;