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

            # Store the base search URL for cabin class variations
            base_search_url = driver.current_url.split('?')[0]
            self.base_search_url = base_search_url  # Store for use in cabin filter method

            # Extract economy results (default)
            self.log("Extracting Economy results...")
            economy_result = self._extract_cabin_class_results(driver, 'economy')

            # Apply premium economy filter and extract
            self.log("Applying Premium Economy filter...")
            premium_result = self._apply_cabin_filter_and_extract(driver, 'premium')

            # Apply business class filter and extract
            self.log("Applying Business Class filter...")
            business_result = self._apply_cabin_filter_and_extract(driver, 'business')

            results = {
                'source': 'Kayak',
                'economy': economy_result,
                'premium_economy': premium_result,
                'business': business_result
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

    def _parse_stops_text(self, text: str) -> tuple:
        """
        Parse stops text to (count, display_string)

        Examples:
        "nonstop" -> (0, "Nonstop")
        "1 stop" -> (1, "1 stop")
        "2+ stops" -> (2, "2+ stops")
        """
        text_lower = text.lower().strip()

        # Nonstop variants
        if any(term in text_lower for term in ['nonstop', 'non-stop', 'direct']):
            return (0, 'Nonstop')

        # Extract number
        match = re.search(r'(\d+)', text)
        if match:
            count = int(match.group(1))
            return (count, text.strip())

        return (None, 'Not available')

    def _unavailable_result(self) -> Dict:
        """Return structure for unavailable cabin class"""
        return {
            'price': None,
            'currency': 'USD',
            'available': False,
            'stops': None,
            'stops_display': 'Not available',
            'airline': 'N/A',
            'is_best_deal': False
        }

    def _extract_cabin_class_results(self, driver, cabin_class: str) -> Dict:
        """Extract best result for current cabin class view (prioritize nonstop)"""
        # Extract multiple flights to find the best one
        flight_results = self._extract_flight_results(driver, count=10)

        if not flight_results:
            return self._unavailable_result()

        # Sort by: 1) Nonstop first, 2) Fewest stops, 3) Lowest price
        def sort_key(flight):
            stops = flight.get('stops')
            if stops is None:
                stops = 999  # Treat unknown as worst
            price = flight.get('price', 999999)
            return (stops, price)

        flight_results.sort(key=sort_key)

        best_flight = flight_results[0]
        self.log(f"  Selected best option: {best_flight['airline']}, ${best_flight['price']}, {best_flight['stops_display']}")

        return best_flight

    def _apply_cabin_filter_and_extract(self, driver, cabin_class: str) -> Dict:
        """Apply cabin class filter by modifying URL path (Kayak format)"""
        try:
            # Kayak uses cabin class in URL path, not query parameters
            # Format: /flights/SEA-IAD/2026-02-24/2026-02-26/premium
            # Use stored base URL (economy URL) not current URL
            base_url = getattr(self, 'base_search_url', driver.current_url.split('?')[0])

            # Cabin class path segments for Kayak
            cabin_paths = {
                'premium': 'premium',
                'business': 'business'
            }

            cabin_path = cabin_paths.get(cabin_class)
            if not cabin_path:
                self.log(f"  No URL path defined for {cabin_class}")
                return self._unavailable_result()

            # Replace passenger segment with cabin class
            # Example: /flights/SEA-IAD/2026-02-24/2026-02-26/1adults -> .../premium
            url_parts = base_url.rstrip('/').split('/')

            # The last segment should be passengers (e.g., "1adults")
            if len(url_parts) >= 6 and 'adult' in url_parts[-1].lower():
                url_parts[-1] = cabin_path
            else:
                # If we can't find passengers, append cabin class
                url_parts.append(cabin_path)

            new_url = '/'.join(url_parts) + '?sort=bestflight_a'
            self.log(f"  Loading {cabin_class} results: {new_url}")

            try:
                driver.get(new_url)

                # Wait for results with shorter timeout
                self._wait_for_results(driver, timeout=30)

                # Extract and return
                result = self._extract_cabin_class_results(driver, cabin_class)

                if result['available']:
                    self.log(f"  Successfully extracted {cabin_class} results")
                else:
                    self.log(f"  No results found for {cabin_class}")

                return result

            except Exception as e:
                self.log(f"  Failed to load {cabin_class} results: {e}")
                return self._unavailable_result()

        except Exception as e:
            self.log(f"Error applying {cabin_class} filter: {e}")
            return self._unavailable_result()

    def _extract_flight_results(self, driver, count: int = 3) -> List[Dict]:
        """Extract multiple flight results from the page (production-ready)"""
        results = []
        self.log(f"Extracting up to {count} flight results...")

        try:
            # Find flight result containers - Kayak uses various class names
            # Try multiple selectors
            selectors = [
                "div[class*='resultWrapper']",
                "div[class*='result-item']",
                "div[class*='Inner']",
                "div[data-resultid]"
            ]

            flight_containers = []
            for selector in selectors:
                flight_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if flight_containers:
                    self.log(f"Found {len(flight_containers)} flight containers using selector: {selector}")
                    break

            if not flight_containers:
                self.log("No flight containers found, falling back to simple extraction")
                # Fallback: extract single result
                simple_result = self._extract_simple_result(driver)
                if simple_result['available']:
                    results.append(simple_result)
                return results

            # Extract from each container
            for i, container in enumerate(flight_containers[:count]):
                try:
                    self.log(f"Processing flight result {i+1}...")

                    # Extract price
                    price = None
                    price_elements = container.find_elements(By.CSS_SELECTOR, "div[class*='price'], span[class*='price']")
                    for elem in price_elements:
                        price_text = elem.text.strip()
                        if price_text and '$' in price_text:
                            price_match = re.search(r'\$[\d,]+', price_text)
                            if price_match:
                                price = int(price_match.group().replace('$', '').replace(',', ''))
                                self.log(f"  Price: ${price}")
                                break

                    if not price:
                        continue

                    # Extract airline
                    airline = 'Unknown'
                    # Look for airline logo
                    airline_imgs = container.find_elements(By.CSS_SELECTOR, "img[alt], img[class*='logo'], img[class*='airline']")
                    for img in airline_imgs:
                        alt = img.get_attribute('alt')
                        if alt and len(alt) > 0 and len(alt) < 50:
                            # Clean up alt text
                            airline = alt.replace('logo', '').replace('Logo', '').strip()
                            if airline and airline.lower() not in ['', 'flight', 'plane']:
                                self.log(f"  Airline: {airline}")
                                break

                    # If no airline from logo, try text elements
                    if airline == 'Unknown':
                        airline_texts = container.find_elements(By.CSS_SELECTOR, "div[class*='airline'], span[class*='carrier'], div[class*='carrier']")
                        for elem in airline_texts:
                            text = elem.text.strip()
                            if text and len(text) > 0 and len(text) < 30:
                                airline = text
                                self.log(f"  Airline: {airline}")
                                break

                    # Extract stops
                    stops_count = None
                    stops_display = 'Not available'
                    stops_texts = container.find_elements(By.XPATH, ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'stop') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nonstop')]")
                    for elem in stops_texts:
                        text = elem.text.strip()
                        if text:
                            stops_count, stops_display = self._parse_stops_text(text)
                            if stops_count is not None:
                                self.log(f"  Stops: {stops_display}")
                                break

                    # Add result
                    results.append({
                        'price': price,
                        'currency': 'USD',
                        'available': True,
                        'stops': stops_count,
                        'stops_display': stops_display,
                        'airline': airline,
                        'is_best_deal': False
                    })

                except Exception as e:
                    self.log(f"  Error extracting from container {i+1}: {e}")
                    continue

        except Exception as e:
            self.log(f"Error in _extract_flight_results: {e}")

        self.log(f"Extracted {len(results)} flight results")
        return results

    def _extract_simple_result(self, driver) -> Dict:
        """Simple fallback extraction method"""
        try:
            # Extract price
            price = None
            price_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='price'], span[class*='price']")
            for elem in price_elements[:5]:
                price_text = elem.text.strip()
                if price_text and '$' in price_text:
                    price_match = re.search(r'\$[\d,]+', price_text)
                    if price_match:
                        price = int(price_match.group().replace('$', '').replace(',', ''))
                        break

            if not price:
                return self._unavailable_result()

            # Extract airline
            airline = 'Unknown'
            airline_imgs = driver.find_elements(By.CSS_SELECTOR, "img[alt*='logo'], img[alt]")
            for img in airline_imgs[:5]:
                alt = img.get_attribute('alt')
                if alt and len(alt) > 0 and len(alt) < 50:
                    airline = alt.replace('logo', '').replace('Logo', '').strip()
                    if airline:
                        break

            # Extract stops
            stops_count = None
            stops_display = 'Not available'
            stops_elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'stop') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nonstop')]")
            for elem in stops_elements[:3]:
                text = elem.text.strip()
                if text:
                    stops_count, stops_display = self._parse_stops_text(text)
                    if stops_count is not None:
                        break

            return {
                'price': price,
                'currency': 'USD',
                'available': True,
                'stops': stops_count,
                'stops_display': stops_display,
                'airline': airline,
                'is_best_deal': False
            }

        except Exception as e:
            self.log(f"Error in simple extraction: {e}")
            return self._unavailable_result()

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

