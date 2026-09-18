import csv
import random
import argparse
from pathlib import Path
from datetime import date, timedelta

parser = argparse.ArgumentParser()
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--rows", type=int, default=1_000_000)
parser.add_argument("--overwrite", action="store_true")
args = parser.parse_args()
if args.rows <= 0: parser.error("--rows deve ser positivo")
random.seed(args.seed)

# Preços do cenário sintético
product_prices = {
    1: 4.99,
    2: 6.99,
    3: 10.99,
    4: 7.99,
    5: 10.99,
    6: 6.49,
    7: 17.90,
    8: 7.49
}

# Nossas lojas já cadastradas
store_ids = [1, 2, 3, 4, 5]

start_date = date(2026, 1, 1)
end_date = date(2026, 9, 17)

total_days = (end_date - start_date).days

output_file = Path(__file__).resolve().parents[1] / "data/raw/sell_out.csv"
output_file.parent.mkdir(parents=True, exist_ok=True)
if output_file.exists() and not args.overwrite:
    raise SystemExit("Arquivo já existe. Use --overwrite apenas para regenerar a base.")

with open(output_file, "w", newline="", encoding="utf-8") as file:

    writer = csv.writer(file)

    # Cabeçalho
    writer.writerow([
        "sale_date",
        "store_id",
        "product_id",
        "quantity",
        "unit_price"
    ])

    # Gerar os registros sintéticos
    for _ in range(args.rows):

        product_id = random.choice(list(product_prices.keys()))
        store_id = random.choice(store_ids)

        sale_date = start_date + timedelta(
            days=random.randint(0, total_days)
        )

        quantity = random.randint(1, 15)

        unit_price = product_prices[product_id]

        writer.writerow([
            sale_date,
            store_id,
            product_id,
            quantity,
            unit_price
        ])

print(f"Arquivo {output_file} criado com {args.rows:,} registros; seed={args.seed}.")