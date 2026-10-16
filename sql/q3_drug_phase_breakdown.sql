SELECT
        d.drug,
        t.phase_group                AS phase,
        COUNT(*)                     AS trial_count,
        MIN(t.start_year)            AS first_trial_year,
        MAX(t.start_year)            AS latest_trial_year
    FROM trial_drugs d
    JOIN trials_clean t ON d.nct_id = t.nct_id
    GROUP BY d.drug, t.phase_group
    ORDER BY d.drug, t.phase_group;