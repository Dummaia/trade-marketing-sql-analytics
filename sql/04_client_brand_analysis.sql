-- ============================================================
-- TRADE MARKETING ANALYTICS
-- Client & Brand Performance
-- ============================================================


-- ------------------------------------------------------------
-- 1. Revenue by Client and Brand
-- ------------------------------------------------------------

SELECT
    c.client_name,
    b.brand_name,
    SUM(s.quantity) AS total_units_sold,
    ROUND(SUM(s.quantity * s.unit_price), 2) AS total_revenue
FROM sell_out s

JOIN products p
    ON s.product_id = p.product_id

JOIN brands b
    ON p.brand_id = b.brand_id

JOIN clients c
    ON b.client_id = c.client_id

GROUP BY
    c.client_id, b.brand_id, c.client_name,
    b.brand_name

ORDER BY
    total_revenue DESC;


-- ------------------------------------------------------------
-- 2. Revenue Share by Client
-- ------------------------------------------------------------

WITH client_revenue AS (
    SELECT
        c.client_name,
        SUM(s.quantity * s.unit_price) AS total_revenue
    FROM sell_out s

    JOIN products p
        ON s.product_id = p.product_id

    JOIN brands b
        ON p.brand_id = b.brand_id

    JOIN clients c
        ON b.client_id = c.client_id

    GROUP BY
        c.client_id, c.client_name
)

SELECT
    client_name,
    ROUND(total_revenue, 2) AS total_revenue,
    ROUND(
        total_revenue
        / NULLIF(SUM(total_revenue) OVER (), 0) * 100,
        2
    ) AS revenue_share_pct
FROM client_revenue

ORDER BY
    total_revenue DESC;
    