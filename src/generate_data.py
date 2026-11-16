
import csv
import random
from datetime import date, timedelta
from pathlib import Path

# Find the main SignalBench project folder
project_folder = Path(__file__).resolve().parents[1]

# Decide where our sample data will be saved
output_file = project_folder / "data" / "raw" / "workload.csv"

# Make our random data reproducible
random.seed(42)

# Generate 56 days of data, ending yesterday
end_date = date.today() - timedelta(days=1)
start_date = end_date - timedelta(days=55)

with output_file.open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    # Write the column names
    writer.writerow([
        "date",
        "records_processed",
        "data_volume_gb",
        "processing_minutes",
        "failed_records",
        "estimated_cost_usd"
    ])

    # Create one record for each day
    for day_number in range(56):
        current_date = start_date + timedelta(days=day_number)

        # Workload gradually increases over time
        base_records = 250000 + day_number * 1500

        # Weekends have slightly less work
        if current_date.weekday() >= 5:
            base_records = int(base_records * 0.8)

        # Occasionally, unusually large workloads occur
        if day_number in (17, 40):
            base_records = int(base_records * 1.6)

        records = int(base_records * random.uniform(0.9, 1.1))
        volume_gb = round(records * 0.00007, 2)
        duration = round(5 + volume_gb * 0.6 + random.uniform(0, 3), 2)
        failures = random.randint(0, 100)
        cost = round(volume_gb * 0.10 + duration * 0.04, 2)

        writer.writerow([
            current_date.isoformat(),
            records,
            volume_gb,
            duration,
            failures,
            cost
        ])

print("Success! Generated 56 days of SignalBench data.")
print(f"Saved to: {output_file}")
