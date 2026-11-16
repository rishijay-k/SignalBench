
import csv
import sqlite3
import unittest
from datetime import date, timedelta
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


class SignalBenchTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.raw = read_csv(
            PROJECT / "data/raw/workload.csv"
        )
        cls.backtest = read_csv(
            PROJECT / "data/forecasts/backtest_results.csv"
        )
        cls.forecasts = read_csv(
            PROJECT / "data/forecasts/next_7_days.csv"
        )

        cls.actual = {
            date.fromisoformat(row["date"]):
            int(row["records_processed"])
            for row in cls.raw
        }

    # TEST 1: Expected number of records
    def test_record_counts(self):
        self.assertEqual(len(self.raw), 56)
        self.assertEqual(len(self.backtest), 14)
        self.assertEqual(len(self.forecasts), 7)

    # TEST 2: Unique, consecutive dates
    def test_historical_dates(self):
        dates = sorted(
            date.fromisoformat(row["date"])
            for row in self.raw
        )

        self.assertEqual(len(set(dates)), 56)

        for previous, current in zip(dates, dates[1:]):
            self.assertEqual(
                current - previous,
                timedelta(days=1)
            )

    # TEST 3: Database matches source data
    def test_database_matches_csv(self):
        db_path = PROJECT / "data/database/signalbench.db"

        self.assertTrue(db_path.exists())

        connection = sqlite3.connect(db_path)

        try:
            database_rows = connection.execute("""
                SELECT workload_date, records_processed
                FROM daily_workloads
                ORDER BY workload_date
            """).fetchall()
        finally:
            connection.close()

        csv_rows = sorted([
            (row["date"], int(row["records_processed"]))
            for row in self.raw
        ])

        self.assertEqual(database_rows, csv_rows)

    # TEST 4: Historical predictions are correct
    def test_backtest_predictions(self):
        for row in self.backtest:
            day = date.fromisoformat(row["date"])

            self.assertEqual(
                int(row["actual_records"]),
                self.actual[day]
            )

            self.assertEqual(
                int(row["predicted_previous_day"]),
                self.actual[day - timedelta(days=1)]
            )

            self.assertEqual(
                int(row["predicted_previous_week"]),
                self.actual[day - timedelta(days=7)]
            )

    # TEST 5: Lowest-error model is selected
    def test_model_selection(self):
        columns = {
            "previous_day": "predicted_previous_day",
            "previous_week": "predicted_previous_week"
        }

        scores = {}

        for model, column in columns.items():
            errors = [
                abs(
                    int(row["actual_records"])
                    - int(row[column])
                )
                for row in self.backtest
            ]

            scores[model] = sum(errors) / len(errors)

        expected_winner = min(scores, key=scores.get)

        selected_model = self.forecasts[0]["model"]

        self.assertEqual(selected_model, expected_winner)

    # TEST 6: Future forecasts are consistent
    def test_future_forecasts(self):
        history = [
            self.actual[day]
            for day in sorted(self.actual)
        ]

        last_date = max(self.actual)
        model = self.forecasts[0]["model"]

        for index, row in enumerate(self.forecasts, start=1):
            expected_date = last_date + timedelta(days=index)

            self.assertEqual(
                date.fromisoformat(row["forecast_date"]),
                expected_date
            )

            self.assertEqual(row["model"], model)

            if model == "previous_day":
                expected_prediction = history[-1]
            elif model == "previous_week":
                expected_prediction = history[-7]
            else:
                self.fail("Unknown model")

            self.assertEqual(
                int(row["predicted_records"]),
                expected_prediction
            )

            history.append(expected_prediction)


if __name__ == "__main__":
    unittest.main()
