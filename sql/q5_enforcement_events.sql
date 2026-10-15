SELECT
        letter_date,
        announced_date,
        letter_count,
        SUM(letter_count) OVER (ORDER BY letter_date) AS cumulative_letters,
        count_source,
        recipients,
        source_url
    FROM enforcement_events
    ORDER BY letter_date;