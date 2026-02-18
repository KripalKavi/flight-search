from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
from pathlib import Path
from scrapers.kayak_scraper import KayakScraper

app = Flask(__name__)

def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def load_config(config_path: str = "flight_search_config.json") -> dict:
    config_file = Path(config_path)
    if not config_file.exists():
        return {
            "headless_browser": True,
            "timeout": 30,
            "default_currency": "USD"
        }
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    """Render search form"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Process search and return results"""
    try:
        # Extract form data
        origin = request.form.get('origin').upper()
        destination = request.form.get('destination').upper()
        depart_date = request.form.get('depart_date')
        return_date = request.form.get('return_date')
        adults = int(request.form.get('adults', 1))
        children = int(request.form.get('children', 0))

        log(f"Search request: {origin} -> {destination}, {depart_date} to {return_date}")

        # Load config
        config = load_config()

        # Initialize scraper
        scraper = KayakScraper(config)

        # Perform search
        results = scraper.search_flights(
            origin=origin,
            destination=destination,
            depart_date=depart_date,
            return_date=return_date,
            adults=adults,
            children=children
        )

        log(f"Search completed: {len(results)} results found")

        return render_template('results.html', results=results,
                             search_params={
                                 'origin': origin,
                                 'destination': destination,
                                 'depart_date': depart_date,
                                 'return_date': return_date,
                                 'adults': adults,
                                 'children': children
                             })

    except Exception as e:
        log(f"ERROR: {e}")
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    log("="*60)
    log("Flight Search Server Starting")
    log("="*60)
    log("Open your browser to: http://localhost:5000")
    log("Press Ctrl+C to stop the server")
    log("="*60)

    app.run(debug=True, host='localhost', port=5000)
