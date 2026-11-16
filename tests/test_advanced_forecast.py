
import csv
import math
import unittest
from datetime import date, timedelta
from pathlib import Path
from statistics import median, mean

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

        history = read_csv(
            PROJECT / "data/raw/workload.csv"
        )

        cls.actual = {
            date.fromisoformat(row["date"]):
            int(row["records_processed"])
            for row in history
        }

    # Test 1: All expected outputs exist
    def test_output_counts(self):
        self.assertEqual(len(self.backtest), 462)
        self.assertEqual(len(self.scores), 3)
        self.assertEqual(len(self.horizons), 21)
        self.assertEqual(len(self.forecasts), 7)

    # Test 2: Historical forecasts use past data
    def test_no_future_leakage(self):
        for row in self.backtest:
            origin = date.fromisoformat(row["origin_date"])
            target = date.fromisoformat(row["target_date"])
            model = row["model"]

            if model == "previous_day":
                expected = self.actual[origin]

            elif model == "previous_week":
                expected = self.actual[
                    target - timedelta(days=7)
                ]

            elif model == "weekday_median":
                past_days = [
                    target - timedelta(days=7 * week)
                    for week in range(1, 5)
                ]

                self.assertTrue(
                    all(day <= origin for day in past_days)
                )

                expected = round(median([
                    self.actual[day]
                    for day in past_days
                ]))

            else:
                self.fail("Unknown forecasting model")

            self.assertEqual(
                int(row["predicted_records"]),
                expected
            )

    # Test 3: The lowest-MAE model wins
    def test_model_selection(self):
        scores = {}

        for row in self.scores:
            model = row["model"]
            selected = [
                item for item in self.backtest
                if item["model"] == model
            ]

            scores[model] = mean(
                int(item["absolute_error"])
                for item in selected
            )

        expected_winner = min(scores, key=scores.get)

        self.assertEqual(
            self.forecasts[0]["model"],
            expected_winner
        )

    # Test 4: Forecast bands match historical errors
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
