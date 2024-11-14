import os
import sqlite3
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Alpha Vantage API key
OILPRICE_API_KEY = os.getenv('OILPRICE_API_KEY')

# List of URLs to scrape
URLS = [
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg',
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg/2',
    'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg/3'
]

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the database file
DB_PATH = os.path.join(SCRIPT_DIR, 'prices.db')

def fetch_brent_prices():
    try:
        # Fetch the exchange rate dynamically
        exchange_rate_response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        exchange_rate_response.raise_for_status()
        exchange_rates = exchange_rate_response.json()
        usd_to_sek = exchange_rates['rates']['SEK']
        
        url = 'https://api.oilpriceapi.com/v1/prices/latest'
        headers = {
            'Authorization': f'Token {OILPRICE_API_KEY}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()
        
        # Extract the relevant data from the response
        price_data = data.get('data', {})
        price_per_gallon = price_data.get('price')
        created_at = price_data.get('created_at')
        
        # Convert the created_at field to a datetime object
        date = pd.to_datetime(created_at)
        
        # Convert the price from per gallon to per litre
        price_per_litre = price_per_gallon / (158.987)
        
        # Convert the price from USD to SEK
        price_per_litre_sek = price_per_litre * usd_to_sek
        
        # Create a DataFrame with the extracted data
        brent_prices = [{'date': date, 'price': price_per_litre_sek}]
        df = pd.DataFrame(brent_prices)
        
        # Sort the DataFrame by date in descending order
        df = df.sort_values(by='date', ascending=False)
        
        # Get the most recent date with data
        if not df.empty:
            return df.iloc[0:1]  # Return a DataFrame with the most recent row
        else:
            return pd.DataFrame()  # Return an empty DataFrame if no data is available
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def create_database():
    # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
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
    conn.commit()
    conn.close()

def insert_gas_prices():
    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get today's date in the format %d/%m
    today_str = datetime.today().strftime('%d/%m')

    for url in URLS:
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
                station_details = columns[0].find(text=True, recursive=False).strip()
                price_tag = columns[1].find('b')
                date_tag = columns[1].find('small') 

                if brand_tag and price_tag and date_tag:
                    brand = brand_tag.get_text(strip=True)
                    station = station_details.strip()
                    
                    # Extract and clean the price
                    price = price_tag.get_text(strip=True)
                    price = price.replace('kr', '').replace(',', '.').strip()
                    
                    date = date_tag.get_text(strip=True)
                    
                    # Exclude the row if the date is not today
                    if date != today_str:
                        continue
                    
                    # Extract the date and add the current year
                    date_with_year = f"{date}/{datetime.now().year}"                
                        
                    # Log the row before insertion
                    print(f"Inserting row: Brand={brand}, Station={station}, Price={price}, Date={date_with_year}")    
                    
                    # Insert data into SQLite database
                    c.execute('''
                        INSERT INTO prices (brand, station, price, date)
                        VALUES (?, ?, ?, ?)
                    ''', (brand, station, price, date_with_year))

    conn.commit()
    conn.close()

def insert_brent_prices():
    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Fetch Brent prices and insert into SQLite database
    brent_data = fetch_brent_prices()
    for index, row in brent_data.iterrows():
        c.execute('''
            INSERT INTO prices (brand, station, price, date)
            VALUES (?, ?, ?, ?)
        ''', ('Brent', 'world', f"{row['price']} $", row['date'].strftime('%d/%m/%Y')))

    conn.commit()
    conn.close()

def main():
    print("Fetching and inserting gas prices...")
    create_database()
    insert_gas_prices()
    insert_brent_prices()

if __name__ == "__main__":
    main()