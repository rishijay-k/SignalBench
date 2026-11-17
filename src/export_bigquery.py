
import csv
import sqlite3
from contextlib import closing
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DATABASE = PROJECT / "data/database/signalbench.db"
OUTPUT = PROJECT / "data/exports/bigquery_daily_workloads.csv"

COLUMNS = [
    "workload_date",
    "records_processed",
    "data_volume_gb",
    "processing_minutes",
    "failed_records",
    "estimated_cost_usd",
]


def main():
    if not DATABASE.is_file():
        raise SystemExit("ERROR: SignalBench database not found.")

    with closing(sqlite3.connect(DATABASE)) as connection:
        rows = connection.execute("""
            SELECT
                workload_date,
                records_processed,
                data_volume_gb,
                processing_minutes,
                failed_records,
                estimated_cost_usd
            FROM daily_workloads
            ORDER BY workload_date
        """).fetchall()

    if not rows:
        raise SystemExit("ERROR: No historical records.")

    dates = [row[0] for row in rows]

    if len(set(dates)) != len(dates):
        raise SystemExit("ERROR: Duplicate workload dates.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print("SIGNALBENCH CLOUD EXPORT")
    print("------------------------")
    print(f"Exported records: {len(rows)}")
    print(f"Latest date: {dates[-1]}")
    print(f"File: {OUTPUT}")
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
