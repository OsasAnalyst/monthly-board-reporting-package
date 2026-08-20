# Automated Monthly Board Reporting Package Generator

I built this project to automate the part of FP&A that eats the most time every month and adds the least analytical value: pulling actuals, checking them against budget, writing the commentary, updating the forecast, and building the deck. None of that work requires judgment once the underlying analysis is done. It just needs to happen the same way, correctly, every single month. This tool does the whole cycle in one command and produces a board-ready PowerPoint deck at the end of it.

## Why This Matters

A monthly board pack is usually assembled by hand: pull the numbers, check them against last month's file for anything that looks wrong, calculate variance, decide what's worth commenting on, write that commentary, and format all of it into slides. Every step is a place for a stale number, a copy-paste error, or a category that quietly stopped reconciling to slip through. None of that is a good use of a finance team's time in a process that repeats on a fixed monthly schedule.

This tool treats the monthly close like a pipeline instead of a manual ritual. Data gets validated before anything downstream runs on it. Variance and commentary follow the same rules every month, so nothing depends on who's writing the deck that week. The output is consistent by construction, not by careful checking after the fact.

## Data Source and Setup

The actuals and budget framework are reused from the budget vs actual variance project in this same portfolio (Project 4), which is built on real Olist Brazilian e-commerce data. I want to be upfront about exactly how the "monthly drops" in this project work, since the dates are simulated in a specific way.

The underlying transaction data is real: June, July, and August 2018 from the Olist dataset. To demonstrate what a live monthly close looks like, I relabeled those three months to June, July, and August 2026 and split them into separate incoming folders, so the pipeline behaves exactly as it would if a new file landed each month. The budget baseline for those months uses the same same-month-prior-year methodology documented in Project 4 (2016-2017 growth rates applied to 2017-2018 style baselines). The result is a real mismatch between a hypergrowth-era marketplace and a conservative flat-growth budget, which shows up as consistently large positive variances in the output. That's a known artifact of the data setup, not a real outperformance story, and the tool says so directly in every commentary section it generates.

## Approach

The pipeline runs as six scripts, called in sequence by one orchestrator:

1. **Data validation** checks that each month's file exists, has rows, has every expected column, has no nulls in category, revenue, or units, and has no duplicate category-month rows. It also compares this month's category list against last month's as an informational check, flagging categories that disappeared or showed up new. Any of the first four checks failing stops that month's close before anything else runs. The category comparison is informational only, since a category legitimately dropping out or appearing is normal and shouldn't block a close.

2. **KPI engine** computes total revenue, total units, blended average price, month-over-month growth, and a category-level revenue growth table.

3. **Variance engine** compares actual to budget using Price-Volume-Mix analysis, the same framework as Project 4. Price effect and volume effect are calculated per category and tie out exactly to the dollar variance. Categories with no budget baseline are flagged separately as unbudgeted rather than forced into a PVM split that doesn't apply to them.

4. **Commentary engine** writes a plain-language line for every category that clears a materiality threshold, classifies whether the move was driven by price, volume, or a mix of both, and adds a caveat when a percentage move is calculated against a very small budget base. Categories that don't clear the threshold are counted but not called out individually, so the commentary stays readable instead of listing fifty lines nobody will read.

5. **Forecast** produces a trailing-average rolling revenue and unit forecast for the next month and backtests that method against every month with enough history to check it, so the forecast comes with a stated accuracy track record instead of just a number.

6. **Report builder** assembles all of it into a six-slide PowerPoint deck: title, financial summary, KPI dashboard with a revenue chart, variance highlights table, commentary, and outlook.

## Key Design Decisions

**Validation is a hard gate, not a suggestion.** File existence, schema, nulls, and duplicates are pass or fail. If any of them fail, that month's close stops before KPIs or variance run on bad data. Category coverage changes are logged but never block the close, since new and dropped categories are a normal part of a real business, not a data quality problem.

**Materiality thresholds are dual, not single.** A revenue variance only gets called out in commentary if it clears both a dollar threshold ($5,000) and a percentage threshold (5 percent) at the same time, with one exception: unbudgeted categories are flagged on the dollar threshold alone, since a percentage against a zero budget doesn't mean anything. This keeps the commentary focused on what a board would actually want to hear about, not every line that moved at all.

**Small budget bases get a caveat, not a suppression.** When a category's budget is under $2,000, its variance percentage can look enormous even on a modest dollar move. Rather than hide these lines, the commentary engine flags them with a note that the percentage is directionally noisy, so the reader isn't misled without losing the line entirely.

**The forecast is trailing-average, not a fitted model.** I chose a simple 3-month trailing average over something more sophisticated because the goal here is a defensible, explainable rolling outlook, not a black box. Every forecast the tool produces comes with a backtest showing how that same method would have performed against the months it already knows the answer to.

