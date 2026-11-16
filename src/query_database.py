
import sqlite3
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DB_FILE = PROJECT / "data" / "database" / "signalbench.db"

if not DB_FILE.exists():
    raise SystemExit("Database missing. Run load_database.py first.")

connection = sqlite3.connect(DB_FILE)

try:
    print("SIGNALBENCH DATABASE ANALYSIS")
    print("-----------------------------")

    # Query 1: Count our records
    count = connection.execute("""
        SELECT COUNT(*) FROM daily_workloads
    """).fetchone()[0]

    print(f"\nTotal records: {count}")

    # Query 2: Calculate average daily workload
    average = connection.execute("""
        SELECT ROUND(AVG(records_processed), 0)
        FROM daily_workloads
    """).fetchone()[0]

    print(f"Average daily records: {average:,.0f}")

    # Query 3: Find the busiest processing day
    busiest = connection.execute("""
        SELECT workload_date, records_processed
        FROM daily_workloads
        ORDER BY records_processed DESC
        LIMIT 1
    """).fetchone()

    print(f"Busiest day: {busiest[0]}")
    print(f"Busiest day records: {busiest[1]:,}")

    # Query 4: Show the latest five days
    latest = connection.execute("""
        SELECT workload_date, records_processed
        FROM daily_workloads
        ORDER BY workload_date DESC
        LIMIT 5
    """).fetchall()

    print("\nLATEST FIVE DAYS")
    for day, records in latest:
        print(f"{day} | {records:,} records")

    print("\nRESULT: PASS")

finally:
    connection.close()
