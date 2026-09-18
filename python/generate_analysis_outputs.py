from __future__ import annotations

from getpass import getpass
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_NAME = os.getenv("PGDATABASE", "trade_marketing")
DB_USER = os.getenv("PGUSER", "postgres")


# ============================================================
# DATABASE
# ============================================================

password = os.getenv("PGPASSWORD") or getpass("Senha do PostgreSQL: ")

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=DB_USER,
    password=password,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

engine = create_engine(database_url)


# ============================================================
# HELPERS
# ============================================================

def br_int(value: float | int) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def br_decimal(value: float, decimals: int = 2) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def br_money(value: float) -> str:
    return f"R$ {br_decimal(value, 2)}"


def br_money_mi(value: float) -> str:
    return f"R$ {br_decimal(value / 1_000_000, 2)} mi"


def money_mi_axis(value, _):
    return f"R$ {value / 1_000_000:.1f} mi"


def save_csv(df: pd.DataFrame, filename: str) -> None:
    df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")


def finish_figure(fig, filename: str, latest_date=None) -> None:
    footer = "Dados sintéticos • Fonte: PostgreSQL"
    if latest_date is not None and pd.notna(latest_date):
        footer += f" • Base até {pd.Timestamp(latest_date).strftime('%d/%m/%Y')}"

    fig.text(
        0.01,
        0.01,
        footer,
        fontsize=9,
        alpha=0.7,
    )
    fig.savefig(
        OUTPUT_DIR / filename,
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)


def add_bar_labels(ax, formatter) -> None:
    for container in ax.containers:
        labels = [formatter(bar.get_width()) for bar in container]
        ax.bar_label(container, labels=labels, padding=4, fontsize=9)


# ============================================================
# BASE METADATA
# ============================================================

metadata_query = """
SELECT
    MIN(sale_date) AS min_sale_date,
    MAX(sale_date) AS max_sale_date
FROM sell_out;
"""

metadata = pd.read_sql(metadata_query, engine)
latest_date = metadata.loc[0, "max_sale_date"]


# ============================================================
# 1. EXECUTIVE KPIs
# ============================================================

executive_query = """
SELECT
    COUNT(*) AS total_sales_records,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(quantity * unit_price), 2) AS total_revenue,
    ROUND(AVG(quantity), 2) AS avg_units_per_record,
    ROUND(AVG(quantity * unit_price), 2) AS avg_revenue_per_record
FROM sell_out;
"""

executive = pd.read_sql(executive_query, engine)
save_csv(executive, "01_executive_kpis.csv")

if executive.loc[0, "total_sales_records"] == 0:
    raise SystemExit("A tabela sell_out está vazia. Execute a carga antes das análises.")

total_records = int(executive.loc[0, "total_sales_records"])
total_units = int(executive.loc[0, "total_units_sold"])
total_revenue = float(executive.loc[0, "total_revenue"])
avg_units = float(executive.loc[0, "avg_units_per_record"])

fig = plt.figure(figsize=(14, 5))

fig.text(0.04, 0.89, "Trade Marketing Analytics", fontsize=24, weight="bold")
fig.text(0.04, 0.81, "Sell-out & PDV Performance", fontsize=13)

kpis = [
    (0.10, br_int(total_records), "Registros de Sell-out"),
    (0.37, br_int(total_units), "Unidades vendidas"),
    (0.65, br_money_mi(total_revenue), "Revenue total"),
    (0.90, br_decimal(avg_units, 2), "Unidades por registro"),
]

for x, value, label in kpis:
    fig.text(x, 0.49, value, fontsize=25, weight="bold", ha="center")
    fig.text(x, 0.39, label, fontsize=11, ha="center")

plt.axis("off")
finish_figure(fig, "01_executive_kpis.png", latest_date)


# ============================================================
# 2. PRODUCT PERFORMANCE
# ============================================================

product_query = """
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
"""

products = pd.read_sql(product_query, engine)
save_csv(products, "02_product_performance.csv")

plot_df = products.sort_values("total_revenue", ascending=True)

fig, ax = plt.subplots(figsize=(12, 7))
ax.barh(plot_df["product_name"], plot_df["total_revenue"])
ax.set_title("Revenue por Produto", fontsize=18, weight="bold", loc="left")
ax.set_xlabel("Revenue")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(FuncFormatter(money_mi_axis))
ax.grid(axis="x", alpha=0.2)
add_bar_labels(ax, br_money_mi)
fig.tight_layout(rect=[0, 0.05, 1, 0.96])
finish_figure(fig, "02_product_revenue.png", latest_date)


# ============================================================
# 3. RETAILER PERFORMANCE
# ============================================================

retailer_query = """
SELECT
    r.retailer_name,
    r.channel,
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
    r.retailer_id, r.retailer_name,
    r.channel
ORDER BY
    total_revenue DESC;
"""

retailers = pd.read_sql(retailer_query, engine)
save_csv(retailers, "03_retailer_performance.csv")

plot_df = retailers.sort_values("total_revenue", ascending=True)

