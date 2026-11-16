
import argparse
import math
import sqlite3
from datetime import date
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DB_FILE = PROJECT / "data/database/signalbench.db"


def ingest_workload(
    db_path,
    work_date,
    records,
    volume_gb,
    processing_minutes,
    failed_records,
    estimated_cost_usd,
):
    # 1. Validate the incoming values
    try:
        parsed_date = date.fromisoformat(work_date)
    except ValueError:
        raise ValueError("Invalid date. Use YYYY-MM-DD.")

    if parsed_date.isoformat() != work_date:
        raise ValueError("Date must use YYYY-MM-DD.")

    if parsed_date > date.today():
        raise ValueError("Future workload dates are not allowed.")

    if records <= 0:
        raise ValueError("Records must be positive.")

    if failed_records < 0 or failed_records > records:
        raise ValueError("Invalid failed-record count.")

    for name, value in [
        ("Volume", volume_gb),
        ("Processing time", processing_minutes),
        ("Cost", estimated_cost_usd),
    ]:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite.")

    if volume_gb <= 0 or processing_minutes <= 0:
        raise ValueError("Volume and processing time must be positive.")

    if estimated_cost_usd < 0:
        raise ValueError("Cost cannot be negative.")

    if not db_path.is_file():
        raise ValueError("Existing SignalBench database not found.")

    payload = (
        work_date,
        records,
        volume_gb,
        processing_minutes,
        failed_records,
        estimated_cost_usd,
    )

    # 2. Connect to the existing database
    connection = sqlite3.connect(db_path, timeout=10)

    try:
        # Prevent two writers from checking/inserting
        # the same record simultaneously.
        connection.execute("BEGIN IMMEDIATE")

        # 3. Create an incremental landing table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incoming_workloads (
                workload_date TEXT PRIMARY KEY NOT NULL,
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
                source_type TEXT NOT NULL
                    DEFAULT 'synthetic_manual',
                ingested_at_utc TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                CHECK(failed_records <= records_processed)
            )
        """)

        # 4. Check whether this date already exists
        existing = connection.execute("""
            SELECT
                workload_date,
                records_processed,
                data_volume_gb,
                processing_minutes,
                failed_records,
                estimated_cost_usd
            FROM incoming_workloads
            WHERE workload_date = ?
        """, (work_date,)).fetchone()

        if existing is None:
            # New date: insert the record
            connection.execute("""
                INSERT INTO incoming_workloads (
                    workload_date,
                    records_processed,
                    data_volume_gb,
                    processing_minutes,
                    failed_records,
                    estimated_cost_usd
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, payload)

            result = "INSERTED"

        elif tuple(existing) == payload:
            # Exactly the same record: do nothing
            result = "ALREADY_EXISTS"

        else:
            # Same date, different values: reject
            raise ValueError(
                "CONFLICT: This date already contains "
                "different data. No changes were saved."
            )

        connection.commit()
        return result

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest a daily SignalBench workload"
    )

    parser.add_argument("--date", required=True)
    parser.add_argument("--records", required=True, type=int)
    parser.add_argument("--gb", required=True, type=float)
    parser.add_argument("--minutes", required=True, type=float)
    parser.add_argument("--failed", required=True, type=int)
    parser.add_argument("--cost", required=True, type=float)

    args = parser.parse_args()

    print("\nSIGNALBENCH INCREMENTAL INGESTION")
    print("--------------------------------")

    try:
        result = ingest_workload(
            DB_FILE,
            args.date,
            args.records,
            args.gb,
            args.minutes,
            args.failed,
            args.cost,
        )

    except (ValueError, sqlite3.Error, OSError) as error:
        print(f"RESULT: FAIL - {error}")
        return 1

    print(f"Date: {args.date}")
    print(f"Records: {args.records:,}")
    print(f"RESULT: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
