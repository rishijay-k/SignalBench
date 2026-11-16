
from pathlib import Path
import sqlite3

import altair as alt
import pandas as pd
import streamlit as st


# -----------------------------------------
# 1. Configure the dashboard
# -----------------------------------------

st.set_page_config(
    page_title="SignalBench | Workload Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROJECT = Path(__file__).resolve().parent

DB_FILE = PROJECT / "data/database/signalbench.db"
BACKTEST_FILE = PROJECT / "data/forecasts/backtest_results.csv"
FORECAST_FILE = PROJECT / "data/forecasts/next_7_days.csv"

ROLLING_BACKTEST_FILE = (
    PROJECT / "data/forecasts/rolling_backtest.csv"
)

ROLLING_SUMMARY_FILE = (
    PROJECT / "data/forecasts/rolling_summary.csv"
)

# Advanced forecasting outputs
ADVANCED_BACKTEST_FILE = (
    PROJECT / "data/forecasts/advanced_backtest.csv"
)

ADVANCED_SCORES_FILE = (
    PROJECT / "data/forecasts/advanced_scores.csv"
)

ADVANCED_HORIZONS_FILE = (
    PROJECT / "data/forecasts/advanced_horizons.csv"
)

ADVANCED_FORECAST_FILE = (
    PROJECT / "data/forecasts/advanced_next_7_days.csv"
)



# -----------------------------------------
# 2. Check the input files
# -----------------------------------------



for file_path in [
    DB_FILE,
    BACKTEST_FILE,
    FORECAST_FILE,
    ROLLING_BACKTEST_FILE,
    ROLLING_SUMMARY_FILE,
    ADVANCED_BACKTEST_FILE,
    ADVANCED_SCORES_FILE,
    ADVANCED_HORIZONS_FILE,
    ADVANCED_FORECAST_FILE,
]:


    if not file_path.exists():
        st.error(f"Required file missing: {file_path}")
        st.stop()


# -----------------------------------------
# 3. Read historical data from SQLite
# -----------------------------------------

connection = sqlite3.connect(DB_FILE)

try:
    historical = pd.read_sql_query(
        """
        SELECT
            workload_date,
            records_processed,
            data_volume_gb,
            processing_minutes,
            failed_records,
            estimated_cost_usd
        FROM daily_workloads
        ORDER BY workload_date
        """,
        connection,
    )
finally:
    connection.close()

historical["workload_date"] = pd.to_datetime(
    historical["workload_date"]
)


# -----------------------------------------
# 4. Read forecasting results
# -----------------------------------------

backtest = pd.read_csv(
    BACKTEST_FILE,
    parse_dates=["date"],
)

forecasts = pd.read_csv(
    FORECAST_FILE,
    parse_dates=["forecast_date"],
)


# Read seven-day rolling backtesting results

rolling_details = pd.read_csv(
    ROLLING_BACKTEST_FILE,
    parse_dates=["origin_date", "target_date"],
)

rolling_summary = pd.read_csv(
    ROLLING_SUMMARY_FILE
)

# Read all three-model evaluation outputs

advanced_backtest = pd.read_csv(
    ADVANCED_BACKTEST_FILE,
    parse_dates=["origin_date", "target_date"],
)

advanced_scores = pd.read_csv(
    ADVANCED_SCORES_FILE
)

advanced_horizons = pd.read_csv(
    ADVANCED_HORIZONS_FILE
)

advanced_forecasts = pd.read_csv(
    ADVANCED_FORECAST_FILE,
    parse_dates=["forecast_date"],
)

advanced_scores = (
    advanced_scores
    .sort_values("mae")
    .reset_index(drop=True)
)




if any(
    dataset.empty
    for dataset in [
        historical,
        backtest,
        forecasts,
        rolling_details,
        rolling_summary,
        advanced_backtest,
        advanced_scores,
        advanced_horizons,
        advanced_forecasts,
    ]
):


    st.error("One or more datasets are empty.")
    st.stop()


# -----------------------------------------
# 5. Calculate model accuracy
# -----------------------------------------

models = {
    "previous_day": "predicted_previous_day",
    "previous_week": "predicted_previous_week",
}

model_scores = []

for model_name, column in models.items():
    errors = (
        backtest["actual_records"] - backtest[column]
    ).abs()

    mae = errors.mean()

    mape = (
        errors / backtest["actual_records"]
    ).mean() * 100

    model_scores.append({
        "Model": model_name,
        "MAE": round(mae, 2),
        "MAPE (%)": round(mape, 2),
    })

scores = pd.DataFrame(model_scores)
scores = scores.sort_values("MAE").reset_index(drop=True)

best_model = scores.iloc[0]["Model"]
reported_model = forecasts.iloc[0]["model"]

if reported_model not in models:
    st.error("Unknown forecasting model in saved results.")
    st.stop()

if reported_model != best_model:
    st.warning(
        "Saved forecasts use a different model from the "
        "current backtesting winner. Rerun forecast.py."
    )

winning_mae = scores.loc[
    scores["Model"] == reported_model, "MAE"
].iloc[0]

winning_mape = scores.loc[
    scores["Model"] == reported_model, "MAPE (%)"
].iloc[0]


# -----------------------------------------
# 6. Dashboard heading
# -----------------------------------------

st.title("SignalBench")
st.subheader("Predictive Workload Intelligence")

st.caption(
    "A data engineering demonstration for workload forecasting, "
    "data quality and model evaluation."
)

st.info(
    "Demonstration environment: all workload data is synthetic. "
    "Forecasts are based on stored historical data, not a live feed."
)


# -----------------------------------------
# 7. Sidebar controls
# -----------------------------------------

st.sidebar.title("SignalBench")
st.sidebar.caption("Dashboard controls")

days = st.sidebar.slider(
    "Historical days to display",
    min_value=7,
    max_value=len(historical),
    value=len(historical),
)

recent = historical.tail(days)

st.sidebar.divider()
st.sidebar.write(f"Database records: {len(historical)}")
st.sidebar.write(f"Backtest observations: {len(backtest)}")
st.sidebar.write(f"Forecasted days: {len(forecasts)}")


# -----------------------------------------
# 8. Main dashboard tabs
# -----------------------------------------



tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview",
    "Forecasts",
    "Backtesting",
    "Data Explorer",
    "7-Day Evaluation",
    "Advanced Forecasting",
])




