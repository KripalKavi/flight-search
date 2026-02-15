# Flight Search - Setup Instructions

## Prerequisites

### 1. Python 3.8+
Check if Python is installed:
```bash
python --version
```

If not installed:
- Download from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"
- Recommended: Python 3.10 or newer

### 2. Chrome Browser
Selenium requires Chrome for web scraping:
- Download from https://www.google.com/chrome/
- Install the latest version

## Installation Steps

### Step 1: Navigate to Project Directory
```bash
cd "Flight Search"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- **Flask** (web server) - version 3.0.0+
- **Selenium** (web scraping) - version 4.16.0+
- **webdriver-manager** (automatic ChromeDriver setup) - version 4.0.1+

**Installation time:** ~30-60 seconds depending on internet speed

### Step 3: Verify Installation
```bash
python -c "import flask; import selenium; print('✓ All dependencies installed')"
```

You should see: `✓ All dependencies installed`

### Step 4: Test Flask Server
```bash
python app.py
```

You should see:
```
============================================================
Flight Search Server Starting
============================================================
Open your browser to: http://localhost:5000
Press Ctrl+C to stop the server
============================================================
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://localhost:5000
```

### Step 5: Open Browser
Navigate to: http://localhost:5000

You should see the flight search form.

## Configuration (Optional)

Edit `flight_search_config.json`:

```json
{
  "headless_browser": false,  // Set to false to see browser (debugging)
  "timeout": 45,              // Increase if searches timeout
  "default_currency": "USD"
}
```

### Configuration Options

- **headless_browser**:
  - `true` - Browser runs in background (recommended for normal use)
  - `false` - Browser window visible (useful for debugging)

- **timeout**:
  - Default: 45 seconds
  - Increase if you see timeout errors
  - Decrease for faster failures on bad searches

- **default_currency**:
  - Currently only USD supported
  - Future: EUR, GBP, etc.

## Troubleshooting

### Chrome Driver Issues

**Problem**: "chromedriver not found" or "selenium.common.exceptions.SessionNotCreatedException"

**Solution 1**: Update webdriver-manager
```bash
pip install --upgrade webdriver-manager
```

**Solution 2**: Manual ChromeDriver installation
1. Check your Chrome version: `chrome://version/`
2. Download matching ChromeDriver: https://chromedriver.chromium.org/
3. Add to PATH or place in project directory

**Solution 3**: Use webdriver-manager auto-download
```python
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
```

### Port Already in Use

**Problem**: "Address already in use" on port 5000

**Solution**: Change port in `app.py`:
```python
app.run(debug=True, host='localhost', port=5001)  # Change to 5001 or any available port
```

Then access: http://localhost:5001

### Permission Errors

**Problem**: "Permission denied" when installing packages

**Solution 1**: Run Command Prompt as Administrator
- Right-click Command Prompt → "Run as administrator"

**Solution 2**: Use user installation
```bash
pip install --user -r requirements.txt
```

**Solution 3**: Use virtual environment (recommended)
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Import Errors

**Problem**: "ModuleNotFoundError: No module named 'flask'" or similar

**Solution**: Ensure you're in the right environment
```bash
# Check which Python is being used
where python  # Windows
which python  # Linux/Mac

# Reinstall dependencies
pip install -r requirements.txt
```

### Timeout Errors During Search

**Problem**: "Timeout waiting for results" during flight search

**Solution 1**: Increase timeout in config
```json
{
  "timeout": 60  // Increase from 45 to 60 seconds
}
```

**Solution 2**: Run in non-headless mode to see what's happening
```json
{
  "headless_browser": false
}
```

**Solution 3**: Check internet connection
- Make sure you can access https://www.kayak.com in your browser

### Kayak Returns N/A for All Classes

**Problem**: Search completes but all prices show "N/A"

**Possible Causes**:
1. Kayak's HTML structure changed (requires code update)
2. Kayak detected bot and blocked request
3. No flights available for that route/date

