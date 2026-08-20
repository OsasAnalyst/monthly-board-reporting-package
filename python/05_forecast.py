import argparse
from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path(r"C:/Users/user/Documents/monthly-board-reporting-package/data/processed")

# How many trailing months to average.
WINDOW = 3


def get_next_month(month_str: str) -> str:
    year, month = map(int, month_str.split("-"))
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
    return f"{year:04d}-{month:02d}"


def discover_available_months(up_to_month: str):
    months = []
    for path in PROCESSED_DIR.glob("kpi_summary_*.csv"):
        month_str = path.stem.replace("kpi_summary_", "")
        if month_str <= up_to_month:
            months.append(month_str)
    return sorted(months)


def load_kpi_summary(month_str: str) -> dict:
    path = PROCESSED_DIR / f"kpi_summary_{month_str}.csv"
    df = pd.read_csv(path, sep=";")
    row = df.iloc[0]
    return {
        "total_revenue": row["total_revenue"],
        "total_units": row["total_units"],
    }

def trailing_average(values: list, window: int) -> float:
    """Mean of the last `window` values, or all of them if few exist."""
    recent = values[-window:]
    return sum(recent) / len(recent)


def run(month_str: str):
    available_months = discover_available_months(month_str)
    if not available_months:
        raise FileNotFoundError(f"No kpi_summary files found up to {month_str}")
 
    history = [load_kpi_summary(m) for m in available_months]
    revenues = [h["total_revenue"] for h in history]
    units = [h["total_units"] for h in history]
 
    # Backtest - how would this method have done on months we already know
    backtest_rows = []
    for i in range(1, len(available_months)):
        # Only use months before this one.
        forecast_revenue = trailing_average(revenues[:i], WINDOW)
        actual_revenue = revenues[i]
        error_pct = round((actual_revenue - forecast_revenue) / forecast_revenue * 100, 1) if forecast_revenue else None
 
        backtest_rows.append({
            "month": available_months[i],
            "type": "backtest",
            "actual_revenue": round(actual_revenue, 2),
            "forecast_revenue": round(forecast_revenue, 2),
            "error_pct": error_pct,
        })
 
    # Forward forecast - project the next month using what's available
    forecast_revenue = trailing_average(revenues, WINDOW)
    forecast_units = trailing_average(units, WINDOW)
    forecast_avg_price = forecast_revenue / forecast_units if forecast_units else 0
    next_month = get_next_month(month_str)
 
    forward_row = {
        "month": next_month,
        "type": "forward_forecast",
        "actual_revenue": None,
        "forecast_revenue": round(forecast_revenue, 2),
        "error_pct": None,
    }
 
    # console output
    months_used = min(WINDOW, len(available_months))
    print(f"Forecast as of {month_str} ({len(available_months)} month(s) of history available)")
 
    if backtest_rows:
        print("Backtest (forecast vs what actually happened):")
        for row in backtest_rows:
            print(f" {row['month']}: forecast ${row['forecast_revenue']:,.0f} vs actual ${row['actual_revenue']:,.0f}  ({row['error_pct']:+.1f}% error)")
    else:
        print("No backtest possible yet - only one month of history exists.")
 
    print(f"Forward forecast for {next_month} (trailing {months_used}-month average):")
    print(f"Revenue: ${forecast_revenue:,.2f}")
    print(f"Units: {forecast_units:,.0f}")
    print(f"Blended avg price: ${forecast_avg_price:,.2f}")
 
    if len(available_months) < WINDOW:
        print(f"Caution: only {len(available_months)} month(s) of history available "
              f"(target window is {WINDOW})")
 
    # save
    all_rows = backtest_rows + [forward_row]
    out_df = pd.DataFrame(all_rows)
    out_path = PROCESSED_DIR / f"forecast_{month_str}.csv"
    out_df.to_csv(out_path, sep=";", index=False)
    print(f"Saved: {out_path}\n")
 
    return out_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="Most recently closed month, e.g. 2026-08")
    args = parser.parse_args()
    run(args.month)