**No SQL layer in this project, by design.** Earlier drafts of this project's structure included a SQL aggregation step, but I dropped it. The real, functional SQL layer demonstrating that skill already exists in Project 4, and this project's actual differentiator is the automation pipeline itself. A SQL file that isn't wired into anything would have been padding, not range.

**No LLM-generated commentary.** Every line of narrative in the deck comes from rule-based logic in `04_commentary_engine.py`, not a language model call. The commentary is deterministic: the same data always produces the same wording, which matters for something a finance team would actually want to trust and audit.

## Project Structure

```
monthly-board-reporting-package/
├── README.md
├── data/
│   ├── raw/
│   │   ├── monthly_actuals_by_category.csv
│   │   └── budget_assumptions.csv
│   ├── incoming/
│   │   ├── 2026-06/
│   │   ├── 2026-07/
│   │   └── 2026-08/
│   └── processed/
├── python/
│   ├── 01_data_validation.py
│   ├── 02_kpi_engine.py
│   ├── 03_variance_engine.py
│   ├── 04_commentary_engine.py
│   ├── 05_forecast.py
│   └── 06_report_builder.py
├── output/
│   ├── 2026-06/
│   ├── 2026-07/
│   └── 2026-08/
└── scripts/
    ├── prepare_incoming_drops.py
    ├── prepare_budget_drops.py
    └── run_monthly_close.py
```

## How the Pieces Fit Together

`scripts/run_monthly_close.py` is the single entry point. It discovers every month folder under `data/incoming/`, then runs all six pipeline scripts against each one in order, stopping that month immediately if validation fails. It can close a single month with `--month` or every available month at once with `--all`. Each script writes its output to `data/processed/` as the pipeline moves forward, and the final step writes a finished `.pptx` deck to `output/{month}/`.

`prepare_incoming_drops.py` and `prepare_budget_drops.py` are one-time setup scripts, not part of the pipeline itself. They split the raw historical file into the three simulated monthly drops described above. A real deployment would replace these with an actual monthly data feed; the pipeline scripts themselves don't know or care where the file came from.

## Key Outputs

Running `python scripts/run_monthly_close.py --all` against the three simulated months produced three complete board decks and surfaced real findings worth reading, not just clean output:

**June 2026** was the largest variance month: actual revenue of $856,078 against a budget of $441,279, a total variance of $414,798, driven overwhelmingly by volume ($421,921) rather than price. 20 of 65 categories were flagged.

**July 2026** flagged the most categories of the three months (23 of 67), with a total variance of $365,826 split more evenly between price ($39,720) and volume ($300,461).

**August 2026** was the cleanest month of the three: 18 of 66 categories flagged, and the computers category flipped from generating unbudgeted revenue in June to a real, budgeted variance of -$26,929 by August, once its budget coverage caught up. That kind of shift is exactly the sort of thing a monthly close process should catch and explain, not just report.

The rolling forecast's own accuracy held up reasonably well across the demo: its July forecast was off by +1.4 percent and its August forecast by -2.7 percent, both against a 2-3 month trailing average with no tuning.

## Future Work

This version proves the automation pipeline end to end on three months of data. If I were taking this into a real engagement, the next steps would be:

Connecting the validation and KPI layers to a real data feed instead of pre-split simulated drops, so the pipeline runs against whatever lands in the folder on its own schedule.

Pulling the hardcoded materiality thresholds and file paths out of each script and into a single `config/reporting_config.yaml`, so thresholds can be adjusted without touching code.

Extending the forecast beyond a trailing average once there's enough real history to justify something more sophisticated, while keeping the backtest-first approach so any new method still has to prove itself against known months before it's trusted.

Adding a template-based slide layer so the deck's visual design can be swapped without touching `06_report_builder.py`.

## Getting Started

1. Clone the repository.
2. Place the raw actuals and budget files in `data/raw/`.
3. Run `scripts/prepare_incoming_drops.py` and `scripts/prepare_budget_drops.py` once to generate the simulated monthly folders under `data/incoming/`.
4. Run the full close for every available month:

```
python scripts/run_monthly_close.py --all
```

Or close a single month:

```
python scripts/run_monthly_close.py --month 2026-08
```

Finished decks land in `output/{month}/board_package_{month}.pptx`.

**Dependencies:** Python 3, pandas, numpy, python-pptx, argparse (standard library).

## Output Deliverable

The final output of each monthly run is `output/{month}/board_package_{month}.pptx`, a six-slide deck covering the financial summary, KPI dashboard, variance highlights, commentary, and forward outlook, generated automatically from validated data with no manual formatting step in between.

## Contact

**Osaretin Idiagbonmwen**
Email: idiagbonmwenosaretin@gmail.com
LinkedIn: https://www.linkedin.com/in/osaretin-idiagbonmwen-33ab85339/
