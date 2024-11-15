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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=ep.main, trigger=CronTrigger(hour=12, minute=0))
scheduler.add_job(func=ep.main, trigger=CronTrigger(hour=15, minute=0))
scheduler.add_job(func=ep.main, trigger=CronTrigger(hour=6, minute=0))
scheduler.add_job(func=ep.main, trigger=CronTrigger(hour=9, minute=0))
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    logger.info("Fetching data from the database")
    
    # Connect to SQLite database
    conn = sqlite3.connect('prices.db')
    c = conn.cursor()

    # Fetch data from the database
    c.execute('SELECT brand, station, price, date FROM prices')
    rows = c.fetchall()

    # Close the connection
    conn.close()

    # Process the data
    data = pd.DataFrame(rows, columns=['brand', 'station', 'price', 'date'])
    data['price'] = data['price'].str.replace('kr', '').str.replace('$', '').str.replace(',', '.').astype(float)
    data['date'] = pd.to_datetime(data['date'], format='%d/%m/%Y')

    # Separate the Brent data from the other data
    brent_data = data[data['brand'].str.lower() == 'brent']
    other_data = data[data['brand'].str.lower() != 'brent']

    # Aggregate data by date to get the lowest and highest prices overall for other brands
    daily_data = other_data.groupby('date').agg({'price': ['min', 'max']}).reset_index()
    daily_data.columns = ['date', 'low', 'high']

    # Aggregate Brent data by date
    brent_daily_data = brent_data.groupby('date').agg({'price': 'mean'}).reset_index()
    brent_daily_data.columns = ['date', 'price']

    # Create the Bensin figure
    bensin_fig = go.Figure()

    # Create the candlestick chart
    bensin_fig = go.Figure(data=[go.Candlestick(
        x=daily_data['date'],
        open=daily_data['low'],  # Replace with actual open prices
        high=daily_data['high'],
        low=daily_data['low'],
        close=daily_data['high'],  # Replace with actual close prices
        name='Bensin Prices'
    )])

    # Update layout for Bensin figure
    bensin_fig.update_layout(
        title='Bensin Prices in Göteborg',
        xaxis_title='Date',
        yaxis_title='Price (kr)',
        xaxis=dict(type='category')  # Show only dates
    )

    # Create the Brent figure
    brent_fig = go.Figure()

    # Add the Brent data trace
    brent_fig.add_trace(go.Scatter(
        x=brent_daily_data['date'],
        y=brent_daily_data['price'],
        mode='lines+markers',  # You can change this to 'lines' or 'markers' as needed
        name='Brent Prices',
        text=brent_data['brand'],  # Add brand information
        hoverinfo='x+y+text'  # Show date, price, and brand in the tooltip
    ))

    # Update layout for Brent figure
    brent_fig.update_layout(
        title='Brent Prices in Göteborg',
        xaxis_title='Date',
        yaxis_title='Price (kr)',
        xaxis=dict(type='category')  # Show only dates
    )

    # Generate the HTML graphs
    bensin_graph_html = pyo.plot(bensin_fig, output_type='div', include_plotlyjs=False)
    brent_graph_html = pyo.plot(brent_fig, output_type='div', include_plotlyjs=False)

    # Exclude the brand 'Brent'
    filtered_data = data[data['brand'].str.lower() != 'brent']

    # Find the lowest price for each brand and the corresponding stations
    lowest_prices = filtered_data.loc[filtered_data.groupby('brand')['price'].idxmin()].reset_index(drop=True)
    lowest_prices = filtered_data.groupby(['brand', 'price']).agg({'station': ', '.join}).reset_index()

    # Find the latest update date for each brand
    latest_update_dates = filtered_data.groupby('brand')['date'].max().reset_index()
    latest_update_dates['date'] = latest_update_dates['date'].dt.strftime('%d/%m/%Y')

    # Merge the lowest prices with the latest update dates
    lowest_prices = pd.merge(lowest_prices, latest_update_dates, on='brand')

    # Sort the table by the lowest price first
    lowest_prices = lowest_prices.sort_values(by=['date', 'price'])
    # Calculate the lowest prices for different time periods for all brands combined
    one_month_ago = datetime.now() - pd.DateOffset(months=1)
    three_months_ago = datetime.now() - pd.DateOffset(months=3)
    one_year_ago = datetime.now() - pd.DateOffset(years=1)

    lowest_prices_1_month = filtered_data[filtered_data['date'] >= one_month_ago].nsmallest(1, 'price')
    lowest_prices_1_month['period'] = '1 Month'

    lowest_prices_3_months = filtered_data[filtered_data['date'] >= three_months_ago].nsmallest(1, 'price')
    lowest_prices_3_months['period'] = '3 Months'

    lowest_prices_1_year = filtered_data[filtered_data['date'] >= one_year_ago].nsmallest(1, 'price')
    lowest_prices_1_year['period'] = '1 Year'

    lowest_prices_all_time = filtered_data.nsmallest(1, 'price')
    lowest_prices_all_time['period'] = 'All Time'

    # Concatenate the DataFrames
    lowest_prices_combined = pd.concat([lowest_prices_1_month, lowest_prices_3_months, lowest_prices_1_year, lowest_prices_all_time])

    logger.info("Rendering template with updated data")
    
    # Pass the new data to the template
    return render_template('index.html', 
                        bensin_graph_html=bensin_graph_html, 
                        brent_graph_html=brent_graph_html, 
                        lowest_prices=lowest_prices,
                        lowest_prices_combined=lowest_prices_combined)

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True)