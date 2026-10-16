SELECT
        lead_sponsor_name,
        lead_sponsor_class,
        COUNT(*)                                                    AS total_trials,
        SUM(CASE WHEN phase_group = 'Phase 3' THEN 1 ELSE 0 END)    AS phase3_trials,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM trials_clean), 1) AS pct_of_total
    FROM trials_clean
    GROUP BY lead_sponsor_name, lead_sponsor_class
    ORDER BY total_trials DESC, lead_sponsor_name
    LIMIT 15;