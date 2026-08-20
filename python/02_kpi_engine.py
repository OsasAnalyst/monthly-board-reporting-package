import argparse
from pathlib import Path
import pandas as pd


DATA_DIR = Path(r"C:/Users/user/Documents/monthly-board-reporting-package/data/incoming")
PROCESSED_DIR = Path(r"C:/Users/user/Documents/monthly-board-reporting-package/data/processed")
FILENAME = "monthly_actuals_by_category.csv"


def get_prior_month(month_str: str) -> str:
    year, month = map(int, month_str.split("-"))
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    return f"{year:04d}-{month:02d}"


def load_month_data(month_str: str):
    file_path = DATA_DIR / month_str / FILENAME
    if not file_path.exists():
        return None
    return pd.read_csv(file_path, sep=";")


def calculate_month_totals(df: pd.DataFrame) -> dict:
    total_revenue = df["revenue"].sum()
    total_units = df["units"].sum()
    blended_avg_price = total_revenue / total_units if total_units else 0

    return {
        "total_revenue": total_revenue,
        "total_units": total_units,
        "blended_avg_price":blended_avg_price
    }


def calculate_total_growth(current_totals: dict, prior_totals):
    if prior_totals is None:
        return {"revenue_growth_pct": None, "units_growth_pct": None}

    def pct_change(current, prior):
        if prior == 0:
            return None
        return round((current - prior) / prior * 100, 2)

    return {
        "revenue_growth_pct": pct_change(current_totals["total_revenue"], prior_totals["total_revenue"]),
        "units_growth_pct": pct_change(current_totals["total_units"], prior_totals["total_units"]),
    }


def calculate_category_growth(df: pd.DataFrame, prior_df):
    """
    Returns a DataFrame with one row per category, comparing this month's
    revenue against the prior month's. Categories that only exist in one
    of the two months get revenue_growth_pct = None
    """
    current = df[["category", "revenue", "units"]].copy()
 
    if prior_df is None:
        current["prior_revenue"] = None
        current["revenue_growth_pct"] = None
        current["status"] = "no_prior_month"
        return current
 
    prior = prior_df[["category", "revenue", "units"]].copy()
    prior = prior.rename(columns={"revenue": "prior_revenue", "units": "prior_units"})
 
    # outer merge so categories that only exist in one month still show up,
    # instead of silently vanishing from the comparison
    merged = pd.merge(current, prior, on="category", how="outer")
 
    def compute_row(row):
        if pd.isna(row["revenue"]):
            return pd.Series({"revenue_growth_pct": None, "status": "dropped_this_month"})
        if pd.isna(row["prior_revenue"]):
            return pd.Series({"revenue_growth_pct": None, "status": "new_this_month"})
        if row["prior_revenue"] == 0:
            return pd.Series({"revenue_growth_pct": None, "status": "prior_zero"})
        growth = round((row["revenue"] - row["prior_revenue"]) / row["prior_revenue"] * 100, 2)
        return pd.Series({"revenue_growth_pct": growth, "status": "ok"})
 
    growth_cols = merged.apply(compute_row, axis=1)
    merged = pd.concat([merged, growth_cols], axis=1)
 
    return merged.sort_values("revenue_growth_pct", ascending=False, na_position="last")


def run(month_str: str):
    df = load_month_data(month_str)
    if df is None:
        raise FileNotFoundError(f"No data found for {month_str}")
 
    prior_month_str = get_prior_month(month_str)
    prior_df = load_month_data(prior_month_str)
 
    current_totals = calculate_month_totals(df)
    prior_totals = calculate_month_totals(prior_df) if prior_df is not None else None
    total_growth = calculate_total_growth(current_totals, prior_totals)
 
    category_growth = calculate_category_growth(df, prior_df)
 
    print(f"KPIs for {month_str}")
    print(f"Total revenue: {current_totals['total_revenue']:,.2f}")
    print(f"Total units: {current_totals['total_units']:,}")
    print(f"Blended avg price: {current_totals['blended_avg_price']:,.2f}")
    if total_growth["revenue_growth_pct"] is not None:
        print(f"Revenue growth MoM: {total_growth['revenue_growth_pct']}%")
        print(f"Units growth MoM: {total_growth['units_growth_pct']}%")
    else:
        print("Revenue/units growth MoM: N/A (no prior month)")
 
    print("Top 5 category revenue growth:")
    print(category_growth.head(5)[["category", "revenue", "revenue_growth_pct", "status"]].to_string(index=False))
 
    # save outputs
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
 
    kpi_summary = pd.DataFrame([{
        "month": month_str,
        **current_totals,
        **total_growth,
    }])
    kpi_summary_path = PROCESSED_DIR / f"kpi_summary_{month_str}.csv"
    kpi_summary.to_csv(kpi_summary_path, sep=";", index=False)
 
    category_growth_path = PROCESSED_DIR / f"category_growth_{month_str}.csv"
    category_growth.to_csv(category_growth_path, sep=";", index=False)
 
    print(f"Saved: {kpi_summary_path}")
    print(f"Saved: {category_growth_path}\n")
 
    return kpi_summary, category_growth

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="Target month, e.g. 2026-07")
    args = parser.parse_args()
    run(args.month)