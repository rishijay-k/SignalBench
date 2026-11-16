
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.ingest_daily import ingest_workload


class IncrementalIngestionTests(unittest.TestCase):

    def setUp(self):
        # Every test uses a temporary database.
        # The real SignalBench database is untouched.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "test.db"

        sqlite3.connect(self.db).close()

        self.sample = {
            "work_date": "2020-01-01",
            "records": 220000,
            "volume_gb": 15.4,
            "processing_minutes": 16.7,
            "failed_records": 12,
            "estimated_cost_usd": 2.21,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def row_count(self):
        with sqlite3.connect(self.db) as connection:
            return connection.execute("""
                SELECT COUNT(*) FROM incoming_workloads
            """).fetchone()[0]

    def test_insert_new_record(self):
        result = ingest_workload(self.db, **self.sample)

        self.assertEqual(result, "INSERTED")
        self.assertEqual(self.row_count(), 1)

    def test_repeated_insert_is_idempotent(self):
        ingest_workload(self.db, **self.sample)

        result = ingest_workload(self.db, **self.sample)

        self.assertEqual(result, "ALREADY_EXISTS")
        self.assertEqual(self.row_count(), 1)

    def test_conflicting_record_is_rejected(self):
        ingest_workload(self.db, **self.sample)

        changed = {
            **self.sample,
            "records": 250000,
        }

        with self.assertRaises(ValueError):
            ingest_workload(self.db, **changed)

        self.assertEqual(self.row_count(), 1)

    def test_invalid_workload_is_rejected(self):
        invalid = {
            **self.sample,
            "failed_records": 300000,
        }

        with self.assertRaises(ValueError):
            ingest_workload(self.db, **invalid)


if __name__ == "__main__":
    unittest.main()
