
import argparse
import sqlite3
import subprocess
import sys

from contextlib import closing
from datetime import date, timedelta
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
DB_FILE = PROJECT / "data/database/signalbench.db"


def check_readiness():

    if not DB_FILE.exists():
        return "FAIL", "Database not found."

    with closing(sqlite3.connect(DB_FILE)) as connection:

        # Find the latest processed workload date
        row = connection.execute("""
            SELECT MAX(workload_date)
            FROM daily_workloads
        """).fetchone()

        if not row or not row[0]:
            return "FAIL", "Historical table is empty."

        latest = date.fromisoformat(row[0])

        # Check for the incoming data table
        exists = connection.execute("""
            SELECT 1 FROM sqlite_master
            WHERE type = 'table'
            AND name = 'incoming_workloads'
        """).fetchone()

        if not exists:
            return "SKIP", "No incoming data table."

        # Check that incoming records do not
        # conflict with existing historical records
        conflict = connection.execute("""
            SELECT i.workload_date
            FROM incoming_workloads i
            JOIN daily_workloads d
              ON i.workload_date = d.workload_date
            WHERE
                i.records_processed != d.records_processed
                OR i.data_volume_gb != d.data_volume_gb
                OR i.processing_minutes != d.processing_minutes
                OR i.failed_records != d.failed_records
                OR i.estimated_cost_usd != d.estimated_cost_usd
            LIMIT 1
        """).fetchone()

        if conflict:
            return "FAIL", (
                f"Conflicting record for {conflict[0]}"
            )

        # Find records not yet included in history
        pending = [
            date.fromisoformat(row[0])
            for row in connection.execute("""
                SELECT workload_date
                FROM incoming_workloads
                WHERE workload_date > ?
                ORDER BY workload_date
            """, (latest.isoformat(),))
        ]

    if not pending:
        return "SKIP", "No new workload data available."

    # Reject missing days
    for number, day in enumerate(pending, start=1):

        expected = latest + timedelta(days=number)

        if day != expected:
            return "FAIL", (
                f"Missing workload date: {expected}"
            )

    if pending[-1] > date.today():
        return "FAIL", "Future-dated record detected."

    # Avoid processing an incomplete current day
    if pending[-1] == date.today():
        return "SKIP", "Today's workload is not complete."

    return "READY", (
        f"{len(pending)} new day(s) available."
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the pipeline if new data is ready.",
    )

    args = parser.parse_args()

    print("\nSIGNALBENCH SCHEDULING CHECK")
    print("----------------------------")

    try:
        status, message = check_readiness()
    except (sqlite3.Error, ValueError, OSError) as error:
        status, message = "FAIL", str(error)

    print(f"Status: {status}")
    print(f"Reason: {message}")

    if status == "FAIL":
        return 1

    if status == "SKIP":
        print("No pipeline execution required.")
        return 0

    if not args.run:
        print("Dry run only. No data was modified.")
        return 0

    print("\nStarting the SignalBench pipeline...")

    result = subprocess.run(
        [sys.executable, str(PROJECT / "run_pipeline.py")],
        cwd=PROJECT,
        check=False,
    )

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
