-- ============================================================
-- TRADE MARKETING ANALYTICS
-- Executive Overview
-- ============================================================

SELECT
    COUNT(*) AS total_sales_records,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(quantity * unit_price), 2) AS total_revenue,
    ROUND(AVG(quantity), 2) AS avg_units_per_record,
    ROUND(AVG(quantity * unit_price), 2) AS avg_revenue_per_record
FROM sell_out;

