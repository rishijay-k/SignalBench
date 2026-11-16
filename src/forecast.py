
import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

# -----------------------------------
# STEP 1: Locate the project database
# -----------------------------------

PROJECT = Path(__file__).resolve().parents[1]
DB_FILE = PROJECT / "data" / "database" / "signalbench.db"
OUTPUT_DIR = PROJECT / "data" / "forecasts"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not DB_FILE.exists():
    raise SystemExit("Database missing. Run load_database.py first.")

# -----------------------------------
# STEP 2: Read historical SQL data
# -----------------------------------

connection = sqlite3.connect(DB_FILE)

try:
    rows = connection.execute("""
        SELECT workload_date, records_processed
        FROM daily_workloads
        ORDER BY workload_date
    """).fetchall()
finally:
    connection.close()

if len(rows) < 21:
    raise SystemExit("At least 21 daily records are required.")

dates = [date.fromisoformat(row[0]) for row in rows]
values = [row[1] for row in rows]

# -----------------------------------
# STEP 3: Define two forecasting models
# -----------------------------------

def predict(model_name, history):
    if model_name == "previous_day":
        return history[-1]

    if model_name == "previous_week":
        return history[-7]

    raise ValueError("Unknown forecasting model")


# -----------------------------------
# STEP 4: Backtest the final 14 days
# -----------------------------------

test_days = 14
backtest_results = []

for index in range(len(values) - test_days, len(values)):

    # Only use data known before this date
    history = values[:index]

    actual = values[index]

    previous_day_prediction = predict(
        "previous_day", history
    )

    previous_week_prediction = predict(
        "previous_week", history
    )

    backtest_results.append({
        "date": dates[index].isoformat(),
        "actual_records": actual,
        "predicted_previous_day": previous_day_prediction,
        "predicted_previous_week": previous_week_prediction,
    })

# -----------------------------------
# STEP 5: Calculate forecasting errors
# -----------------------------------

model_columns = {
    "previous_day": "predicted_previous_day",
    "previous_week": "predicted_previous_week",
}

scores = {}

for model_name, column in model_columns.items():

    absolute_errors = [
        abs(row["actual_records"] - row[column])
        for row in backtest_results
    ]

    mae = sum(absolute_errors) / len(absolute_errors)

    mape = (
        sum(
            abs(row["actual_records"] - row[column])
            / row["actual_records"]
            for row in backtest_results
        )
        / len(backtest_results)
        * 100
    )

    scores[model_name] = {
        "mae": mae,
        "mape": mape,
    }

# Choose the model with the lowest MAE
winning_model = min(
    scores,
    key=lambda name: scores[name]["mae"]
)

# -----------------------------------
# STEP 6: Predict the next seven days
# -----------------------------------

future_history = values.copy()
future_forecasts = []

for day_number in range(1, 8):

    future_date = dates[-1] + timedelta(days=day_number)

    prediction = predict(
        winning_model,
        future_history
    )

    future_forecasts.append({
        "forecast_date": future_date.isoformat(),
        "predicted_records": prediction,
        "model": winning_model,
    })

    # Reuse predictions when forecasting further ahead
    future_history.append(prediction)

# -----------------------------------
# STEP 7: Save the backtesting results
# -----------------------------------

backtest_file = OUTPUT_DIR / "backtest_results.csv"

with backtest_file.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "date",
            "actual_records",
            "predicted_previous_day",
            "predicted_previous_week",
        ],
    )

    writer.writeheader()
    writer.writerows(backtest_results)

# -----------------------------------
# STEP 8: Save future predictions
# -----------------------------------

forecast_file = OUTPUT_DIR / "next_7_days.csv"

with forecast_file.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "forecast_date",
            "predicted_records",
            "model",
        ],
    )

    writer.writeheader()
    writer.writerows(future_forecasts)

# -----------------------------------
# STEP 9: Display the results
# -----------------------------------

print("\nSIGNALBENCH FORECASTING ENGINE")
print("------------------------------")
print(f"Historical records: {len(values)}")
print(f"Backtest days: {test_days}")

print("\nMODEL COMPARISON")

for model_name, metrics in scores.items():
    print(f"\nModel: {model_name}")
    print(f"MAE: {metrics['mae']:,.0f} records")
    print(f"MAPE: {metrics['mape']:.2f}%")

print(f"\nSelected model: {winning_model}")

print("\nNEXT SEVEN DAYS")

for row in future_forecasts:
    print(
        f"{row['forecast_date']} | "
        f"{row['predicted_records']:,} predicted records"
    )

print("\nFiles saved:")
print(backtest_file)
print(forecast_file)

print("\nRESULT: PASS")
