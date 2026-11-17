
import csv
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

CSV_FILE = PROJECT / "data/raw/workload.csv"
DB_FILE = PROJECT / "data/database/signalbench.db"

COLUMNS = """
    workload_date,
    records_processed,
    data_volume_gb,
    processing_minutes,
    failed_records,
    estimated_cost_usd
"""


def read_original_data():
    rows = []

    with CSV_FILE.open(
        "r", newline="", encoding="utf-8"
    ) as file:
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

    return rows


def merge_record(connection, payload):
    existing = connection.execute(
        f"""
        SELECT {COLUMNS}
        FROM daily_workloads
        WHERE workload_date = ?
        """,
        (payload[0],),
    ).fetchone()

    if existing is None:
        connection.execute(
            f"""
            INSERT INTO daily_workloads ({COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        return "INSERTED"

    if tuple(existing) == tuple(payload):
        return "UNCHANGED"

    raise ValueError(
        f"Conflicting workload for {payload[0]}. "
        "Existing historical data was not overwritten."
    )


def main():
    print("\nSIGNALBENCH INCREMENTAL DATABASE LOADER")
    print("---------------------------------------")

    # Validate the original CSV first
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "src/validate_data.py"),
        ],
        check=True,
    )

    original_rows = read_original_data()

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Explicit transaction management:
    # all inserts succeed together or roll back.
    connection = sqlite3.connect(
        DB_FILE,
        timeout=10,
        autocommit=False,
    )

    inserted = 0
    unchanged = 0
    incoming_count = 0

    try:
        with connection:
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

            # First merge the original snapshot
            for payload in original_rows:
                result = merge_record(connection, payload)

                if result == "INSERTED":
                    inserted += 1
                else:
                    unchanged += 1

            # Check whether the incremental table exists
            landing_exists = connection.execute("""
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                AND name = 'incoming_workloads'
            """).fetchone()

            if landing_exists:
                incoming_rows = connection.execute(
                    f"""
                    SELECT {COLUMNS}
                    FROM incoming_workloads
                    ORDER BY workload_date
                    """
                ).fetchall()
            else:
                incoming_rows = []

            incoming_count = len(incoming_rows)

            # Merge accepted incremental records
            for payload in incoming_rows:

                parsed_date = date.fromisoformat(payload[0])

                if parsed_date > date.today():
                    raise ValueError(
                        "Future-dated workload detected."
                    )

                result = merge_record(connection, payload)

                if result == "INSERTED":
                    inserted += 1
                else:
                    unchanged += 1

            # Verify complete chronological history
            all_dates = [
                date.fromisoformat(row[0])
                for row in connection.execute("""
                    SELECT workload_date
                    FROM daily_workloads
                    ORDER BY workload_date
                """)
            ]

            for previous, current in zip(
                all_dates, all_dates[1:]
            ):
                if current - previous != timedelta(days=1):
                    raise ValueError(
                        "Missing or duplicate historical day "
                        f"between {previous} and {current}."
                    )

            count = len(all_dates)
            latest = all_dates[-1] if all_dates else None

        print(f"Original CSV rows: {len(original_rows)}")
        print(f"Incoming rows found: {incoming_count}")
        print(f"Newly inserted: {inserted}")
        print(f"Already present: {unchanged}")
        print(f"Total forecasting records: {count}")
        print(f"Latest workload date: {latest}")
        print("RESULT: PASS")

        return 0

    except (ValueError, sqlite3.Error) as error:
        print(f"RESULT: FAIL - {error}")
        return 1

    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
