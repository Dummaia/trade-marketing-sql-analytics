-- ============================================================
-- TRADE MARKETING ANALYTICS
-- Product Performance
-- ============================================================

SELECT
    p.product_name,
    b.brand_name,
    c.client_name,
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
    p.product_id, b.brand_id, c.client_id, p.product_name,
    b.brand_name,
    c.client_name

ORDER BY
    total_revenue DESC;

