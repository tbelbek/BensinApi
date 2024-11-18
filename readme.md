# BensinApi

BensinApi is a Flask-based web application that tracks and displays gas and Brent oil prices in Göteborg. The application scrapes gas prices from various sources and fetches Brent oil prices using an API. The data is stored in a SQLite database and visualized using Plotly.

## Features

- Scrapes gas prices from multiple sources.
- Fetches Brent oil prices using the Alpha Vantage API.
- Stores data in a SQLite database.
- Displays the lowest gas prices by brand.
- Visualizes gas and Brent oil prices using Plotly.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/tbelbek/BensinApi.git
    cd BensinApi
    ```

2. Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

4. Create a `.env` file and add your Alpha Vantage API key:
    ```env
    OILPRICE_API_KEY=your_api_key_here
    ```

5. Initialize the database:
    ```bash
    python extract_prices.py
    ```

## Usage

1. Run the Flask application:
    ```bash
    python app.py
    ```

2. Open your web browser and navigate to `http://127.0.0.1:5000/`.

## Project Structure

- `app.py`: Main Flask application file.
- `extract_prices.py`: Script to scrape gas prices and fetch Brent oil prices.
- `templates/index.html`: HTML template for the web application.
- `prices.db`: SQLite database file.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

This project is licensed under the MIT License.