# -----------------------------------------
# TAB 1: Historical overview
# -----------------------------------------

with tab1:

    st.header("Historical workload overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Days displayed",
        f"{len(recent)}",
    )

    c2.metric(
        "Average daily records",
        f"{recent['records_processed'].mean():,.0f}",
    )

    c3.metric(
        "Peak daily records",
        f"{recent['records_processed'].max():,}",
    )

    c4.metric(
        "Total data processed",
        f"{recent['data_volume_gb'].sum():,.1f} GB",
    )

    st.subheader("Daily processing workload")

    st.line_chart(
        recent,
        x="workload_date",
        y="records_processed",
    )

    st.subheader("Processing cost trend")

    st.line_chart(
        recent,
        x="workload_date",
        y="estimated_cost_usd",
    )


# -----------------------------------------
# TAB 2: Future forecasts
# -----------------------------------------

with tab2:

    st.header("Seven-day workload forecast")

    st.caption(
        "These are the seven days after the final "
        "historical record, not necessarily after today."
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Selected model",
        reported_model.replace("_", " ").title(),
    )

    c2.metric(
        "Backtest MAE",
        f"{winning_mae:,.0f} records",
    )

    c3.metric(
        "Backtest MAPE",
        f"{winning_mape:.2f}%",
    )

    st.subheader("Predicted daily workload")

    st.line_chart(
        forecasts,
        x="forecast_date",
        y="predicted_records",
    )

    st.subheader("Forecast records")

    st.dataframe(
        forecasts,
        hide_index=True,
    )

    st.download_button(
        "Download forecasts CSV",
        data=FORECAST_FILE.read_bytes(),
        file_name="signalbench_forecasts.csv",
        mime="text/csv",
    )


