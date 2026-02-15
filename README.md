# ✈️ Flight Search

Local web-based flight search tool that compares prices across multiple travel classes (Economy, Premium Economy, Business) from various travel websites.

## Features

✅ Simple web form for flight searches
✅ Compare Economy, Premium Economy, and Business class prices
✅ Scrapes Kayak for real-time pricing
✅ Easy-to-read table display
✅ Runs locally on your machine (no cloud deployment needed)
✅ Extensible architecture for adding more sources

## Quick Start

1. **Install Chrome Browser** (required for web scraping)
   - Download: https://www.google.com/chrome/

2. **Run the launcher**
   ```
   Double-click: run_search.bat
   ```

3. **Open your browser**
   - Navigate to: http://localhost:5000

4. **Search for flights**
   - Enter origin/destination airports (e.g., SEA, JFK)
   - Select dates and passenger counts
   - Click "Search Flights"

## Usage Examples

### Example Search
- **Origin**: SEA (Seattle)
- **Destination**: JFK (New York JFK)
- **Departure**: 2025-03-15
- **Return**: 2025-03-22
- **Adults**: 2
- **Children**: 0

### Results Table
| Source | Economy | Premium Economy | Business |
|--------|---------|-----------------|----------|
| Kayak  | $450    | $750            | $1,200   |

## Configuration

Edit `flight_search_config.json` to customize:

```json
{
  "headless_browser": true,     // Run browser in background
  "timeout": 45,                // Wait time for page loads (seconds)
  "default_currency": "USD"
}
```

**Note:** Set `headless_browser` to `false` if you want to see the browser window during searches (useful for debugging).

## Requirements

- Python 3.8+
- Chrome Browser
- Windows OS (batch file launcher)

For Linux/Mac users, run directly:
```bash
pip install -r requirements.txt
python app.py
```

## How It Works

1. User enters flight details in web form
2. Flask server receives search request
3. Selenium opens Kayak and performs search
4. Scraper extracts prices for each travel class
5. Results displayed in formatted table
6. User can perform new search

## Project Structure

```
Flight Search/
├── app.py                   # Flask web server
├── scrapers/
│   ├── kayak_scraper.py     # Kayak scraper
│   └── base_scraper.py      # Base class for scrapers
├── templates/
│   ├── index.html           # Search form
│   ├── results.html         # Results table
│   └── error.html           # Error page
├── static/
│   └── styles.css           # Styling
├── flight_search_config.json
├── requirements.txt
└── run_search.bat           # Launcher
```

## Adding More Sources

To add another travel website:

1. Create `scrapers/new_source_scraper.py` extending `BaseScraper`
2. Implement `search_flights()` method
3. Update `app.py` to call new scraper
4. Results automatically appear as new table row

Example:
```python
from scrapers.base_scraper import BaseScraper

class GoogleFlightsScraper(BaseScraper):
    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Google Flights"

    def search_flights(self, origin, destination, depart_date,
                      return_date, adults, children):
        # Implementation here
        pass
```

## Troubleshooting

**"Chrome not found"**
- Install Chrome browser from https://www.google.com/chrome/

**"Module not found"**
- Run: `pip install -r requirements.txt`

**"Timeout waiting for results"**
- Increase `timeout` in config file (default: 45 seconds)
- Check internet connection
- Set `headless_browser: false` to see what's happening

**Scraper returns N/A**
- Kayak HTML structure may have changed
- Check `kayak_scraper.py` selectors need updating
- Run in non-headless mode to debug

**Port 5000 already in use**
- Edit `app.py` and change port number:
  ```python
  app.run(debug=True, host='localhost', port=5001)
  ```

## Known Limitations

- **Web Scraping Fragility**: Kayak's website structure may change, requiring selector updates
- **Rate Limiting**: Too many rapid searches may trigger Kayak's bot detection
- **Price Accuracy**: Prices are estimates from initial search results, not guaranteed booking prices
- **Cabin Class Detection**: Current implementation uses price multipliers; production version would need to interact with cabin class filters

## Safety Features

- Headless browser mode (no distracting windows)
- Graceful error handling with helpful error pages
- Automatic retry on failures (configurable)
- Detailed console logging for debugging

## Future Enhancements

- [ ] Add more sources (Google Flights, Expedia, etc.)
- [ ] Parallel searching across multiple sources
- [ ] Save search history
- [ ] Email notifications for price drops
- [ ] Export results to CSV/Excel
- [ ] Date range searching (flexible dates)
- [ ] One-way flight support

## License

This is a personal project for educational purposes. Please respect the terms of service of scraped websites.

## Support

For issues and questions, refer to `SETUP_INSTRUCTIONS.md` for detailed setup help.
