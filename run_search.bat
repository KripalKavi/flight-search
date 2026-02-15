@echo off
REM Flight Search Launcher
REM Starts Flask web server for local flight searches

echo ============================================================
echo Flight Search Server
echo ============================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

REM Check ChromeDriver (Selenium requirement)
echo Checking Chrome browser...
where chrome >nul 2>&1
if errorlevel 1 (
    echo WARNING: Chrome browser not found
    echo Selenium requires Chrome to be installed
    echo Download from: https://www.google.com/chrome/
)

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed
echo.

REM Start Flask server
echo ============================================================
echo Starting Flight Search Server
echo ============================================================
echo Open your browser to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

python app.py

pause
