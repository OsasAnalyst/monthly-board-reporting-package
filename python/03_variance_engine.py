import argparse
from pathlib import Path
import pandas as pd

DATA_DIR = Path(r"C:/Users/user/Documents/monthly-board-reporting-package/data/incoming")
PROCESSED_DIR = Path(r"C:/Users/user/Documents/monthly-board-reporting-package/data/processed")

MATERIALITY_DOLLAR = 5000
MATERIALITY_PCT = 5

def load_actuals(month_str: str):
    path = DATA_DIR / month_str / "monthly_actuals_by_category.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, sep=";")
    return df[["category", "revenue", "units", "avg_price"]]

def load_budget(month_str: str):
    path = DATA_DIR / month_str / "budget_assumptions.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, sep=",")
    return df[["category", "budget_revenue", "budget_units", "budget_avg_price"]]


def build_variance_table(actual_df: pd.DataFrame, budget_df: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(actual_df, budget_df, on="category", how="outer")
 
    def classify(row):
        if pd.isna(row["budget_revenue"]):
            return "unbudgeted"
        if pd.isna(row["revenue"]):
            return "budgeted_no_actual"
        return "ok"
 
    merged["status"] = merged.apply(classify, axis=1)
 
    # Fill missing numeric values with 0

    numeric_cols = ["revenue", "units", "avg_price", "budget_revenue", "budget_units", "budget_avg_price"]
    merged[numeric_cols] = merged[numeric_cols].fillna(0)
 
    def compute_effects(row):
        if row["status"] == "unbudgeted":
            # No budget price/units to compare against - the entire actual
            # revenue is the variance, with no price/volume split possible.
            variance = row["revenue"]
            return pd.Series({
                "revenue_variance": variance,
                "variance_pct": None,
                "price_effect": None,
                "volume_effect": None,
                "unbudgeted_effect": variance,
            })
 
        # price_effect + volume_effect always equals revenue_variance
        # exactly, not approximately, when both sides have real numbers.
        variance = row["revenue"] - row["budget_revenue"]
        price_effect = (row["avg_price"] - row["budget_avg_price"]) * row["units"]
        volume_effect = (row["units"] - row["budget_units"]) * row["budget_avg_price"]
        variance_pct = round(variance / row["budget_revenue"] * 100, 2) if row["budget_revenue"] else None
 
        return pd.Series({
            "revenue_variance": round(variance, 2),
            "variance_pct": variance_pct,
            "price_effect": round(price_effect, 2),
            "volume_effect": round(volume_effect, 2),
            "unbudgeted_effect": 0,
        })
 
    effect_cols = merged.apply(compute_effects, axis=1)
    merged = pd.concat([merged, effect_cols], axis=1)
 
    def flag_material(row):
        if row["status"] == "unbudgeted":
            return abs(row["revenue_variance"]) >= MATERIALITY_DOLLAR
        pct_ok = row["variance_pct"] is not None and abs(row["variance_pct"]) >= MATERIALITY_PCT
        dollar_ok = abs(row["revenue_variance"]) >= MATERIALITY_DOLLAR
        return dollar_ok and pct_ok
 
    merged["material"] = merged.apply(flag_material, axis=1)
 
    return merged.sort_values("revenue_variance", key=abs, ascending=False)


def run(month_str: str):
    actual_df = load_actuals(month_str)
    budget_df = load_budget(month_str)
 
    if actual_df is None:
        raise FileNotFoundError(f"No actuals found for {month_str}")
    if budget_df is None:
        raise FileNotFoundError(f"No budget found for {month_str}")
 
    variance_table = build_variance_table(actual_df, budget_df)
 
    # sanity check
    total_actual = variance_table["revenue"].sum()
    total_budget = variance_table["budget_revenue"].sum()
    total_variance = total_actual - total_budget
    total_price_effect = variance_table["price_effect"].fillna(0).sum()
    total_volume_effect = variance_table["volume_effect"].fillna(0).sum()
    total_unbudgeted_effect = variance_table["unbudgeted_effect"].sum()
 
    print(f"Variance for {month_str}")
    print(f"Total actual revenue: {total_actual:,.2f}")
    print(f"Total budget revenue: {total_budget:,.2f}")
    print(f"Total variance: {total_variance:,.2f}")
    print(f"Price effect: {total_price_effect:,.2f}")
    print(f"Volume effect: {total_volume_effect:,.2f}")
    print(f"Unbudgeted effect: {total_unbudgeted_effect:,.2f}")
   
    check = total_price_effect + total_volume_effect + total_unbudgeted_effect
    print(f"Check matches variance {check:,.2f}")
 
    material_rows = variance_table[variance_table["material"]]
    print(f"{len(material_rows)} material variance flagged (>= ${MATERIALITY_DOLLAR} AND >= {MATERIALITY_PCT}%, or unbudgeted >= ${MATERIALITY_DOLLAR}):")
    if not material_rows.empty:
        print(material_rows[["category", "revenue", "budget_revenue", "revenue_variance", "variance_pct", "status"]].to_string(index=False))
    else:
        print("(none)")
 
    # save
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"variance_{month_str}.csv"
    variance_table.to_csv(out_path, sep=";", index=False)
    print(f"Saved: {out_path}")
 
    return variance_table

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="Target month, e.g. 2026-07")
    args = parser.parse_args()
    run(args.month)