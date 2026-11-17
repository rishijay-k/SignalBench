
import csv
import math
import sqlite3
import unittest
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data/forecasts"


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


class AdvancedForecastTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.backtest = read_csv(
            DATA / "advanced_backtest.csv"
        )

        cls.scores = read_csv(
            DATA / "advanced_scores.csv"
        )

        cls.horizons = read_csv(
            DATA / "advanced_horizons.csv"
        )

        cls.forecasts = read_csv(
            DATA / "advanced_next_7_days.csv"
        )

        # Always use the complete SQL history
        with sqlite3.connect(
            PROJECT / "data/database/signalbench.db"
        ) as connection:
            rows = connection.execute("""
                SELECT workload_date, records_processed
                FROM daily_workloads
                ORDER BY workload_date
            """).fetchall()

        cls.actual = {
            date.fromisoformat(day): int(records)
            for day, records in rows
        }

    def test_output_counts(self):
        historical_days = len(self.actual)

        expected_origins = historical_days - 28 - 7 + 1
        expected_comparisons = (
            expected_origins * 7 * 3
        )

        self.assertGreater(expected_origins, 0)

        self.assertEqual(
            len(self.backtest),
            expected_comparisons
        )

        self.assertEqual(len(self.scores), 3)
        self.assertEqual(len(self.horizons), 21)
        self.assertEqual(len(self.forecasts), 7)

    def test_no_future_leakage(self):
        for row in self.backtest:
            origin = date.fromisoformat(
                row["origin_date"]
            )
            target = date.fromisoformat(
                row["target_date"]
            )

            horizon = int(row["horizon"])
            model = row["model"]

            self.assertEqual(
                target,
                origin + timedelta(days=horizon)
            )

            self.assertEqual(
                int(row["actual_records"]),
                self.actual[target]
            )

            if model == "previous_day":
                reference_days = [origin]
                expected = self.actual[origin]

            elif model == "previous_week":
                reference_days = [
                    target - timedelta(days=7)
                ]
                expected = self.actual[reference_days[0]]

            elif model == "weekday_median":
                reference_days = [
                    target - timedelta(days=7 * week)
                    for week in range(1, 5)
                ]

                expected = round(median([
                    self.actual[day]
                    for day in reference_days
                ]))

            else:
                self.fail("Unknown model")

            for day in reference_days:
                self.assertLessEqual(day, origin)

            self.assertEqual(
                int(row["predicted_records"]),
                expected
            )

    def test_model_selection(self):
        calculated_scores = {}

        for score in self.scores:
            model = score["model"]

            selected = [
                row for row in self.backtest
                if row["model"] == model
            ]

            mae = mean(
                int(row["absolute_error"])
                for row in selected
            )

            mape = mean(
                float(row["absolute_percentage_error"])
                for row in selected
            )

            self.assertAlmostEqual(
                float(score["mae"]),
                mae,
                places=5
            )

            calculated_scores[model] = (mae, mape)

        winner = min(
            calculated_scores,
            key=lambda model: calculated_scores[model]
        )

        self.assertEqual(
            self.forecasts[0]["model"],
            winner
        )

    def test_forecast_error_bands(self):
        winner = self.forecasts[0]["model"]
        last_date = max(self.actual)

        for row in self.forecasts:
            horizon = int(row["horizon"])

            forecast_date = date.fromisoformat(
                row["forecast_date"]
            )

            self.assertEqual(
                forecast_date,
                last_date + timedelta(days=horizon)
            )

            errors = sorted(
                int(item["absolute_error"])
                for item in self.backtest
                if item["model"] == winner
                and int(item["horizon"]) == horizon
            )

            self.assertTrue(errors)

            rank = math.ceil(0.90 * len(errors))
            expected_band = errors[rank - 1]

            prediction = int(row["predicted_records"])

            self.assertEqual(
                int(row["historical_error_p90"]),
                expected_band
            )

            self.assertEqual(
                int(row["lower_bound"]),
                max(0, prediction - expected_band)
            )

            self.assertEqual(
                int(row["upper_bound"]),
                prediction + expected_band
            )


if __name__ == "__main__":
    unittest.main()
