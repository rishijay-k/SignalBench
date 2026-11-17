
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
        # Keep original CSV records separate
        cls.raw = read_csv(
            PROJECT / "data/raw/workload.csv"
        )

        cls.backtest = read_csv(
            PROJECT / "data/forecasts/backtest_results.csv"
        )

        cls.forecasts = read_csv(
            PROJECT / "data/forecasts/next_7_days.csv"
        )

        cls.rolling = read_csv(
            PROJECT / "data/forecasts/rolling_backtest.csv"
        )

        # Read complete history from SQLite
        with sqlite3.connect(
            PROJECT / "data/database/signalbench.db"
        ) as connection:

            rows = connection.execute("""
                SELECT workload_date, records_processed
                FROM daily_workloads
                ORDER BY workload_date
            """).fetchall()

            exists = connection.execute("""
                SELECT 1 FROM sqlite_master
                WHERE type = 'table'
                AND name = 'incoming_workloads'
            """).fetchone()

            cls.incoming = (
                connection.execute("""
                    SELECT workload_date, records_processed
                    FROM incoming_workloads
                """).fetchall()
                if exists else []
            )

        cls.actual = {
            date.fromisoformat(day): int(records)
            for day, records in rows
        }

        cls.historical_dates = sorted(cls.actual)

    # TEST 1: Record counts
    def test_record_counts(self):
        self.assertGreaterEqual(len(self.raw), 35)
        self.assertGreaterEqual(
            len(self.actual), len(self.raw)
        )
        self.assertEqual(len(self.backtest), 14)
        self.assertEqual(len(self.forecasts), 7)

    # TEST 2: Original dates are valid
    def test_historical_dates(self):
        dates = sorted(
            date.fromisoformat(row["date"])
            for row in self.raw
        )

        self.assertEqual(len(dates), len(set(dates)))

        for previous, current in zip(dates, dates[1:]):
            self.assertEqual(
                current - previous,
                timedelta(days=1)
            )

    # TEST 3: Database matches source records
    def test_database_matches_csv(self):
        expected = {
            date.fromisoformat(row["date"]):
            int(row["records_processed"])
            for row in self.raw
        }

        for day_string, records in self.incoming:
            day = date.fromisoformat(day_string)

            if day in expected:
                self.assertEqual(expected[day], int(records))

            expected[day] = int(records)

        self.assertEqual(self.actual, expected)

    # TEST 4: Historical predictions
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

    # TEST 5: Automatic model selection
    def test_model_selection(self):
        models = ("previous_day", "previous_week")

        expected_origins = len(self.actual) - 28 - 7 + 1
        expected_per_model = expected_origins * 7

        self.assertGreater(expected_origins, 0)

        scores = {}

        for model in models:
            selected = [
                row for row in self.rolling
                if row["model"] == model
            ]

            self.assertEqual(
                len(selected), expected_per_model
            )

            scores[model] = sum(
                int(row["absolute_error"])
                for row in selected
            ) / len(selected)

        winner = min(scores, key=scores.get)

        self.assertEqual(
            self.forecasts[0]["model"], winner
        )

    # TEST 6: Future forecast dates and values
    def test_future_forecasts(self):
        history = [
            self.actual[day]
            for day in self.historical_dates
        ]

        last_date = self.historical_dates[-1]
        model = self.forecasts[0]["model"]

        for horizon, row in enumerate(
            self.forecasts, start=1
        ):
            expected_date = last_date + timedelta(
                days=horizon
            )

            self.assertEqual(
                date.fromisoformat(row["forecast_date"]),
                expected_date
            )

            self.assertEqual(row["model"], model)

            if model == "previous_day":
                expected = history[-1]

            elif model == "previous_week":
                expected = history[-7]

            else:
                self.fail("Unknown forecasting model")

            self.assertEqual(
                int(row["predicted_records"]),
                expected
            )

            history.append(expected)

    # TEST 7: Rolling forecast correctness
    def test_rolling_forecast_logic(self):
        for row in self.rolling:
            origin = date.fromisoformat(
                row["origin_date"]
            )

            target = date.fromisoformat(
                row["target_date"]
            )

            horizon = int(row["horizon"])

            self.assertIn(horizon, range(1, 8))

            self.assertEqual(
                target,
                origin + timedelta(days=horizon)
            )

            self.assertEqual(
                int(row["actual_records"]),
                self.actual[target]
            )

            if row["model"] == "previous_day":
                reference_date = origin

            elif row["model"] == "previous_week":
                reference_date = (
                    target - timedelta(days=7)
                )

            else:
                self.fail("Unknown model")

            self.assertLessEqual(reference_date, origin)

            prediction = int(row["predicted_records"])

            self.assertEqual(
                prediction,
                self.actual[reference_date]
            )

            self.assertEqual(
                int(row["absolute_error"]),
                abs(self.actual[target] - prediction)
            )

    # TEST 8: Complete history is consecutive
    def test_merged_history_is_consecutive(self):
        dates = self.historical_dates

        self.assertGreaterEqual(len(dates), 35)

        for previous, current in zip(dates, dates[1:]):
            self.assertEqual(
                current - previous,
                timedelta(days=1)
            )


if __name__ == "__main__":
    unittest.main()
