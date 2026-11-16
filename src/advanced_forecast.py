
import csv
import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median

# -----------------------------------------
# 1. Configuration
# -----------------------------------------

PROJECT = Path(__file__).resolve().parents[1]

DB_FILE = PROJECT / "data/database/signalbench.db"
OUTPUT_DIR = PROJECT / "data/forecasts"

HORIZON = 7
MIN_HISTORY = 28

MODELS = (
    "previous_day",
    "previous_week",
    "weekday_median",
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------
# 2. Read historical workload data
# -----------------------------------------

if not DB_FILE.exists():
    raise SystemExit("Database missing. Run load_database.py.")

with sqlite3.connect(DB_FILE) as connection:
    rows = connection.execute("""
        SELECT workload_date, records_processed
        FROM daily_workloads
        ORDER BY workload_date
    """).fetchall()

dates = [date.fromisoformat(row[0]) for row in rows]
values = [int(row[1]) for row in rows]

if len(values) < MIN_HISTORY + HORIZON:
    raise SystemExit("Not enough history for backtesting.")

if any(value <= 0 for value in values):
    raise SystemExit("Workload must contain positive values.")

for old, new in zip(dates, dates[1:]):
    if new - old != timedelta(days=1):
        raise SystemExit("Historical dates must be consecutive.")

# -----------------------------------------
# 3. Define three forecasting methods
# -----------------------------------------

def forecast_values(history, model, days=7):

    simulated = list(history)
    predictions = []

    for _ in range(days):

        if model == "previous_day":
            prediction = simulated[-1]

        elif model == "previous_week":
            prediction = simulated[-7]

        elif model == "weekday_median":
            last_four_matching_weekdays = [
                simulated[-7 * week]
                for week in range(1, 5)
            ]

            prediction = round(
                median(last_four_matching_weekdays)
            )

        else:
            raise ValueError(f"Unknown model: {model}")

        predictions.append(prediction)
        simulated.append(prediction)

    return predictions

# -----------------------------------------
# 4. Seven-day rolling backtest
# -----------------------------------------

backtest = []

for origin in range(
    MIN_HISTORY,
    len(values) - HORIZON + 1
):

    history = values[:origin]
    origin_date = dates[origin - 1]

    for model in MODELS:

        predictions = forecast_values(
            history,
            model,
            HORIZON,
        )

        for horizon, predicted in enumerate(
            predictions, start=1
        ):

            target_index = origin + horizon - 1
            actual = values[target_index]

            error = abs(actual - predicted)

            backtest.append({
                "origin_date": origin_date.isoformat(),
                "target_date": dates[target_index].isoformat(),
                "horizon": horizon,
                "model": model,
                "actual_records": actual,
                "predicted_records": predicted,
                "absolute_error": error,
                "absolute_percentage_error": error / actual * 100,
            })

# -----------------------------------------
# 5. Compare the three models
# -----------------------------------------

scores = []

for model in MODELS:

    selected = [
        row for row in backtest
        if row["model"] == model
    ]

    scores.append({
        "model": model,
        "evaluations": len(selected),
        "mae": mean(
            row["absolute_error"] for row in selected
        ),
        "mape": mean(
            row["absolute_percentage_error"]
            for row in selected
        ),
    })

# Lower MAE is better; MAPE breaks any tie
scores.sort(key=lambda row: (row["mae"], row["mape"]))

winning_model = scores[0]["model"]

# -----------------------------------------
# 6. Create historical error bands
# -----------------------------------------

def historical_p90(errors):
    ordered = sorted(errors)

    # Nearest-rank empirical 90th percentile
    rank = math.ceil(0.90 * len(ordered))

    return ordered[rank - 1]

# Each day-ahead horizon gets its own error estimate
horizon_summary = []

for model in MODELS:

    for horizon in range(1, HORIZON + 1):

        selected = [
            row for row in backtest
            if row["model"] == model
            and row["horizon"] == horizon
        ]

        errors = [
            row["absolute_error"] for row in selected
        ]

        horizon_summary.append({
            "model": model,
            "horizon": horizon,
            "mae": mean(errors),
            "historical_error_p90": historical_p90(errors),
        })

# -----------------------------------------
# 7. Generate seven future predictions
# -----------------------------------------

future_values = forecast_values(
    values,
    winning_model,
    HORIZON,
)

future_forecasts = []

for horizon, predicted in enumerate(
    future_values, start=1
):

    error_band = next(
        row["historical_error_p90"]
        for row in horizon_summary
        if row["model"] == winning_model
        and row["horizon"] == horizon
    )

    forecast_date = dates[-1] + timedelta(days=horizon)

    future_forecasts.append({
        "forecast_date": forecast_date.isoformat(),
        "horizon": horizon,
        "model": winning_model,
        "predicted_records": predicted,
        "lower_bound": max(0, predicted - error_band),
        "upper_bound": predicted + error_band,
        "historical_error_p90": error_band,
    })

# -----------------------------------------
# 8. Save CSV files
# -----------------------------------------

def save_csv(filename, records):

    destination = OUTPUT_DIR / filename

    with destination.open(
        "w", newline="", encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys()),
        )

        writer.writeheader()
        writer.writerows(records)

    return destination

saved_files = [
    save_csv("advanced_backtest.csv", backtest),
    save_csv("advanced_scores.csv", scores),
    save_csv("advanced_horizons.csv", horizon_summary),
    save_csv("advanced_next_7_days.csv", future_forecasts),
]

# -----------------------------------------
# 9. Print results
# -----------------------------------------

print("\nSIGNALBENCH ADVANCED FORECASTING")
print("--------------------------------")

print(f"Historical days: {len(values)}")
print(f"Rolling origins: {len(set(r['origin_date'] for r in backtest))}")
print(f"Backtest comparisons: {len(backtest)}")

print("\nTHREE-MODEL COMPARISON")

for score in scores:
    print(f"\nModel: {score['model']}")
    print(f"MAE: {score['mae']:,.2f} records")
    print(f"MAPE: {score['mape']:.2f}%")

print(f"\nSelected model: {winning_model}")

print("\nSEVEN-DAY FORECAST WITH ERROR BANDS")

for row in future_forecasts:
    print(
        f"{row['forecast_date']} | "
        f"{row['predicted_records']:,} records | "
        f"Range: {row['lower_bound']:,} "
        f"to {row['upper_bound']:,}"
    )

print("\nFiles saved:")
for path in saved_files:
    print(path)

print("\nRESULT: PASS")
