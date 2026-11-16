
import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

# -----------------------------------------
# 1. Locate SignalBench data
# -----------------------------------------

PROJECT = Path(__file__).resolve().parents[1]

DB_FILE = PROJECT / "data/database/signalbench.db"
OUTPUT_DIR = PROJECT / "data/forecasts"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not DB_FILE.exists():
    raise SystemExit("Database missing. Run load_database.py first.")

# -----------------------------------------
# 2. Read historical data
# -----------------------------------------

with sqlite3.connect(DB_FILE) as connection:
    rows = connection.execute("""
        SELECT workload_date, records_processed
        FROM daily_workloads
        ORDER BY workload_date
    """).fetchall()

dates = [date.fromisoformat(row[0]) for row in rows]
values = [int(row[1]) for row in rows]

if len(values) < 35:
    raise SystemExit("At least 35 historical days are required.")

# Make sure historical days are consecutive
for previous, current in zip(dates, dates[1:]):
    if current - previous != timedelta(days=1):
        raise SystemExit("Historical dates are not consecutive.")

if any(value <= 0 for value in values):
    raise SystemExit("Historical workload must be positive.")

# -----------------------------------------
# 3. Define forecasting models
# -----------------------------------------

MODELS = ("previous_day", "previous_week")
HORIZON = 7
MIN_HISTORY = 28

def forecast_seven_days(history, model):
    simulated = history.copy()
    predictions = []

    for _ in range(HORIZON):

        if model == "previous_day":
            prediction = simulated[-1]

        elif model == "previous_week":
            prediction = simulated[-7]

        else:
            raise ValueError("Unknown model")

        predictions.append(prediction)

        # Later predictions may use earlier forecasts,
        # but never future actual observations.
        simulated.append(prediction)

    return predictions

# -----------------------------------------
# 4. Run rolling-origin simulations
# -----------------------------------------

results = []

for origin in range(
    MIN_HISTORY,
    len(values) - HORIZON + 1
):

    # Information available at this starting point
    history = values[:origin]
    origin_date = dates[origin - 1]

    for model in MODELS:

        predictions = forecast_seven_days(
            history,
            model,
        )

        for step, prediction in enumerate(
            predictions,
            start=1,
        ):

            target_index = origin + step - 1
            actual = values[target_index]
            target_date = dates[target_index]

            absolute_error = abs(actual - prediction)
            percentage_error = absolute_error / actual * 100

            results.append({
                "origin_date": origin_date.isoformat(),
                "target_date": target_date.isoformat(),
                "horizon": step,
                "model": model,
                "actual_records": actual,
                "predicted_records": prediction,
                "absolute_error": absolute_error,
                "absolute_percentage_error": percentage_error,
            })

# -----------------------------------------
# 5. Evaluate each forecasting horizon
# -----------------------------------------

summary = []

for model in MODELS:

    for horizon in range(1, HORIZON + 1):

        selected = [
            row for row in results
            if row["model"] == model
            and row["horizon"] == horizon
        ]

        mae = mean(
            row["absolute_error"] for row in selected
        )

        mape = mean(
            row["absolute_percentage_error"]
            for row in selected
        )

        summary.append({
            "model": model,
            "horizon": horizon,
            "evaluations": len(selected),
            "mae": round(mae, 2),
            "mape": round(mape, 2),
        })

# -----------------------------------------
# 6. Compare overall seven-day performance
# -----------------------------------------

overall_scores = {}

for model in MODELS:

    model_results = [
        row for row in results
        if row["model"] == model
    ]

    overall_scores[model] = {
        "mae": mean(
            row["absolute_error"]
            for row in model_results
        ),
        "mape": mean(
            row["absolute_percentage_error"]
            for row in model_results
        ),
    }

winner = min(
    MODELS,
    key=lambda model: overall_scores[model]["mae"]
)

# -----------------------------------------
# 7. Save detailed results
# -----------------------------------------

details_file = OUTPUT_DIR / "rolling_backtest.csv"

with details_file.open(
    "w", newline="", encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=list(results[0].keys()),
    )

    writer.writeheader()
    writer.writerows(results)

# -----------------------------------------
# 8. Save horizon-by-horizon results
# -----------------------------------------

summary_file = OUTPUT_DIR / "rolling_summary.csv"

with summary_file.open(
    "w", newline="", encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=list(summary[0].keys()),
    )

    writer.writeheader()
    writer.writerows(summary)

# -----------------------------------------
# 9. Display the evaluation report
# -----------------------------------------

origin_count = len(
    range(MIN_HISTORY, len(values) - HORIZON + 1)
)

print("\nSIGNALBENCH ROLLING BACKTEST")
print("---------------------------")

print(f"Historical days: {len(values)}")
print(f"Forecast horizon: {HORIZON} days")
print(f"Rolling origins: {origin_count}")
print(f"Total comparisons: {len(results)}")

print("\nSEVEN-DAY MODEL COMPARISON")

for model, scores in overall_scores.items():

    print(f"\nModel: {model}")
    print(f"MAE: {scores['mae']:,.2f} records")
    print(f"MAPE: {scores['mape']:.2f}%")

print(f"\nLowest overall MAE: {winner}")

print("\nFiles saved:")
print(details_file)
print(summary_file)

print("\nRESULT: PASS")
