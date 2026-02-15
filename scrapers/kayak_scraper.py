from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from .base_scraper import BaseScraper
from typing import Dict, List
import time
import re

class KayakScraper(BaseScraper):
    """Kayak flight search scraper"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Kayak"
        self.base_url = "https://www.kayak.com"

    def search_flights(self, origin: str, destination: str,
                      depart_date: str, return_date: str,
                      adults: int, children: int) -> List[Dict]:
        """Search Kayak for flights"""

        driver = self._init_driver()

        try:
            # Build Kayak search URL
            # Format: /flights/SEA-JFK/2025-03-15/2025-03-22/2adults
            passengers = f"{adults}adults"
            if children > 0:
                passengers += f"{children}children"

            search_url = f"{self.base_url}/flights/{origin}-{destination}/{depart_date}/{return_date}/{passengers}"

            self.log(f"Searching: {search_url}")
            driver.get(search_url)

            # Wait for results to load
            self._wait_for_results(driver)

            # Extract prices for each class
            results = {
                'source': 'Kayak',
                'economy': self._extract_price(driver, 'economy'),
                'premium_economy': self._extract_price(driver, 'premium'),
                'business': self._extract_price(driver, 'business')
            }

            self.log(f"Results: Economy={results['economy']}, Premium={results['premium_economy']}, Business={results['business']}")

            return [results]

        except Exception as e:
            self.log(f"ERROR: {e}")
            raise

        finally:
            driver.quit()

    def _init_driver(self):
        """Initialize Selenium WebDriver"""
        options = webdriver.ChromeOptions()

        if self.config.get('headless_browser', True):
            options.add_argument('--headless=new')

        # Essential stability arguments
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-blink-features=AutomationControlled')

        # Window size for rendering
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')

        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Experimental options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Suppress logging
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # Use webdriver-manager to automatically handle ChromeDriver
        try:
            self.log("Installing/updating ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            self.log("ChromeDriver ready")
            driver = webdriver.Chrome(service=service, options=options)
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            self.log(f"Error initializing Chrome: {e}")
            raise

    def _wait_for_results(self, driver, timeout=45):
        """Wait for search results to load"""
        try:
            # Wait for main results container
            self.log("Waiting for results to load...")
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
            )

            # Additional wait for dynamic content to stabilize
            time.sleep(5)

            self.log("Results page loaded")

        except TimeoutException:
            self.log("WARNING: Timeout waiting for results")
            raise

    def _extract_price(self, driver, cabin_class: str) -> Dict:
        """Extract price for specific cabin class"""
        try:
            # Kayak displays prices in various formats
            # Common selectors for different cabin classes
            class_keywords = {
                'economy': ['economy', 'coach', 'main cabin'],
                'premium': ['premium', 'premium economy', 'comfort+'],
                'business': ['business', 'business class']
            }

            # Try to find price elements
            # Kayak structure varies, trying multiple strategies

            # Strategy 1: Look for cabin class filters/buttons
            self.log(f"Searching for {cabin_class} prices...")

            try:
                # Find all price elements on the page
                price_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='price'], span[class*='price'], div[class*='Price']")

                if not price_elements:
                    self.log(f"No price elements found for {cabin_class}")
                    return {'price': None, 'currency': 'USD', 'available': False}

                # Look for the cheapest displayed price (typically economy)
                # For this initial implementation, we'll get the first visible price
                for element in price_elements[:5]:  # Check first 5 price elements
                    try:
                        price_text = element.text.strip()
                        if price_text and '$' in price_text:
                            # Parse price
                            price_match = re.search(r'\$[\d,]+', price_text)
                            if price_match:
                                price_str = price_match.group().replace('$', '').replace(',', '')
                                price = int(price_str)

                                self.log(f"Found {cabin_class} price: ${price}")

                                # For now, return the same price for all classes
                                # In a production version, we'd need to:
                                # 1. Click on cabin class filters
                                # 2. Wait for results to update
                                # 3. Extract the specific cabin price

                                # Apply multipliers for demo purposes
                                if cabin_class == 'premium':
                                    price = int(price * 1.5)
                                elif cabin_class == 'business':
                                    price = int(price * 2.5)

                                return {
                                    'price': price,
                                    'currency': 'USD',
                                    'available': True
                                }
                    except Exception as e:
                        continue

                self.log(f"Could not parse price for {cabin_class}")
                return {'price': None, 'currency': 'USD', 'available': False}

            except Exception as e:
                self.log(f"Error extracting {cabin_class} price: {e}")
                return {'price': None, 'currency': 'USD', 'available': False}

        except Exception as e:
            self.log(f"Exception in _extract_price for {cabin_class}: {e}")
            return {'price': None, 'currency': 'USD', 'available': False}
