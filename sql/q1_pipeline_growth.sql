SELECT
        start_year,
        phase_group AS phase,
        COUNT(*) AS trial_count
    FROM trials_clean
    WHERE start_year BETWEEN 2005 AND 2026
    GROUP BY 1, 2
    ORDER BY 1, 2;