# -----------------------------------------
# TAB 3: Backtesting
# -----------------------------------------

with tab3:

    st.header("Model evaluation")

    st.write(
        "We compared two simple forecasting methods "
        "using 14 historical days."
    )

    st.subheader("Model accuracy comparison")

    st.dataframe(
        scores,
        hide_index=True,
    )

    st.caption(
        "MAE measures average error in records. "
        "MAPE measures average percentage error. "
        "Lower values are better."
    )

    st.subheader("Actual versus predicted workload")

    selected_column = models[reported_model]

    st.line_chart(
        backtest,
        x="date",
        y=["actual_records", selected_column],
    )

    st.caption(
        "This backtest measures one-step-ahead predictions. "
        "Seven-day forecasting accuracy needs separate testing."
    )

    st.subheader("Detailed backtest results")

    st.dataframe(
        backtest,
        hide_index=True,
    )


# -----------------------------------------
# TAB 4: Data explorer
# -----------------------------------------

with tab4:

    st.header("Historical data explorer")

    st.write(
        "Browse the historical workload records "
        "stored inside the SQLite database."
    )

    st.dataframe(
        recent.sort_values(
            "workload_date",
            ascending=False,
        ),
        hide_index=True,
    )

    st.download_button(
        "Download historical data CSV",
        data=historical.to_csv(index=False).encode("utf-8"),
        file_name="signalbench_historical.csv",
        mime="text/csv",
    )


# -----------------------------------------
# TAB 5: Seven-day forecasting evaluation
# -----------------------------------------

with tab5:

    st.header("Seven-Day Forecast Evaluation")

    st.caption(
        "Rolling-origin backtesting across historical "
        "starting points. Each model predicts seven days "
        "without seeing future actual values."
    )

    # Calculate overall model accuracy
    overall = (
        rolling_details
        .groupby("model", as_index=False)
        .agg(
            comparisons=("absolute_error", "size"),
            mae=("absolute_error", "mean"),
            mape=("absolute_percentage_error", "mean"),
        )
        .sort_values("mae")
        .reset_index(drop=True)
    )

    rolling_winner = overall.iloc[0]["model"]
    rolling_mae = overall.iloc[0]["mae"]
    rolling_mape = overall.iloc[0]["mape"]

    origin_count = rolling_details["origin_date"].nunique()

    # Summary cards
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Rolling starting points",
        f"{origin_count}",
    )

    c2.metric(
        "Best seven-day model",
        rolling_winner.replace("_", " ").title(),
    )

    c3.metric(
        "Seven-day MAE",
        f"{rolling_mae:,.0f}",
    )

    c4.metric(
        "Seven-day MAPE",
        f"{rolling_mape:.2f}%",
    )

    st.divider()

    # Compare overall model accuracy
    st.subheader("Overall model comparison")

    st.dataframe(
        overall.round(2),
        hide_index=True,
    )

    if rolling_winner != reported_model:
        st.warning(
            "The seven-day evaluation selected a different "
            "model from the current forecast generator. "
            "Existing future predictions have not changed."
        )
    else:
        st.success(
            "The seven-day evaluation and existing "
            "forecast generator selected the same model."
        )

    # Display error by forecast horizon
    st.subheader("Prediction error by days ahead")

    mae_chart = (
        rolling_summary
        .pivot(
            index="horizon",
            columns="model",
            values="mae",
        )
        .reset_index()
    )

    st.line_chart(
        mae_chart,
        x="horizon",
        y=["previous_day", "previous_week"],
    )

    st.caption(
        "Day 1 measures tomorrow's forecast. "
        "Day 7 measures the seventh day ahead. "
        "Lower MAE indicates better historical accuracy."
    )

    # Show the percentage error as well
    st.subheader("Percentage error by forecast horizon")

    mape_chart = (
        rolling_summary
        .pivot(
            index="horizon",
            columns="model",
            values="mape",
        )
        .reset_index()
    )

    st.line_chart(
        mape_chart,
        x="horizon",
        y=["previous_day", "previous_week"],
    )

    # Interactive historical forecast explorer
    st.divider()
    st.subheader("Explore a historical forecast")

    selected_model = st.selectbox(
        "Choose a forecasting model",
        ["previous_day", "previous_week"],
        key="rolling_model",
    )

    available_origins = sorted(
        rolling_details["origin_date"].dt.date.unique(),
        reverse=True,
    )

    selected_origin = st.selectbox(
        "Choose a historical forecast starting date",
        available_origins,
        key="rolling_origin",
    )

    selected_rows = rolling_details.loc[
        (rolling_details["model"] == selected_model)
        & (
            rolling_details["origin_date"].dt.date
            == selected_origin
        )
    ].sort_values("horizon")

    st.line_chart(
        selected_rows,
        x="target_date",
        y=["actual_records", "predicted_records"],
    )

    st.caption(
        "Compare the seven predictions made at the "
        "selected historical starting point with "
        "what actually happened."
    )

    st.dataframe(
        selected_rows,
        hide_index=True,
    )

    # Download full evaluation results
    st.divider()

    st.download_button(
        "Download seven-day backtesting results",
        data=ROLLING_BACKTEST_FILE.read_bytes(),
        file_name="signalbench_rolling_backtest.csv",
        mime="text/csv",
    )

