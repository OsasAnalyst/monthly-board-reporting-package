import pandas as pd
import os


raw_path = r"C:/Users/user/Documents/monthly-board-reporting-package/data/raw/budget_assumptions.csv"
df = pd.read_csv(raw_path, sep=",")

month_map = {
    "2018-06": "2026-06",
    "2018-07": "2026-07",
    "2018-08": "2026-08"
}

output_base = r"C:/Users/user/Documents/monthly-board-reporting-package/data/incoming"

for source_month,target_month in month_map.items():
    month_df = df[df["month"] == source_month].copy()

    if month_df.empty:
        print(f"WARNING: no budget rows found for {source_month}")
        continue
    month_df["month"] = target_month

    out_folder = os.path.join(output_base, target_month)
    os.makedirs(out_folder, exist_ok=True)

    out_path = os.path.join(out_folder, "budget_assumptions.csv")
    month_df.to_csv(out_path, sep=',', index=False)
 
    print(f"{target_month}: {len(month_df)} budget rows written to {out_path}")
