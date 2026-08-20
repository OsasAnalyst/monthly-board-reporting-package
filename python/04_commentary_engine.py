import argparse
from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path(r"C:/Users/user/Documents/monthly-board-reporting-package/data/processed")

SMALL_BUDGET_BASE_THRESHOLD = 2000

DATA_SETUP_DISCLAIMER = (
    "Note: budget for this simulated 2026 dataset was built from 2016-2017 "
    "same-month-prior-year growth rates (2-10% tiers), while the underlying "
    "'actuals' are real 2017-2018 Olist order data from a period of genuine "
    "marketplace hypergrowth. Large positive variances below reflect that "
    "mismatch in the data setup, not an actual outperformance story."
)

def load_variance(month_str: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"variance_{month_str}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No variance file for {month_str}")
    return pd.read_csv(path, sep=";")


def classify_driver(row) -> str:
    if row["status"] == "unbudgeted":
        return "unbudgeted"
 
    price = abs(row["price_effect"]) if not pd.isna(row["price_effect"]) else 0
    volume = abs(row["volume_effect"]) if not pd.isna(row["volume_effect"]) else 0
    total = price + volume
 
    if total == 0:
        return "none"
 
    price_share = price / total
    if price_share >= 0.65:
        return "price"
    elif price_share <= 0.35:
        return "volume"
    else:
        return "both"

def format_category(category: str) -> str:
    return category.replace("_", " ").title()


def generate_line(row) -> str:
    category_display = format_category(row["category"])
    abs_dollar = abs(row["revenue_variance"])
    direction = "beat" if row["revenue_variance"] > 0 else "missed"
 
    if row["status"] == "unbudgeted":
        return (
            f"{category_display} generated ${abs_dollar:,.0f} in revenue with no "
            f"budget baseline set for this category."
        )
 
    driver = classify_driver(row)
    if driver == "price":
        driver_text = "driven primarily by price - units sold at a different average price than planned, not a change in volume"
    elif driver == "volume":
        driver_text = "driven primarily by volume - a different number of units sold than planned, not a price change"
    elif driver == "both":
        driver_text = "driven by a mix of price and volume changes, in roughly similar measure"
    else:
        driver_text = "with no meaningful price or volume movement behind it"
 
    pct_text = f" ({abs(row['variance_pct']):.1f}%)" if not pd.isna(row["variance_pct"]) else ""
    line = f"{category_display} {direction} budget by ${abs_dollar:,.0f}{pct_text}, {driver_text}."
 
    if 0 < row["budget_revenue"] < SMALL_BUDGET_BASE_THRESHOLD:
        line += f" (Note: budget for this category was only ${row['budget_revenue']:,.0f}, so the percentage above is directionally noisy.)"
 
    return line
 
 
def run(month_str: str):
    df = load_variance(month_str)
 
    material_rows = df[df["material"]].copy()
    material_rows = material_rows.sort_values("revenue_variance", key=abs, ascending=False)
    material_rows["narrative"] = material_rows.apply(generate_line, axis=1)
 
    n_material = len(material_rows)
    n_total = len(df)
    n_other = n_total - n_material
 
    summary_line = (
        f"{n_material} of {n_total} categories moved materially against budget this month. "
        f"The remaining {n_other} categories were within normal range and are not called out individually."
    )
 
    # console output
    print(f"Commentary for {month_str}")
    print(DATA_SETUP_DISCLAIMER)
    print(f"\n{summary_line}\n")
    for _, row in material_rows.iterrows():
        print(f"- {row['narrative']}")
    print()
 
    # save
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"commentary_{month_str}.csv"
    output_cols = ["category", "revenue_variance", "variance_pct", "status", "narrative"]
    material_rows[output_cols].to_csv(out_path, sep=";", index=False)
    print(f"Saved: {out_path}\n")
 
    return material_rows, summary_line
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="Target month, e.g. 2026-07")
    args = parser.parse_args()
    run(args.month)