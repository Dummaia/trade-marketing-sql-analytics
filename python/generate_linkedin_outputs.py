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
# CONFIGURAÇÃO
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "linkedin"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_NAME = os.getenv("PGDATABASE", "trade_marketing")
DB_USER = os.getenv("PGUSER", "postgres")


# ============================================================
# CONEXÃO
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

def br_int(value) -> str:
    return f"{int(round(float(value))):,}".replace(",", ".")


def br_decimal(value, decimals=2) -> str:
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def br_money_mi(value) -> str:
    return f"R$ {br_decimal(float(value) / 1_000_000, 2)} mi"


def axis_mi(value, _):
    return f"R$ {value / 1_000_000:.1f} mi".replace(".", ",")


def pct(value) -> str:
    return f"{float(value):.2f}%".replace(".", ",")


def clean_axes(ax, grid_axis="x"):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis=grid_axis, alpha=0.18)
    ax.set_axisbelow(True)


def add_footer(fig, latest_date):
    text = "Dados sintéticos • PostgreSQL + SQL + Python"
    if pd.notna(latest_date):
        text += f" • Base até {pd.Timestamp(latest_date).strftime('%d/%m/%Y')}"
    fig.text(0.02, 0.015, text, fontsize=9, alpha=0.65)


def save(fig, filename, latest_date):
    add_footer(fig, latest_date)
    fig.savefig(
        OUTPUT_DIR / filename,
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.25,
    )
    plt.close(fig)


# ============================================================
# METADADOS
# ============================================================

meta = pd.read_sql(
    """
    SELECT
        MIN(sale_date) AS min_sale_date,
        MAX(sale_date) AS max_sale_date
    FROM sell_out;
    """,
    engine,
)

min_date = pd.Timestamp(meta.loc[0, "min_sale_date"])
max_date = pd.Timestamp(meta.loc[0, "max_sale_date"])


# ============================================================
# 1. KPIs EXECUTIVOS
# ============================================================

executive = pd.read_sql(
    """
    SELECT
        COUNT(*) AS total_sales_records,
        SUM(quantity) AS total_units_sold,
        ROUND(SUM(quantity * unit_price), 2) AS total_revenue,
        ROUND(AVG(quantity), 2) AS avg_units_per_record
    FROM sell_out;
    """,
    engine,
)

if executive.loc[0, "total_sales_records"] == 0:
    raise SystemExit("A tabela sell_out está vazia. Execute a carga antes das análises.")

total_records = executive.loc[0, "total_sales_records"]
total_units = executive.loc[0, "total_units_sold"]
total_revenue = executive.loc[0, "total_revenue"]
avg_units = executive.loc[0, "avg_units_per_record"]


# ============================================================
# 2. PRODUTOS
# ============================================================

products = pd.read_sql(
    """
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
    """,
    engine,
)

products["total_revenue"] = products["total_revenue"].astype(float)
products["total_units_sold"] = products["total_units_sold"].astype(float)


# ============================================================
# 3. CLIENTES
# ============================================================

clients = pd.read_sql(
    """
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
    """,
    engine,
)

clients["total_revenue"] = clients["total_revenue"].astype(float)
clients["revenue_share_pct"] = clients["revenue_share_pct"].astype(float)


# ============================================================
# 4. RETAILERS
# ============================================================

retailers = pd.read_sql(
    """
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
    """,
    engine,
)

retailers["total_revenue"] = retailers["total_revenue"].astype(float)
retailers["avg_revenue_per_store"] = retailers["avg_revenue_per_store"].astype(float)


# ============================================================
# 5. PERFORMANCE MENSAL
# Exclui automaticamente o último mês quando ele está incompleto.
# ============================================================

monthly = pd.read_sql(
    """
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
    """,
    engine,
)

monthly["month"] = pd.to_datetime(monthly["month"])
monthly["total_revenue"] = monthly["total_revenue"].astype(float)
monthly["growth_pct"] = pd.to_numeric(monthly["growth_pct"])


# ============================================================
# INSIGHTS DINÂMICOS
# ============================================================

