SELECT
        drug_name,
        shortage_start,
        start_precision,
        shortage_end,
        ROUND(
            (JULIANDAY(shortage_end) - JULIANDAY(shortage_start)) / 30.44
        , 1) AS shortage_months,
        wind_down_503a_end,
        wind_down_503b_end,
        notes,
        source_url
    FROM shortage_status
    ORDER BY shortage_start;