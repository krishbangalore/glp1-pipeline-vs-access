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