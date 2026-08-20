import argparse
import sys
from pathlib import Path
import pandas as pd

EXPECTED_COLUMNS = ["month","category", "revenue", "units", "avg_price"]
CRITICAL_FIELDS = ["category", "revenue", "units"]
DATA_DIR = Path(r"C:\Users\user\Documents\monthly-board-reporting-package\data\incoming")
FILENAME = "monthly_actuals_by_category.csv"

# Helper function to turn "2026-07" into "2026-06", the prior month string
def get_prior_month(month_str: str) -> str:
    year, month = map(int, month_str.split("-"))
    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1
    return f"{year:04d}-{month:02d}"

# Load a month's file
def load_month_data(month_str: str):
    file_path = DATA_DIR / month_str / FILENAME

    if not file_path.exists():
        return None, False, f"File not found: {file_path}"

    df = pd.read_csv(file_path, sep=";")

    if df.empty:
        return None, False, f"File exists but has 0 rows: {file_path}"
    return df, True, f"Loaded {len(df)} rows from {file_path}"

# Individual checks - keeping it seperate

def check_required_columns(df, expected_cols):
    missing = set(expected_cols) - set(df.columns)
    if missing:
        return False, f"Missing columns: {sorted(missing)}"
    return True, "All expected columns present"

def check_nulls_in_critical_fields(df, fields):
    null_counts = df[fields].isnull().sum()
    bad_fields = null_counts[null_counts > 0]
    if not bad_fields.empty:
        detail = ", ".join(f"{col}={count}" for col, count in bad_fields.items())
        return False, f"Nulls found in critical fields: {detail}"
    return True, "No nulls in critical fields"

def check_duplicate_rows(df):
    dupes = df.duplicated(subset=["category", "month"], keep=False)
    if dupes.any():
        dup_categories = df.loc[dupes, "category"].unique().tolist()
        return False, f"Duplicate category+month rows found: {dup_categories}"
    return True, "No duplicate category+month rows"


def check_category_coverage(df, prior_df):
    """
    Warning-level check, not a hard fail - a category disappearing or
    appearing is worth flagging, but shouldn't by itself stop the pipeline.
    prior_df is None when there's no prior month to compare against.
    """
    if prior_df is None:
        return True, "No prior month available"
 
    current_categories = set(df["category"])
    prior_categories = set(prior_df["category"])
 
    disappeared = prior_categories - current_categories
    new_categories = current_categories - prior_categories
 
    messages = []
    if disappeared:
        messages.append(f"Categories missing vs prior month: {sorted(disappeared)}")
    if new_categories:
        messages.append(f"New categories not in prior month: {sorted(new_categories)}")
 
    if messages:
        return True, " | ".join(messages)  # still True — informational, not a failure
    return True, "Category list matches prior month"


# Runs every check, collects results, decides pass/fail
def validate_month(month_str: str):
    results = []
    critical_failure = False
 
    df, passed, message = load_month_data(month_str)
    results.append(("file_load", passed, message))
    if not passed:
        critical_failure = True
        df = None
 
    if df is not None:
        checks = [
            ("required_columns", check_required_columns(df, EXPECTED_COLUMNS)),
            ("nulls_in_critical_fields", check_nulls_in_critical_fields(df, CRITICAL_FIELDS)),
            ("duplicate_rows", check_duplicate_rows(df)),
        ]
        for name, (passed, message) in checks:
            results.append((name, passed, message))
            if not passed:
                critical_failure = True
 
        prior_month_str = get_prior_month(month_str)
        prior_df, prior_ok, _ = load_month_data(prior_month_str)
        if not prior_ok:
            prior_df = None
 
        passed, message = check_category_coverage(df, prior_df)
        results.append(("category_coverage", passed, message))
 
    return results, critical_failure, df

def print_summary(month_str, results,critical_failure):
    print(f"Validation results for {month_str}")
    for name, passed, message in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}: {message}")
    print("Overall", "FAILED" if critical_failure else "PASSED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="Target month, e.g. 2026-06")
    args = parser.parse_args()

    results, critical_failure, df = validate_month(args.month)
    print_summary(args.month, results, critical_failure)
 
    sys.exit(1 if critical_failure else 0)