top_product = products.iloc[0]
top_client = clients.iloc[0]

growth_valid = monthly.dropna(subset=["growth_pct"])
best_growth = growth_valid.loc[growth_valid["growth_pct"].idxmax()] if not growth_valid.empty else None


# ============================================================
# VISUAL 1 — CAPA / EXECUTIVE OVERVIEW
# ============================================================

fig = plt.figure(figsize=(12, 6.75))

fig.text(0.05, 0.90, "Trade Marketing Analytics", fontsize=27, weight="bold")
fig.text(0.05, 0.84, "Sell-out & PDV Performance", fontsize=14)
fig.text(
    0.05, 0.78,
    f"Período analisado: {min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')}",
    fontsize=10,
    alpha=0.7,
)

cards = [
    (0.12, br_int(total_records), "Registros de Sell-out"),
    (0.38, br_int(total_units), "Unidades vendidas"),
    (0.65, br_money_mi(total_revenue), "Revenue total"),
    (0.88, br_decimal(avg_units, 2), "Unidades / registro"),
]

for x, value, label in cards:
    fig.text(x, 0.61, value, fontsize=23, weight="bold", ha="center")
    fig.text(x, 0.54, label, fontsize=10.5, ha="center")

fig.text(0.05, 0.39, "Principais insights", fontsize=15, weight="bold")

fig.text(
    0.06, 0.31,
    f"• {top_product['product_name']} liderou o revenue, com {br_money_mi(top_product['total_revenue'])}.",
    fontsize=11,
)
fig.text(
    0.06, 0.24,
    f"• {top_client['client_name']} concentrou {pct(top_client['revenue_share_pct'])} do revenue total.",
    fontsize=11,
)
fig.text(
    0.06, 0.17,
    (f"• Maior variação MoM entre meses completos: {pct(best_growth['growth_pct'])} em {best_growth['month'].strftime('%m/%Y')}." if best_growth is not None else "• MoM indisponível: são necessários meses consecutivos comparáveis."),
    fontsize=11,
)

plt.axis("off")
save(fig, "01_linkedin_executive_overview.png", max_date)


# ============================================================
# VISUAL 2 — REVENUE POR PRODUTO
# ============================================================

plot_df = products.sort_values("total_revenue", ascending=True)

fig, ax = plt.subplots(figsize=(12, 6.75))
ax.barh(plot_df["product_name"], plot_df["total_revenue"])
ax.set_title("Revenue por Produto", fontsize=20, weight="bold", loc="left", pad=32)
ax.text(
    0, 1.02,
    "Ranking acumulado de Sell-out por produto",
    transform=ax.transAxes,
    fontsize=11,
    alpha=0.7,
)
ax.set_xlabel("")
ax.set_ylabel("")
ax.xaxis.set_major_formatter(FuncFormatter(axis_mi))
clean_axes(ax)

for container in ax.containers:
    labels = [br_money_mi(bar.get_width()) for bar in container]
    ax.bar_label(container, labels=labels, padding=4, fontsize=9)

fig.tight_layout(rect=[0, 0.05, 1, 0.95])
save(fig, "02_linkedin_product_revenue.png", max_date)


# ============================================================
# VISUAL 3 — PARTICIPAÇÃO POR CLIENTE (DONUT)
# ============================================================

fig, ax = plt.subplots(figsize=(12, 6.75))

wedges, _ = ax.pie(
    clients["revenue_share_pct"],
    startangle=90,
    wedgeprops={"width": 0.38},
)

ax.set_title("Participação no Revenue por Cliente", fontsize=20, weight="bold", loc="left", pad=32)
ax.text(-1.25, 1.05, "Share do revenue total por cliente", fontsize=11, alpha=0.7)

legend_labels = [
    f"{row.client_name} — {pct(row.revenue_share_pct)}"
    for row in clients.itertuples()
]

ax.legend(
    wedges,
    legend_labels,
    loc="center left",
    bbox_to_anchor=(1.02, 0.5),
    frameon=False,
)

