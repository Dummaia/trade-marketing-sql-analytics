-- ============================================================
-- TRADE MARKETING ANALYTICS
-- Retailer & PDV Performance
-- ============================================================


-- ------------------------------------------------------------
-- 1. Performance by Retailer
-- ------------------------------------------------------------

SELECT
    r.retailer_name,
    r.channel,
    SUM(s.quantity) AS total_units_sold,
    ROUND(SUM(s.quantity * s.unit_price), 2) AS total_revenue
FROM sell_out s

JOIN stores st
    ON s.store_id = st.store_id

JOIN retailers r
    ON st.retailer_id = r.retailer_id

GROUP BY
    r.retailer_id, r.retailer_name,
    r.channel

ORDER BY
    total_revenue DESC;


-- ------------------------------------------------------------
-- 2. Performance by Store / PDV
-- ------------------------------------------------------------

SELECT
    st.store_name,
    r.retailer_name,
    st.city,
    st.state,
    SUM(s.quantity) AS total_units_sold,
    ROUND(SUM(s.quantity * s.unit_price), 2) AS total_revenue
FROM sell_out s

JOIN stores st
    ON s.store_id = st.store_id

JOIN retailers r
    ON st.retailer_id = r.retailer_id

GROUP BY
    st.store_id, r.retailer_id, st.store_name,
    r.retailer_name,
    st.city,
    st.state

ORDER BY
    total_revenue DESC;


-- ------------------------------------------------------------
-- 3. Average Revenue per Store
-- ------------------------------------------------------------

SELECT
    r.retailer_name,
    COUNT(DISTINCT st.store_id) AS total_stores,
    SUM(s.quantity) AS total_units_sold,
    ROUND(SUM(s.quantity * s.unit_price), 2) AS total_revenue,
    ROUND(
        SUM(s.quantity * s.unit_price)
        / COUNT(DISTINCT st.store_id),
        2
    ) AS avg_revenue_per_store
FROM sell_out s

JOIN stores st
    ON s.store_id = st.store_id

JOIN retailers r
    ON st.retailer_id = r.retailer_id

GROUP BY
    r.retailer_id, r.retailer_name

ORDER BY
    avg_revenue_per_store DESC;