SELECT
        SUBSTR(issue_date, 1, 4)    AS year,
        SUBSTR(issue_date, 1, 7)    AS month,
        COUNT(*)                    AS letters_issued,
        SUM(COUNT(*)) OVER (
            ORDER BY SUBSTR(issue_date, 1, 7)
        )                           AS cumulative_letters
    FROM warning_letters
    GROUP BY month
    ORDER BY month;