
import csv
import sqlite3
import subprocess
import sys
from pathlib import Path

# Find our SignalBench project
PROJECT = Path(__file__).resolve().parents[1]

CSV_FILE = PROJECT / "data" / "raw" / "workload.csv"
DB_FILE = PROJECT / "data" / "database" / "signalbench.db"

print("SIGNALBENCH DATABASE LOADER")
print("---------------------------")

# STEP 1: Validate the data before storing it
print("Checking data quality...")

subprocess.run(
    [sys.executable, str(PROJECT / "src" / "validate_data.py")],
    check=True,
)

# STEP 2: Read our validated CSV records
rows = []

with CSV_FILE.open("r", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        rows.append((
            row["date"],
            int(row["records_processed"]),
            float(row["data_volume_gb"]),
            float(row["processing_minutes"]),
            int(row["failed_records"]),
            float(row["estimated_cost_usd"]),
        ))

# STEP 3: Connect to SQLite
DB_FILE.parent.mkdir(parents=True, exist_ok=True)

connection = sqlite3.connect(DB_FILE)

try:
    with connection:

        # STEP 4: Create our first SQL table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS daily_workloads (
                workload_date TEXT NOT NULL PRIMARY KEY,
                records_processed INTEGER NOT NULL
                    CHECK(records_processed > 0),
                data_volume_gb REAL NOT NULL
                    CHECK(data_volume_gb > 0),
                processing_minutes REAL NOT NULL
                    CHECK(processing_minutes > 0),
                failed_records INTEGER NOT NULL
                    CHECK(failed_records >= 0),
                estimated_cost_usd REAL NOT NULL
                    CHECK(estimated_cost_usd >= 0),
                CHECK(failed_records <= records_processed)
            )
        """)

        # STEP 5: Refresh our demonstration dataset
        connection.execute("DELETE FROM daily_workloads")

        connection.executemany("""
            INSERT INTO daily_workloads (
                workload_date,
                records_processed,
                data_volume_gb,
                processing_minutes,
                failed_records,
                estimated_cost_usd
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, rows)

    # STEP 6: Confirm the number of stored records
    count = connection.execute(
        "SELECT COUNT(*) FROM daily_workloads"
    ).fetchone()[0]

    print("\nDATABASE LOAD COMPLETE")
    print(f"Records inserted: {count}")
    print(f"Database file: {DB_FILE}")
    print("RESULT: PASS" if count == 56 else "RESULT: FAIL")

finally:
    connection.close()