**Solution 1**: Run in non-headless mode to debug
```json
{
  "headless_browser": false
}
```

**Solution 2**: Try different search parameters
- Use major airports (SEA, JFK, LAX, ORD)
- Try dates 2-3 weeks in the future
- Verify airport codes are valid

**Solution 3**: Check console logs
- Look for error messages in terminal
- Logs show exact URL being accessed

### Flask Debug Mode Warnings

**Problem**: Flask warns about running in debug mode

**Solution**: This is expected for development. For production, disable debug:
```python
app.run(debug=False, host='localhost', port=5000)
```

## Platform-Specific Notes

### Windows
- Use `run_search.bat` for quick startup
- Chrome typically installed in: `C:\Program Files\Google\Chrome\`
- Python typically installed in: `C:\Users\[username]\AppData\Local\Programs\Python`

### Linux
- Install Chrome: `sudo apt install google-chrome-stable`
- Run directly: `python app.py`
- May need to install `xvfb` for headless mode: `sudo apt install xvfb`

### macOS
- Install Chrome from DMG: https://www.google.com/chrome/
- Run directly: `python app.py`
- May need to allow Chrome in Security & Privacy settings

## Usage

### Starting the Server
```bash
# Option 1: Double-click run_search.bat (Windows)

# Option 2: Command line
python app.py
```

### Performing a Search
1. Open http://localhost:5000
2. Enter origin airport code (e.g., SEA)
3. Enter destination airport code (e.g., JFK)
4. Select departure date
5. Select return date
6. Enter number of adults (1-9)
7. Enter number of children (0-9)
8. Click "Search Flights"
9. Wait for results (typically 15-30 seconds)

### Stopping the Server
- Press `Ctrl+C` in the terminal
- Close the terminal window

## Testing Your Installation

### Test 1: Form Loads
```
1. Start server: python app.py
2. Open: http://localhost:5000
3. Verify: Form displays with all fields
```

### Test 2: Search Submission
```
1. Enter: SEA → JFK
2. Dates: Any future dates
3. Adults: 2
4. Click: Search Flights
5. Verify: Results page loads (even if N/A)
```

### Test 3: Selenium Works
```python
# Run this test script:
from selenium import webdriver
options = webdriver.ChromeOptions()
options.add_argument('--headless=new')
driver = webdriver.Chrome(options=options)
driver.get('https://www.kayak.com')
print(f"Page title: {driver.title}")
driver.quit()
print("✓ Selenium is working")
```

## Success Criteria

You're ready to use the app when:
- ✅ Flask server starts without errors
- ✅ Search form loads at http://localhost:5000
- ✅ Form submission reaches results page
- ✅ Selenium can open Chrome (even if headless)
- ✅ No Python import errors

## Getting Help

### Check Logs
The console shows detailed logs:
```
[2025-02-15 10:30:15] Search request: SEA → JFK, 2025-03-15 to 2025-03-22
[2025-02-15 10:30:15] [Kayak] Searching: https://www.kayak.com/flights/...
[2025-02-15 10:30:18] [Kayak] Waiting for results to load...
[2025-02-15 10:30:25] [Kayak] Results page loaded
```

### Enable Debug Mode
Set `headless_browser: false` in config to see browser window

### Common Search Examples
```
Domestic US:
- SEA → JFK (Seattle to New York)
- LAX → ORD (Los Angeles to Chicago)
- SFO → MIA (San Francisco to Miami)

International:
- JFK → LHR (New York to London)
- LAX → NRT (Los Angeles to Tokyo)
- SFO → CDG (San Francisco to Paris)
```

## Next Steps

After successful installation:
1. Try a test search
2. Experiment with different routes
3. Customize `flight_search_config.json`
4. Review `README.md` for advanced features
5. Consider adding more travel sources

## Performance Tips

- **Faster searches**: Keep `headless_browser: true`
- **Debugging**: Set `headless_browser: false`
- **Multiple searches**: Keep server running between searches
- **Timeout tuning**: Adjust based on your internet speed
