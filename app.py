import atexit
import logging
import sqlite3
from datetime import datetime

import extract_prices as ep
import pandas as pd
import plotly.graph_objs as go
import plotly.offline as pyo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, render_template

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the scheduler
scheduler = BackgroundScheduler()
for hour in range(24):
    scheduler.add_job(
        func=ep.insert_gas_prices, trigger=CronTrigger(hour=hour, minute=0)
    )
scheduler.add_job(func=ep.insert_brent_prices, trigger=CronTrigger(hour=6, minute=0))
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


def fetch_data_from_db(query):
    conn = sqlite3.connect(ep.DB_PATH)
    c = conn.cursor()
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    return rows


def process_gas_data(gas_rows):
    gas_data = pd.DataFrame(
        gas_rows, columns=["brand", "station", "price", "created_at"]
    )
    gas_data["price"] = gas_data["price"].astype(float)
    gas_data["created_at"] = pd.to_datetime(
        gas_data["created_at"], format="%Y-%m-%d %H:%M:%S"
    )
    return gas_data


def process_brent_data(brent_rows):
    brent_data = pd.DataFrame(brent_rows, columns=["price", "created_at"])
    brent_data["price"] = brent_data["price"].str.replace(" $", "").astype(float)
    brent_data["created_at"] = pd.to_datetime(
        brent_data["created_at"], format="%Y-%m-%d %H:%M:%S"
    )
    return brent_data


def create_bensin_figure(daily_data):
    bensin_fig = go.Figure(
        data=[
            go.Candlestick(
                x=daily_data["date"],
                open=daily_data["low"],
                high=daily_data["high"],
                low=daily_data["low"],
                close=daily_data["high"],
                name="Bensin Prices",
            )
        ]
    )
    bensin_fig.update_layout(
        title="Bensin Prices in Göteborg",
        xaxis_title="Date",
        yaxis_title="Price (kr)",
        xaxis=dict(type="category"),
    )
    return bensin_fig


def create_brent_figure(brent_daily_data):
    brent_fig = go.Figure()
    brent_fig.add_trace(
        go.Scatter(
            x=brent_daily_data["date"],
            y=brent_daily_data["price"],
            mode="lines+markers",
            name="Brent Prices",
            text=brent_daily_data["price"],
            hoverinfo="x+y+text",
        )
    )
    brent_fig.update_layout(
        title="Brent Prices in Göteborg",
        xaxis_title="Date",
        yaxis_title="Price (kr)",
        xaxis=dict(type="category"),
    )
    return brent_fig


def get_lowest_prices(gas_data):
    # Get today's date
    today = datetime.now().date()

    # Filter the data for only today's prices
    todays_data = gas_data[gas_data["created_at"].dt.date == today]

    # Combine stations for the same brand, price, and created_at
    todays_data["stations"] = todays_data.groupby(["brand", "price", "created_at"])[
        "station"
    ].transform(lambda x: ", ".join(x))

    # Find the lowest prices for each brand
    lowest_prices_idx = todays_data.groupby("brand")["price"].idxmin()
    lowest_prices = todays_data.loc[lowest_prices_idx].reset_index(drop=True)

    # Format the created_at column
    lowest_prices["created_at"] = lowest_prices["created_at"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Select relevant columns and remove duplicates
    lowest_prices = lowest_prices[
        ["brand", "price", "station", "stations", "created_at"]
    ].drop_duplicates()

    return lowest_prices.sort_values(by=["price"])


def get_lowest_prices_combined(gas_data):
    periods = {
        "1 Month": datetime.now() - pd.DateOffset(months=1),
        "3 Months": datetime.now() - pd.DateOffset(months=3),
        "1 Year": datetime.now() - pd.DateOffset(years=1),
        "All Time": None,
    }
    lowest_prices_combined = []
    for period, date in periods.items():
        if date:
            data = gas_data[gas_data["created_at"] >= date]
        else:
            data = gas_data
        lowest_price = data.nsmallest(1, "price")
        lowest_price["period"] = period
        lowest_prices_combined.append(lowest_price)
    return pd.concat(lowest_prices_combined)


@app.route("/")
def index():
    logger.info("Fetching data from the database")

    gas_rows = fetch_data_from_db(
        "SELECT brand, station, price, created_at FROM gas_prices"
    )
    brent_rows = fetch_data_from_db("SELECT price, created_at FROM brent_prices")

    gas_data = process_gas_data(gas_rows)
    brent_data = process_brent_data(brent_rows)

    daily_data = (
        gas_data.groupby("created_at").agg({"price": ["min", "max"]}).reset_index()
    )
    daily_data.columns = ["date", "low", "high"]

    brent_daily_data = (
        brent_data.groupby("created_at").agg({"price": "mean"}).reset_index()
    )
    brent_daily_data.columns = ["date", "price"]

    bensin_fig = create_bensin_figure(daily_data)
    brent_fig = create_brent_figure(brent_daily_data)

    bensin_graph_html = pyo.plot(bensin_fig, output_type="div", include_plotlyjs=False)
    brent_graph_html = pyo.plot(brent_fig, output_type="div", include_plotlyjs=False)

    lowest_prices = get_lowest_prices(gas_data)
    lowest_prices_combined = get_lowest_prices_combined(gas_data)

    logger.info("Rendering template with updated data")

    return render_template(
        "index.html",
        bensin_graph_html=bensin_graph_html,
        brent_graph_html=brent_graph_html,
        lowest_prices=lowest_prices,
        lowest_prices_combined=lowest_prices_combined,
    )


if __name__ == "__main__":
    logger.info("Starting Flask application")
    app.run(debug=True)
