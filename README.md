
# SignalBench

## Predictive Workload Intelligence

SignalBench is a data engineering demonstration project that
generates processing workloads, validates their quality,
stores them in SQL, and forecasts future demand.

The project demonstrates an end-to-end local data pipeline
with forecasting, backtesting, and an interactive dashboard.

## Architecture

Synthetic Data Generator
    |
    v
CSV Dataset
    |
    v
Data Quality Validation
    |
    v
SQLite Database
    |
    v
Forecasting + Backtesting
    |
    v
Streamlit Dashboard

## Technology Stack

- Python 3.14
- SQLite
- SQL
- Pandas
- Streamlit
- Git

## Project Features

- Generate 56 days of synthetic workload data
- Validate missing, duplicate, and invalid records
- Store structured workload data in SQLite
- Query workloads using SQL
- Compare previous-day and previous-week forecasting
- Evaluate one-step-ahead historical predictions
- Generate seven-day workload forecasts
- Display results in an interactive dashboard
- Run automated consistency tests

## Run Locally on macOS

Requires Python 3.14.

Open Terminal in the SignalBench project folder.

Create and activate a virtual environment:

    python3.14 -m venv .venv
    source .venv/bin/activate

Install dependencies:

    python -m pip install -r requirements.txt

Create the data directories:

    mkdir -p data/raw data/database

Generate and validate data:

    python src/generate_data.py
    python src/validate_data.py

Load and query the SQL database:

    python src/load_database.py
    python src/query_database.py

Generate forecasts:

    python src/forecast.py

Run automated tests:

    python -m unittest discover -s tests -v

Launch the dashboard:

    python -m streamlit run app.py

Open the local URL displayed by Streamlit.

## Model Evaluation

The forecasting engine evaluates two baseline methods:

1. Previous-day prediction
2. Previous-week prediction

It uses the final 14 historical observations to compare
one-step-ahead forecasting accuracy.

Metrics:
- MAE: Mean Absolute Error
- MAPE: Mean Absolute Percentage Error

The model with the lowest MAE is used to generate a
seven-day forecast.

## Limitations

- All historical workload data is synthetic.
- Results are not evidence of real production performance.
- The initial backtest measures one-step-ahead predictions.
- Seven-day forecast accuracy has not yet been independently
  evaluated with a multi-horizon backtest.
- The system currently runs locally, not on cloud infrastructure.

## Future Development

- Rolling-origin multi-horizon backtesting
- Stronger forecasting models
- Prediction intervals
- Automated pipeline orchestration
- Google Cloud and BigQuery integration
- Production monitoring and observability

## Author

Rishijay S Kocher

Website: https://rishijay.com
