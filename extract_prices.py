import sqlite3

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# Alpha Vantage API key
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

def fetch_brent_prices():
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=BZ=F&apikey={ALPHA_VANTAGE_API_KEY}'
    response = requests.get(url)
    data = response.json()
    time_series = data.get('Time Series (Daily)', {})
    
    brent_prices = []
    for date, prices in time_series.items():
        brent_prices.append({
            'date': pd.to_datetime(date),
            'price': float(prices['4. close'])
        })
    
    return pd.DataFrame(brent_prices)

# List of URLs to scrape
urls = [
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg',
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg/2',
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg/3',
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg/4',
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg/5'
]

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('prices.db')
c = conn.cursor()

# Create table for gas prices
c.execute('''
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY,
        brand TEXT,
        station TEXT,
        price TEXT,
        date TEXT
    )
''')

# Fetch gas prices and insert into SQLite database
dates_fetched = set()
for url in urls:
    # Send a GET request to the URL
    response = requests.get(url)

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract the data
    price_table = soup.find('table', {'id': 'price_table'})
    rows = price_table.find_all('tr')

    for row in rows[1:]:  # Skip the header row
        columns = row.find_all('td')
        if len(columns) > 1:
            # Extract brand and station details
            brand_tag = columns[0].find('b')
            br_tag = columns[0].find('br')
            price_tag = columns[1].find('b')
            date_tag = columns[1].find('small')

            if brand_tag and br_tag and price_tag and date_tag:
                brand = brand_tag.get_text(strip=True)
                station = br_tag.next_sibling.strip()
                price = price_tag.get_text(strip=True)
                date = date_tag.get_text(strip=True)
                
                # Insert data into SQLite database
                c.execute('''
                    INSERT INTO prices (brand, station, price, date)
                    VALUES (?, ?, ?, ?)
                ''', (brand, station, price, date))
                
                # Add date to the set of fetched dates
                dates_fetched.add(pd.to_datetime(date, format='%d/%m'))

# Fetch Brent prices and insert into SQLite database for the fetched dates
brent_data = fetch_brent_prices()
for index, row in brent_data.iterrows():
    if row['date'] in dates_fetched:
        c.execute('''
            INSERT INTO prices (brand, station, price, date)
            VALUES (?, ?, ?, ?)
        ''', ('Brent', 'world', f"{row['price']} kr", row['date'].strftime('%d/%m')))

# Commit the transaction and close the connection
conn.commit()
conn.close()