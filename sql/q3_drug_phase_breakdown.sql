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