SELECT
        CASE WHEN lead_sponsor_class = 'INDUSTRY' THEN 'Industry' ELSE 'Non-industry' END AS sponsor_type,
        COUNT(*)                                                       AS total_trials,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM trials_clean), 1) AS pct_of_all_trials,
        SUM(CASE WHEN phase_group = 'Phase 3' THEN 1 ELSE 0 END)       AS phase3_trials,
        ROUND(100.0 * SUM(CASE WHEN phase_group = 'Phase 3' THEN 1 ELSE 0 END) /
              (SELECT COUNT(*) FROM trials_clean WHERE phase_group = 'Phase 3'), 1) AS pct_of_phase3
    FROM trials_clean
    GROUP BY 1
    ORDER BY 1;