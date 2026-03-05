from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import logging
from pathlib import Path
from scrapers.kayak_scraper import KayakScraper
from scrapers.alaska_scraper import AlaskaScraper
from scrapers.delta_scraper import DeltaScraper

app = Flask(__name__)

# Configure file logging
LOG_FILE = Path(__file__).parent / "flight_search.log"

# Setup logger
def setup_logging():
    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create logger
    logger = logging.getLogger('flight_search')
    logger.setLevel(logging.INFO)

    # File handler (overwrite mode)
    file_handler = logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize logger
logger = setup_logging()

def log(message: str):
    logger.info(message)

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

        # Initialize scrapers
        kayak_scraper = KayakScraper(config)
        alaska_scraper = AlaskaScraper(config)
        delta_scraper = DeltaScraper(config)

        # Perform searches from both sources
        results = []

        # Search Kayak
        # try:
        #     log("Searching Kayak...")
        #     kayak_results = kayak_scraper.search_flights(
        #         origin=origin,
        #         destination=destination,
        #         depart_date=depart_date,
        #         return_date=return_date,
        #         adults=adults,
        #         children=children
        #     )
        #     results.extend(kayak_results)
        #     log(f"Kayak search completed")
        # except Exception as e:
        #     log(f"Kayak search failed: {e}")

        # Search Alaska Airlines
        # try:
        #     log("Searching Alaska Airlines...")
        #     alaska_results = alaska_scraper.search_flights(
        #         origin=origin,
        #         destination=destination,
        #         depart_date=depart_date,
        #         return_date=return_date,
        #         adults=adults,
        #         children=children
        #     )
        #     results.extend(alaska_results)
        #     log(f"Alaska Airlines search completed")
        # except Exception as e:
        #     log(f"Alaska Airlines search failed: {e}")

        # Search Delta
        try:
            log("Searching Delta...")
            delta_results = delta_scraper.search_flights(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                return_date=return_date,
                adults=adults,
                children=children
            )
            results.extend(delta_results)
            log(f"Delta search completed")
        except Exception as e:
            log(f"Delta search failed: {e}")

        log(f"Search completed: {len(results)} results found from {len(results)} sources")

        # Calculate best deal: cheapest option with fewest stops
        def find_best_deal(results):
            best_stops = float('inf')
            best_price = float('inf')
            best_deal = None

            for result in results:
                for cabin_class in ['economy', 'premium_economy', 'business']:
                    cabin_data = result[cabin_class]

                    if not cabin_data['available'] or cabin_data['price'] is None:
                        continue

                    stops = cabin_data.get('stops', float('inf'))
                    if stops is None:
                        stops = float('inf')  # Treat unknown stops as worst

                    price = cabin_data['price']

                    # Priority 1: Fewer stops
                    # Priority 2: Lower price (within same stop count)
                    if (stops < best_stops) or (stops == best_stops and price < best_price):
                        best_stops = stops
                        best_price = price
                        best_deal = {
                            'source': result['source'],
                            'cabin_class': cabin_class,
                            'price': price,
                            'stops': stops,
                            'stops_display': cabin_data.get('stops_display', 'Unknown'),
                            'currency': cabin_data.get('currency', 'USD')
                        }

            return best_deal

        # Calculate best deal
        best_deal_info = find_best_deal(results)

        # Mark the best deal in results
        if best_deal_info:
            for result in results:
                if result['source'] == best_deal_info['source']:
                    result[best_deal_info['cabin_class']]['is_best_deal'] = True

        log(f"Best deal: {best_deal_info}")

        # Debug: Log what's being sent to template
        for result in results:
            log(f"Template data - Economy: ${result['economy']['price']}, Premium: ${result['premium_economy']['price']}, Business: ${result['business']['price']}")

        return render_template('results.html',
                             results=results,
                             best_deal_info=best_deal_info,
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
    log(f"Log file: {LOG_FILE}")
    log("Open your browser to: http://localhost:5000")
    log("Press Ctrl+C to stop the server")
    log("="*60)

    app.run(debug=True, host='localhost', port=5000)
