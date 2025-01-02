import os
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests_html import HTMLSession

# Load environment variables from .env file
load_dotenv()

# Alpha Vantage API key
OILPRICE_API_KEY = os.getenv('OILPRICE_API_KEY')

# Base URL for scraping
BASE_URL = 'https://bensinpriser.nu/stationer/95/vastra-gotalands-lan/goteborg'

# Number of pages to scrape
NUM_PAGES = 3

# Generate the list of URLs dynamically
URLS = [f"{BASE_URL}/{i}" if i > 1 else BASE_URL for i in range(1, NUM_PAGES + 1)]

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the database file
DB_PATH = os.path.join(SCRIPT_DIR, 'prices.db')

# Function to renew session ID using requests_html
def renew_session_id(base_url):
    session = HTMLSession()

    # Perform the request
    response = session.get(base_url)

    # Check if login was successful
    if response.status_code == 200:
        # Extract the session ID from the cookies
        session_id = session.cookies.get("PHPSESSID")  # Replace with the actual cookie name
        if session_id:
            print("New session ID:", session_id)
            return session_id
        else:
            print("Failed to retrieve session ID.")
            return None
    else:
        print("Login failed with status code:", response.status_code)
        return None

def fetch_brent_prices():
    try:
        print("Fetching and inserting brent prices...")
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
        CREATE TABLE IF NOT EXISTS gas_prices (
            id INTEGER PRIMARY KEY,
            brand TEXT,
            station TEXT,
            price TEXT,
            date TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    # Create table for Brent prices
    c.execute('''
        CREATE TABLE IF NOT EXISTS brent_prices (
            id INTEGER PRIMARY KEY,
            price TEXT,
            date TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    conn.commit()
    conn.close()

def insert_gas_prices():
    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("Fetching and inserting gas prices...")

    # Get today's date in the format %d/%m
    today_str = datetime.today().strftime('%d/%m')
    
    yesterday = datetime.today() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%d/%m')

    all_data = []
    
    php_session_id= renew_session_id(BASE_URL)

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.7",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "cookie": f"PHPSESSID={php_session_id}",
        "dnt": "1",
        "priority": "u=0, i",
        "referer": "https://bensinpriser.nu/stationer/98/vastra-gotalands-lan/goteborg",
        "sec-ch-ua": "\"Brave\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
        "sec-ch-ua-arch": "\"x86\"",
        "sec-ch-ua-bitness": "\"64\"",
        "sec-ch-ua-full-version-list": "\"Brave\";v=\"131.0.0.0\", \"Chromium\";v=\"131.0.0.0\", \"Not_A Brand\";v=\"24.0.0.0\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-model": "\"\"",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-ch-ua-platform-version": "\"10.0.0\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "cross-site",
        "sec-fetch-user": "?1",
        "sec-gpc": "1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }

    for url in URLS:
        print(f"Fetching data from URL: {url}")
        
        # Define the proxy settings
        proxies = {
            "http": "http://host.docker.internal:40000",
            "https": "http://host.docker.internal:40000"
        }
        # Send a GET request to the URL
        response = requests.get(url, headers=headers, proxies=proxies)

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
                    parts = date.split('/')
                    if len(parts[0]) == 1:
                        parts[0] = parts[0].zfill(2)
                    date = '/'.join(parts)
                    
                    # Exclude the row if the date is not today
                    if date not in (today_str):
                        continue
                    
                    # Extract the date and add the current year
                    date_with_year = f"{date}/{datetime.now().year}"                
                        
                    # Append the data to the list
                    all_data.append((brand, station, price , date_with_year))

    # Create a dictionary to store the latest data for each station
    latest_data = {}
    for data in all_data:
        brand, station, price, date_with_year = data
        if station not in latest_data or latest_data[station][3] < date_with_year:
            latest_data[station] = data

    # Insert the latest data for each station into the database
    for data in latest_data.values():
        brand, station, price, date_with_year = data
        
        # Insert a new record
        c.execute('''
            INSERT INTO gas_prices (brand, station, price, date)
            VALUES (?, ?, ?, ?)
        ''', (brand, station, price, date_with_year))
        print(f"Inserted row: Brand={brand}, Station={station}, Price={price}, Date={date_with_year}")

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
            INSERT INTO brent_prices (price, date)
            VALUES (?, ?)
        ''', (f"{row['price']} $", row['date'].strftime('%d/%m/%Y')))

    conn.commit()
    conn.close()

def main():
    print("Fetching and inserting gas prices...")
    create_database()
    insert_gas_prices()
    insert_brent_prices()

if __name__ == "__main__":
    main()