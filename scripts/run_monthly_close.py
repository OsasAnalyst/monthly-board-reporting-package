import argparse
import importlib.util
import re
import sys
from pathlib import Path
 
PROJECT_ROOT = Path(r"C:/Users/user/Documents/monthly-board-reporting-package")
PYTHON_DIR = PROJECT_ROOT / "python"
INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"
 
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def load_module(filename: str):
    """
    Loads a script from the python/ folder by file path, bypassing the
    'can't import a name starting with a digit' restriction. Returns the
    loaded module so its functions can be called directly.
    """
    file_path = PYTHON_DIR / filename
    module_name = filename.replace(".py", "").replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_available_months():
    """
    Looks at actual folder names under data/incoming/ instead of assuming
    which months exist. Only keeps folders shaped like YYYY-MM.
    """
    months = [p.name for p in INCOMING_DIR.iterdir() if p.is_dir() and MONTH_PATTERN.match(p.name)]
    return sorted(months)


def run_month(month_str: str) -> bool:
    """
    Runs all 6 steps for one month, in order, stopping immediately if a
    step fails. Returns True if the whole month closed successfully.
    """
    print(f"\n{'=' * 60}")
    print(f"CLOSING {month_str}")
    print(f"{'=' * 60}")
 
    # Step 1: Validation
    validation = load_module("01_data_validation.py")
    results, critical_failure, df = validation.validate_month(month_str)
    validation.print_summary(month_str, results, critical_failure)
    if critical_failure:
        print(f"STOPPED: {month_str} failed validation. Fix the data and re-run.")
        return False
 
    # Step 2: KPIs
    kpi_engine = load_module("02_kpi_engine.py")
    kpi_engine.run(month_str)
 
    # Step 3: Variance
    variance_engine = load_module("03_variance_engine.py")
    variance_engine.run(month_str)
 
    # Step 4: Commentary
    commentary_engine = load_module("04_commentary_engine.py")
    commentary_engine.run(month_str)
 
    # Step 5: Forecast
    forecast = load_module("05_forecast.py")
    forecast.run(month_str)
 
    # Step 6: Report
    report_builder = load_module("06_report_builder.py")
    report_builder.run(month_str)
 
    print(f"{month_str} CLOSED SUCCESSFULLY")
    return True


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--month", help="Close a single month, e.g. 2026-08")
    group.add_argument("--all", action="store_true", help="Close every month found in data/incoming/")
    args = parser.parse_args()
 
    if args.all:
        months = discover_available_months()
        if not months:
            print("No month folders found under data/incoming/")
            sys.exit(1)
 
        print(f"Found {len(months)} month(s): {', '.join(months)}")
        results = {}
        for month_str in months:
            results[month_str] = run_month(month_str)
 
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        for month_str, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"  {month_str}: {status}")
 
        if not all(results.values()):
            sys.exit(1)
 
    else:
        success = run_month(args.month)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()