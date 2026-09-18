-- Cobertura inferida pelas datas extremas; não comprova completude da ingestão.
WITH bounds AS (
 SELECT MIN(sale_date) AS first_date, MAX(sale_date) AS last_date FROM sell_out
), months AS (
 SELECT generate_series(
  date_trunc('month', first_date) + CASE WHEN EXTRACT(DAY FROM first_date)=1 THEN INTERVAL '0 month' ELSE INTERVAL '1 month' END,
  date_trunc('month', last_date) - CASE WHEN last_date=(date_trunc('month', last_date)+INTERVAL '1 month - 1 day')::date THEN INTERVAL '0 month' ELSE INTERVAL '1 month' END,
  INTERVAL '1 month')::date AS month FROM bounds
), monthly_revenue AS (
 SELECT m.month, SUM(s.quantity*s.unit_price) AS total_revenue
 FROM months m LEFT JOIN sell_out s ON s.sale_date>=m.month AND s.sale_date<m.month+INTERVAL '1 month'
 GROUP BY m.month
), comparison AS (
 SELECT month, total_revenue, LAG(total_revenue) OVER (ORDER BY month) AS previous_month_revenue FROM monthly_revenue
)
SELECT month, ROUND(total_revenue,2) AS total_revenue, previous_month_revenue,
 ROUND((total_revenue-previous_month_revenue)/NULLIF(previous_month_revenue,0)*100,2) AS growth_pct
FROM comparison ORDER BY month;
