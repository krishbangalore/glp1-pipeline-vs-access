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