ax.text(0, 0.03, br_money_mi(total_revenue), ha="center", va="center", fontsize=19, weight="bold")
ax.text(0, -0.12, "Revenue total", ha="center", va="center", fontsize=10, alpha=0.7)

fig.tight_layout(rect=[0, 0.05, 0.88, 0.95])
save(fig, "03_linkedin_client_share.png", max_date)


# ============================================================
# VISUAL 4 — REVENUE MÉDIO POR PDV
# ============================================================

plot_df = retailers.sort_values("avg_revenue_per_store", ascending=False)

fig, ax = plt.subplots(figsize=(12, 6.75))
bars = ax.bar(plot_df["retailer_name"], plot_df["avg_revenue_per_store"])

ax.set_title("Revenue Médio por PDV", fontsize=20, weight="bold", loc="left", pad=32)
ax.text(
    0, 1.02,
    "Comparação por quantidade de lojas com vendas em cada retailer",
    transform=ax.transAxes,
    fontsize=11,
    alpha=0.7,
)
ax.set_xlabel("")
ax.set_ylabel("")
ax.yaxis.set_major_formatter(FuncFormatter(axis_mi))
clean_axes(ax, grid_axis="y")

labels = [br_money_mi(bar.get_height()) for bar in bars]
ax.bar_label(bars, labels=labels, padding=4, fontsize=10)

fig.tight_layout(rect=[0, 0.05, 1, 0.95])
save(fig, "04_linkedin_avg_revenue_per_pdv.png", max_date)


# ============================================================
# VISUAL 5 — EVOLUÇÃO MENSAL
# ============================================================

fig, ax = plt.subplots(figsize=(12, 6.75))

ax.plot(monthly["month"], monthly["total_revenue"], marker="o", linewidth=2)
ax.set_title("Evolução Mensal do Revenue", fontsize=20, weight="bold", loc="left", pad=32)
ax.text(
    0, 1.02,
    "Somente meses completos são considerados na série",
    transform=ax.transAxes,
    fontsize=11,
    alpha=0.7,
)
ax.set_xlabel("")
ax.set_ylabel("")
ax.yaxis.set_major_formatter(FuncFormatter(axis_mi))
clean_axes(ax, grid_axis="y")

for x, y in zip(monthly["month"], monthly["total_revenue"]):
    ax.annotate(
        br_money_mi(y),
        (x, y),
        textcoords="offset points",
        xytext=(0, 9),
        ha="center",
        fontsize=8.5,
    )

fig.autofmt_xdate()
fig.tight_layout(rect=[0, 0.05, 1, 0.95])
save(fig, "05_linkedin_monthly_revenue.png", max_date)


# ============================================================
# VISUAL 6 — CRESCIMENTO MoM
# ============================================================

growth_df = monthly.dropna(subset=["growth_pct"]).copy()

fig, ax = plt.subplots(figsize=(12, 6.75))
bars = ax.bar(growth_df["month"].dt.strftime("%b/%Y"), growth_df["growth_pct"])
ax.axhline(0, linewidth=1)

ax.set_title("Crescimento Month-over-Month", fontsize=20, weight="bold", loc="left", pad=32)
ax.text(
    0, 1.02,
    "Variação percentual do revenue em relação ao mês anterior",
    transform=ax.transAxes,
    fontsize=11,
    alpha=0.7,
)
ax.set_xlabel("")
ax.set_ylabel("Variação (%)")
clean_axes(ax, grid_axis="y")

labels = [f"{bar.get_height():+.2f}%".replace(".", ",") for bar in bars]
ax.bar_label(bars, labels=labels, padding=4, fontsize=9)

fig.tight_layout(rect=[0, 0.05, 1, 0.95])
save(fig, "06_linkedin_monthly_growth.png", max_date)


# ============================================================
# FINAL
# ============================================================

print("\nVisuais para LinkedIn gerados em:")
print(OUTPUT_DIR)

for file_path in sorted(OUTPUT_DIR.glob("*.png")):
    print(f" - {file_path.name}")


engine.dispose()