fig, ax = plt.subplots(figsize=(11, 6))
ax.barh(plot_df["retailer_name"], plot_df["total_revenue"])
ax.set_title("Revenue por Retailer", fontsize=18, weight="bold", loc="left")
ax.set_xlabel("Revenue")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(FuncFormatter(money_mi_axis))
ax.grid(axis="x", alpha=0.2)
add_bar_labels(ax, br_money_mi)
fig.tight_layout(rect=[0, 0.05, 1, 0.96])
finish_figure(fig, "03_retailer_revenue.png", latest_date)

plot_df = retailers.sort_values("avg_revenue_per_store", ascending=True)

fig, ax = plt.subplots(figsize=(11, 6))
ax.barh(plot_df["retailer_name"], plot_df["avg_revenue_per_store"])
ax.set_title("Revenue Médio por PDV", fontsize=18, weight="bold", loc="left")
ax.set_xlabel("Revenue médio por loja")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(FuncFormatter(money_mi_axis))
ax.grid(axis="x", alpha=0.2)
add_bar_labels(ax, br_money_mi)
fig.tight_layout(rect=[0, 0.05, 1, 0.96])
finish_figure(fig, "04_retailer_avg_revenue_per_store.png", latest_date)


# ============================================================
# 4. STORE / PDV PERFORMANCE
# ============================================================

store_query = """
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
"""

stores = pd.read_sql(store_query, engine)
save_csv(stores, "04_store_performance.csv")

plot_df = stores.sort_values("total_revenue", ascending=True)

fig, ax = plt.subplots(figsize=(12, 7))
ax.barh(plot_df["store_name"], plot_df["total_revenue"])
ax.set_title("Revenue por PDV", fontsize=18, weight="bold", loc="left")
ax.set_xlabel("Revenue")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(FuncFormatter(money_mi_axis))
ax.grid(axis="x", alpha=0.2)
add_bar_labels(ax, br_money_mi)
fig.tight_layout(rect=[0, 0.05, 1, 0.96])
finish_figure(fig, "05_store_revenue.png", latest_date)


# ============================================================
# 5. CLIENT REVENUE SHARE
# ============================================================

client_query = """
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
        total_revenue / NULLIF(SUM(total_revenue) OVER (), 0) * 100,
        2
    ) AS revenue_share_pct
FROM client_revenue
ORDER BY
    total_revenue DESC;
"""

clients = pd.read_sql(client_query, engine)
save_csv(clients, "05_client_revenue_share.csv")

plot_df = clients.sort_values("revenue_share_pct", ascending=True)

fig, ax = plt.subplots(figsize=(11, 6))
ax.barh(plot_df["client_name"], plot_df["revenue_share_pct"])
ax.set_title("Participação no Revenue por Cliente", fontsize=18, weight="bold", loc="left")
ax.set_xlabel("Participação no revenue total (%)")
ax.set_ylabel("")
ax.grid(axis="x", alpha=0.2)

for container in ax.containers:
    labels = [f"{bar.get_width():.2f}%".replace(".", ",") for bar in container]
    ax.bar_label(container, labels=labels, padding=4, fontsize=9)

fig.tight_layout(rect=[0, 0.05, 1, 0.96])
finish_figure(fig, "06_client_revenue_share.png", latest_date)


# ============================================================
# 6. MONTHLY PERFORMANCE
#    Only complete months are included automatically.
# ============================================================

monthly_query = """
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
"""

monthly = pd.read_sql(monthly_query, engine)
monthly["month"] = pd.to_datetime(monthly["month"])
save_csv(monthly, "06_monthly_performance.csv")

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(monthly["month"], monthly["total_revenue"], marker="o")
ax.set_title("Evolução Mensal do Revenue", fontsize=18, weight="bold", loc="left")
ax.set_xlabel("")
ax.set_ylabel("Revenue")
ax.yaxis.set_major_formatter(FuncFormatter(money_mi_axis))
ax.grid(alpha=0.2)
fig.autofmt_xdate()
fig.tight_layout(rect=[0, 0.05, 1, 0.96])
finish_figure(fig, "07_monthly_revenue.png", latest_date)

growth_df = monthly.dropna(subset=["growth_pct"]).copy()

fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(growth_df["month"].dt.strftime("%b/%Y"), growth_df["growth_pct"])
ax.axhline(0, linewidth=1)
ax.set_title("Crescimento Month-over-Month", fontsize=18, weight="bold", loc="left")
ax.set_xlabel("")
ax.set_ylabel("Variação (%)")
ax.grid(axis="y", alpha=0.2)

for container in ax.containers:
    labels = [
        f"{bar.get_height():+.2f}%".replace(".", ",")
        for bar in container
    ]
    ax.bar_label(container, labels=labels, padding=4, fontsize=9)

fig.tight_layout(rect=[0, 0.05, 1, 0.96])
finish_figure(fig, "08_monthly_growth.png", latest_date)


# ============================================================
# DONE
# ============================================================

print("\nArquivos gerados em:")
print(OUTPUT_DIR)

for file_path in sorted(OUTPUT_DIR.iterdir()):
    if file_path.suffix.lower() in {".png", ".csv"}:
        print(f" - {file_path.name}")
engine.dispose()
