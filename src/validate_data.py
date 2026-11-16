
import csv
import math
from datetime import date, timedelta
from pathlib import Path

# Find our raw data file
PROJECT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT / "data" / "raw" / "workload.csv"

# The exact columns we expect
EXPECTED_COLUMNS = [
    "date",
    "records_processed",
    "data_volume_gb",
    "processing_minutes",
    "failed_records",
    "estimated_cost_usd",
]

errors = []
dates = []
seen_dates = set()
row_count = 0

print("SIGNALBENCH DATA QUALITY CHECK")
print("------------------------------")

# Check whether our CSV exists
if not DATA_FILE.exists():
    raise SystemExit("FAIL: workload.csv was not found.")

with DATA_FILE.open("r", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)

    # Check column names and their order
    if reader.fieldnames != EXPECTED_COLUMNS:
        raise SystemExit(
            "FAIL: The CSV columns do not match the expected schema."
        )

    for line_number, row in enumerate(reader, start=2):
        row_count += 1

        # Check missing or empty values
        if any(
            value is None or not value.strip()
            for value in row.values()
        ):
            errors.append(f"Line {line_number}: Missing value")
            continue

        # Convert text into dates and numbers
        try:
            current_date = date.fromisoformat(row["date"])
            records = int(row["records_processed"])
            volume = float(row["data_volume_gb"])
            minutes = float(row["processing_minutes"])
            failures = int(row["failed_records"])
            cost = float(row["estimated_cost_usd"])
        except ValueError:
            errors.append(f"Line {line_number}: Invalid date or number")
            continue

        # Check duplicate dates
        if current_date in seen_dates:
            errors.append(f"Line {line_number}: Duplicate date")

        seen_dates.add(current_date)
        dates.append(current_date)

        # Check impossible values
        if (
            records <= 0
            or failures < 0
            or failures > records
            or not math.isfinite(volume)
            or not math.isfinite(minutes)
            or not math.isfinite(cost)
            or volume <= 0
            or minutes <= 0
            or cost < 0
        ):
            errors.append(f"Line {line_number}: Invalid workload values")

# Check expected number of records
if row_count != 56:
    errors.append(f"Expected 56 rows, found {row_count}")

# Check whether any days are missing
sorted_dates = sorted(seen_dates)

for previous, current in zip(sorted_dates, sorted_dates[1:]):
    if current - previous != timedelta(days=1):
        errors.append(f"Missing day(s) between {previous} and {current}")

# Show the final quality result
print(f"Rows checked: {row_count}")
print(f"Unique dates: {len(seen_dates)}")
print(f"Quality errors: {len(errors)}")

if errors:
    print("\nRESULT: FAIL")
    for error in errors:
        print("-", error)
    raise SystemExit(1)
else:
    print("\nRESULT: PASS")
    print("Data is ready for the next stage.")