# -----------------------------------------
# TAB 6: Advanced Forecasting
# -----------------------------------------

with tab6:

    st.header("Advanced Forecasting Intelligence")

    st.caption(
        "Three forecasting methods evaluated across "
        "seven future horizons using rolling-origin "
        "historical backtesting."
    )

    # -------------------------------------
    # 1. Identify the winning model
    # -------------------------------------

    advanced_winner = advanced_scores.iloc[0]["model"]
    winner_mae = advanced_scores.iloc[0]["mae"]
    winner_mape = advanced_scores.iloc[0]["mape"]

    forecast_models = advanced_forecasts["model"].unique()

    if (
        len(forecast_models) != 1
        or forecast_models[0] != advanced_winner
    ):
        st.error(
            "Forecast files and model evaluation do not "
            "agree. Rerun advanced_forecast.py."
        )
        st.stop()

    # -------------------------------------
    # 2. Display summary metrics
    # -------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Winning model",
        advanced_winner.replace("_", " ").title(),
    )

    c2.metric(
        "Seven-day MAE",
        f"{winner_mae:,.0f}",
    )

    c3.metric(
        "Seven-day MAPE",
        f"{winner_mape:.2f}%",
    )

    c4.metric(
        "Forecast days",
        str(len(advanced_forecasts)),
    )

    st.info(
        "All workload records are synthetic. "
        "Accuracy statistics describe historical "
        "backtests, not guaranteed future performance."
    )

    st.divider()

    # -------------------------------------
    # 3. Compare all three models
    # -------------------------------------

    st.subheader("Three-Model Performance")

    st.write(
        "The best model is selected using the lowest "
        "overall seven-day Mean Absolute Error."
    )

    display_scores = advanced_scores[
        ["model", "evaluations", "mae", "mape"]
    ].copy()

    display_scores.columns = [
        "Model",
        "Comparisons",
        "MAE (records)",
        "MAPE (%)",
    ]

    st.dataframe(
        display_scores.round(2),
        hide_index=True,
    )

    st.subheader("Forecast error by model")

    st.bar_chart(
        advanced_scores,
        x="model",
        y="mae",
        horizontal=True,
    )

    st.caption(
        "Lower MAE indicates smaller historical "
        "forecasting errors."
    )

    # -------------------------------------
    # 4. Compare errors by horizon
    # -------------------------------------

    st.divider()
    st.subheader("Accuracy Across Seven Days")

    horizon_comparison = (
        advanced_horizons
        .pivot(
            index="horizon",
            columns="model",
            values="mae",
        )
        .reset_index()
    )

    st.line_chart(
        horizon_comparison,
        x="horizon",
        y=[
            "previous_day",
            "previous_week",
            "weekday_median",
        ],
    )

    st.caption(
        "The chart shows how prediction error changes "
        "from one day ahead to seven days ahead."
    )

    # -------------------------------------
    # 5. Forecast chart with error bands
    # -------------------------------------

    st.divider()
    st.subheader("Forecast With Historical Error Bands")

    # Shaded lower-to-upper range
    uncertainty_area = (
        alt.Chart(advanced_forecasts)
        .mark_area(
            color="#277E87",
            opacity=0.18,
        )
        .encode(
            x=alt.X(
                "forecast_date:T",
                title="Forecast date",
            ),
            y=alt.Y(
                "lower_bound:Q",
                title="Records processed",
                scale=alt.Scale(zero=False),
            ),
            y2="upper_bound:Q",
        )
    )

    # Central forecast line
    forecast_line = (
        alt.Chart(advanced_forecasts)
        .mark_line(
            color="#277E87",
            strokeWidth=3,
            point=True,
        )
        .encode(
            x=alt.X(
                "forecast_date:T",
                title="Forecast date",
            ),
            y=alt.Y(
                "predicted_records:Q",
                title="Records processed",
            ),
            tooltip=[
                alt.Tooltip(
                    "forecast_date:T",
                    title="Date",
                ),
                alt.Tooltip(
                    "predicted_records:Q",
                    title="Prediction",
                    format=",.0f",
                ),
                alt.Tooltip(
                    "lower_bound:Q",
                    title="Lower estimate",
                    format=",.0f",
                ),
                alt.Tooltip(
                    "upper_bound:Q",
                    title="Upper estimate",
                    format=",.0f",
                ),
            ],
        )
    )

    combined_chart = (
        uncertainty_area + forecast_line
    ).properties(height=360)

    st.altair_chart(
        combined_chart,
        width="stretch",
    )

    st.caption(
        "Shaded regions use the historical 90th "
        "percentile of absolute errors at each horizon. "
        "These are exploratory error bands, not "
        "validated 90% prediction intervals."
    )

    # -------------------------------------
    # 6. Display detailed forecast values
    # -------------------------------------

    st.subheader("Seven-Day Forecast Details")

    st.dataframe(
        advanced_forecasts,
        hide_index=True,
    )

    st.download_button(
        "Download advanced seven-day forecast",
        data=ADVANCED_FORECAST_FILE.read_bytes(),
        file_name="signalbench_advanced_forecast.csv",
        mime="text/csv",
    )

    # -------------------------------------
    # 7. Evaluation information
    # -------------------------------------

    st.divider()

    st.subheader("Evaluation Methodology")

    origins = advanced_backtest[
        "origin_date"
    ].nunique()

    st.write(f"Historical starting points: {origins}")
    st.write(
        f"Total prediction comparisons: "
        f"{len(advanced_backtest)}"
    )
    st.write("Forecast horizon: seven days")
    st.write("Model selection metric: overall MAE")

    st.caption(
        "Rolling backtest windows overlap. "
        "Model selection and error-band estimation "
        "use the same synthetic historical dataset. "
        "Independent coverage validation remains pending."
    )

# -----------------------------------------
# 9. Footer
# -----------------------------------------

st.divider()

st.caption(
    "SignalBench | Predictive Data Engineering | "
    "Local demonstration"
)
