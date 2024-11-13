from flask import Flask, render_template
import sqlite3
import plotly.graph_objs as go
import plotly.offline as pyo
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
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
    data['price'] = data['price'].str.replace('kr', '').str.replace(',', '.').astype(float)
    data['date'] = pd.to_datetime(data['date'], format='%d/%m')

    # Aggregate data by date to get the lowest and highest prices overall
    daily_data = data.groupby('date').agg({'price': ['min', 'max']}).reset_index()
    daily_data.columns = ['date', 'low', 'high']

    # Create the candlestick chart
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=daily_data['date'],
        open=daily_data['low'],
        high=daily_data['high'],
        low=daily_data['low'],
        close=daily_data['high'],
        name='Prices'
    ))

    # Update layout
    fig.update_layout(
        title='Gas Prices in Göteborg',
        xaxis_title='Date',
        yaxis_title='Price (kr)',
        template='plotly_dark'
    )

    # Generate the HTML graph
    graph_html = pyo.plot(fig, output_type='div', include_plotlyjs=False)

    return render_template('index.html', graph_html=graph_html)


if __name__ == '__main__':
    app.run(debug=True)