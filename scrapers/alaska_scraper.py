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

class AlaskaScraper(BaseScraper):
    """Alaska Airlines flight search scraper"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Alaska Airlines"
        self.base_url = "https://www.alaskaair.com"

    def search_flights(self, origin: str, destination: str,
                      depart_date: str, return_date: str,
                      adults: int, children: int) -> List[Dict]:
        """Search Alaska Airlines for flights (both cash and points)"""

        driver = self._init_driver()
        all_results = []

        try:
            # Build base URL
            base_params = (
                f"?O={origin}"
                f"&D={destination}"
                f"&OD={depart_date}"
                f"&DD={return_date}"
                f"&A={adults}"
                f"&RT=true"
                f"&locale=en-us"
            )
            if children > 0:
                base_params += f"&C={children}"

            # Search 1: Cash prices
            cash_url = f"{self.base_url}/search/results{base_params}"
            self.log(f"Searching (Cash): {cash_url}")
            driver.get(cash_url)
            self._wait_for_results(driver)

            self.log("Extracting cash prices from page...")
            economy_cash, premium_cash, business_cash = self._extract_all_cabin_classes(driver, currency='USD')

            cash_results = {
                'source': 'Alaska Airlines (Cash)',
                'payment_type': 'cash',
                'economy': economy_cash,
                'premium_economy': premium_cash,
                'business': business_cash
            }
            self.log(f"Cash Results: Economy=${economy_cash.get('price')}, Premium=${premium_cash.get('price')}, Business=${business_cash.get('price')}")
            all_results.append(cash_results)

            # Search 2: Points/Miles prices
            points_url = f"{self.base_url}/search/results{base_params}&ShoppingMethod=onlineaward"
            self.log(f"Searching (Points): {points_url}")
            driver.get(points_url)
            self._wait_for_results(driver)

            self.log("Extracting points prices from page...")
            economy_points, premium_points, business_points = self._extract_all_cabin_classes(driver, currency='miles')

            points_results = {
                'source': 'Alaska Airlines (Miles)',
                'payment_type': 'miles',
                'economy': economy_points,
                'premium_economy': premium_points,
                'business': business_points
            }
            self.log(f"Points Results: Economy={economy_points.get('price')} miles, Premium={premium_points.get('price')} miles, Business={business_points.get('price')} miles")
            all_results.append(points_results)

            return all_results

        except Exception as e:
            self.log(f"ERROR: {e}")
            # Return unavailable results for both cash and points
            unavailable_cash = {
                'source': 'Alaska Airlines (Cash)',
                'payment_type': 'cash',
                'economy': self._unavailable_result(),
                'premium_economy': self._unavailable_result(),
                'business': self._unavailable_result()
            }
            unavailable_points = {
                'source': 'Alaska Airlines (Miles)',
                'payment_type': 'miles',
                'economy': self._unavailable_result(currency='miles'),
                'premium_economy': self._unavailable_result(currency='miles'),
                'business': self._unavailable_result(currency='miles')
            }
            return [unavailable_cash, unavailable_points]

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

        # Window size - large enough to show Premium and First class prices
        # Alaska hides some prices on smaller screens (responsive design)
        options.add_argument('--window-size=1920,1200')
        options.add_argument('--start-maximized')

        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Experimental options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

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
        """Parse stops text to (count, display_string)"""
        text_lower = text.lower().strip()

        if any(term in text_lower for term in ['nonstop', 'non-stop', 'direct']):
            return (0, 'Nonstop')

        match = re.search(r'(\d+)', text)
        if match:
            count = int(match.group(1))
            return (count, text.strip())

        return (None, 'Not available')

    def _unavailable_result(self, currency: str = 'USD') -> Dict:
        """Return structure for unavailable cabin class"""
        return {
            'price': None,
            'currency': currency,
            'available': False,
            'stops': None,
            'stops_display': 'Not available',
            'airline': 'Alaska Airlines',
            'is_best_deal': False
        }

    def _extract_all_cabin_classes(self, driver, currency: str = 'USD') -> tuple:
        """Extract Main (Economy), Premium, and First Class from same page"""
        try:
            # Alaska shows all fare types on one page: Saver, Main, Premium, First
            # We want: Main (economy), Premium, First (business)
            # Skip: Saver

            economy_result = self._unavailable_result(currency=currency)
            premium_result = self._unavailable_result(currency=currency)
            business_result = self._unavailable_result(currency=currency)

            self.log("Looking for fare type containers...")

            # Scroll down to ensure all content is loaded
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                self.log("Scrolled page to trigger lazy-loaded content")
            except:
                pass

            # Take a screenshot for debugging
            try:
                import os
                screenshot_path = os.path.join(os.path.dirname(__file__), '..', 'alaska_debug.png')
                driver.save_screenshot(screenshot_path)
                self.log(f"Saved debug screenshot to: {screenshot_path}")
            except Exception as e:
                self.log(f"Could not save screenshot: {e}")

            # Debug: Log page title and URL
            self.log(f"Page title: {driver.title}")
            self.log(f"Current URL: {driver.current_url}")

            # Debug: Check if we can find ANY prices on the page
            all_price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
            self.log(f"Found {len(all_price_elements)} elements containing '$'")

            if all_price_elements:
                # Log first few prices found
                for i, elem in enumerate(all_price_elements[:5]):
                    try:
                        self.log(f"  Price element {i+1}: '{elem.text.strip()}'")
                    except:
                        pass

            # Strategy 1: Simple approach - find all prices and try to map them
            fare_types = {
                'main': None,
                'premium': None,
                'first': None
            }

            # Look for any element containing fare type keywords
            self.log("Searching for fare type keywords...")

            # Get all text on page to search
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            self.log(f"Page contains 'Main': {'Main' in page_text}")
            self.log(f"Page contains 'Premium': {'Premium' in page_text}")
            self.log(f"Page contains 'First': {'First' in page_text}")
            self.log(f"Page contains 'Saver': {'Saver' in page_text}")

            # Try to find elements by text
            selectors_to_try = [
                "//*[contains(text(), 'Main')]",
                "//*[contains(text(), 'Premium')]",
                "//*[contains(text(), 'First')]"
            ]

            all_elements = []
            for xpath in selectors_to_try:
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    self.log(f"Found {len(elements)} elements with xpath: {xpath}")
                    all_elements.extend(elements)

            self.log(f"Total elements to check: {len(all_elements)}")

            # SIMPLIFIED APPROACH: Extract prices quickly and map to fare types
            fare_prices = {
                'main': [],
                'premium': [],
                'first': []
            }

            self.log("Searching for fare type selection elements...")

            # Strategy: Find elements with fare type text and look for prices in nearby ancestors (fast)
            # Limit search to first 3 elements of each type for speed

            # Look for Main - try finding containers that have both "Main" and a price
            # Strategy 1: Find elements where parent/ancestor contains both "Main" and price
            try:
                # For cash: look for "$", for miles: look for numbers with commas
                if currency == 'USD':
                    search_pattern = "$"
                    price_regex = r'\$(\d+(?:,\d{3})*)'
                else:
                    search_pattern = "miles"
                    # Miles shown as "20k", "22.5k", "25k" etc. on Alaska points page
                    price_regex = r'(\d+(?:\.\d+)?k)'  # Match numbers with 'k' suffix

                # Find all elements that contain "Main" text (but not "Saver")
                main_containers = driver.find_elements(By.XPATH, f"//*[contains(., 'Main') and not(contains(., 'Saver'))]")
                self.log(f"Found {len(main_containers)} containers with 'Main'")

                for container in main_containers[:5]:
                    container_text = container.text
                    # Only process if text is not too large (avoid whole page)
                    if len(container_text) > 2000:
                        continue
                    # Check if "Main" appears prominently (not just mentioned in passing)
                    if 'Main' in container_text[:200]:  # Main should appear early
                        prices = re.findall(price_regex, container_text)
                        if currency == 'miles':
                            self.log(f"  Checking container (first 200 chars): {container_text[:200]}")
                            self.log(f"  Found {len(prices)} potential mile values: {prices[:5]}")
                        for price_str in prices:
                            # Convert miles format
                            if currency == 'USD':
                                price_val = int(price_str.replace(',', ''))
                            else:  # miles - handle "20k" format
                                if price_str.endswith('k'):
                                    # Convert "20k" to 20000, "22.5k" to 22500
                                    price_val = int(float(price_str[:-1]) * 1000)
                                else:
                                    price_val = int(price_str.replace(',', ''))

                            # Different ranges for cash vs miles
                            if currency == 'USD':
                                if 200 <= price_val <= 1000:
                                    fare_prices['main'].append(price_val)
                                    self.log(f"  Found Main price: ${price_val} (from combined container)")
                                    break
                            else:  # miles
                                if 5000 <= price_val <= 150000:
                                    fare_prices['main'].append(price_val)
                                    self.log(f"  Found Main price: {price_val} miles (from combined container)")
                                    break
                    if fare_prices['main']:
                        break
            except Exception as e:
                self.log(f"  Error in combined search: {e}")

            # Strategy 2: If not found, try traditional ancestor search
            if not fare_prices['main']:
                main_elements = driver.find_elements(By.XPATH, "//*[text()='Main' or contains(text(), 'Main')]")
                self.log(f"Found {len(main_elements)} 'Main' text elements, checking ancestors...")

                if currency == 'USD':
                    price_regex = r'\$(\d+(?:,\d{3})*)'
                    min_val, max_val = 200, 1000
                    unit = "$"
                else:
                    # Miles shown as "20k", "25k" etc.
                    price_regex = r'(\d+(?:\.\d+)?k)'
                    min_val, max_val = 5000, 150000
                    unit = " miles"

                for elem in main_elements[:10]:  # Check more elements
                    try:
                        for level in range(1, 6):  # Check up to 5 levels
                            ancestor = elem.find_element(By.XPATH, "/".join([".."] * level))
                            ancestor_text = ancestor.text
                            if len(ancestor_text) > 2000:  # Skip if too large
                                break
                            if 'Main' in ancestor_text[:300]:  # Main should appear early
                                prices = re.findall(price_regex, ancestor_text)
                                for price_str in prices:
                                    # Convert price format
                                    if currency == 'USD':
                                        price_val = int(price_str.replace(',', ''))
                                    else:  # miles - handle "20k" format
                                        if price_str.endswith('k'):
                                            price_val = int(float(price_str[:-1]) * 1000)
                                        else:
                                            price_val = int(price_str.replace(',', ''))

                                    if min_val <= price_val <= max_val:
                                        fare_prices['main'].append(price_val)
                                        self.log(f"  Found Main price: {unit}{price_val} (level {level})")
                                        break
                            if fare_prices['main']:
                                break
                        if fare_prices['main']:
                            break
                    except:
                        continue

            # Look for Premium
            premium_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Premium') and not(contains(text(), 'Class'))]")
            self.log(f"Found {len(premium_elements)} 'Premium' elements")

            if currency == 'USD':
                price_regex_simple = r'\$[\d,]+'
                min_val, max_val = 100, 5000
                unit_prefix = "$"
            else:
                # Miles shown as "20k", "50k" etc.
                price_regex_simple = r'\d+(?:\.\d+)?k'
                min_val, max_val = 5000, 150000
                unit_prefix = ""

            for elem in premium_elements[:3]:
                try:
                    for level in [1, 2]:
                        ancestor = elem.find_element(By.XPATH, "/".join([".."] * level))
                        prices = re.findall(price_regex_simple, ancestor.text)
                        for price_str in prices:
                            # Convert price format
                            if currency == 'USD':
                                price_val = int(price_str.replace('$', '').replace(',', ''))
                            else:  # miles - handle "50k" format
                                if price_str.endswith('k'):
                                    price_val = int(float(price_str[:-1]) * 1000)
                                else:
                                    price_val = int(price_str.replace(',', ''))

                            if min_val <= price_val <= max_val:
                                fare_prices['premium'].append(price_val)
                                unit = " miles" if currency != 'USD' else ""
                                self.log(f"  Found Premium price: {unit_prefix}{price_val}{unit}")
                                break
                        if fare_prices['premium']:
                            break
                    if fare_prices['premium']:
                        break
                except:
                    continue

            # Look for First
            first_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'First') and not(contains(text(), 'Class'))]")
            self.log(f"Found {len(first_elements)} 'First' elements")

            for elem in first_elements[:3]:
                try:
                    for level in [1, 2]:
                        ancestor = elem.find_element(By.XPATH, "/".join([".."] * level))
                        prices = re.findall(price_regex_simple, ancestor.text)
                        for price_str in prices:
                            # Convert price format
                            if currency == 'USD':
                                price_val = int(price_str.replace('$', '').replace(',', ''))
                            else:  # miles - handle "50k" format
                                if price_str.endswith('k'):
                                    price_val = int(float(price_str[:-1]) * 1000)
                                else:
                                    price_val = int(price_str.replace(',', ''))

                            if min_val <= price_val <= max_val:
                                fare_prices['first'].append(price_val)
                                unit = " miles" if currency != 'USD' else ""
                                self.log(f"  Found First price: {unit_prefix}{price_val}{unit}")
                                break
                        if fare_prices['first']:
                            break
                    if fare_prices['first']:
                        break
                except:
                    continue

            # Pick cheapest for each fare type
            if fare_prices['main']:
                fare_types['main'] = min(fare_prices['main'])
                self.log(f"Selected Main price: ${fare_types['main']}")

            if fare_prices['premium']:
                fare_types['premium'] = min(fare_prices['premium'])
                self.log(f"Selected Premium price: ${fare_types['premium']}")

            if fare_prices['first']:
                fare_types['first'] = min(fare_prices['first'])
                self.log(f"Selected First price: ${fare_types['first']}")

            # IMPORTANT: Validate that we got DIFFERENT prices
            all_found_prices = [p for p in [fare_types.get('main'), fare_types.get('premium'), fare_types.get('first')] if p is not None]
            if len(all_found_prices) != len(set(all_found_prices)):
                self.log("WARNING: Found duplicate prices across fare types - extraction may be inaccurate")
                # If all three are the same, something is wrong - clear them
                if len(set(all_found_prices)) == 1 and len(all_found_prices) == 3:
                    self.log("All three fare types have same price - clearing to show as unavailable")
                    fare_types = {'main': None, 'premium': None, 'first': None}

            # Build results from extracted prices
            if fare_types['main']:
                economy_result = {
                    'price': fare_types['main'],
                    'currency': currency,
                    'available': True,
                    'stops': None,  # Will be extracted separately if needed
                    'stops_display': 'Not available',
                    'airline': 'Alaska Airlines',
                    'is_best_deal': False
                }

            if fare_types['premium']:
                premium_result = {
                    'price': fare_types['premium'],
                    'currency': currency,
                    'available': True,
                    'stops': None,
                    'stops_display': 'Not available',
                    'airline': 'Alaska Airlines',
                    'is_best_deal': False
                }

            if fare_types['first']:
                business_result = {
                    'price': fare_types['first'],
                    'currency': currency,
                    'available': True,
                    'stops': None,
                    'stops_display': 'Not available',
                    'airline': 'Alaska Airlines',
                    'is_best_deal': False
                }

            # Try to extract stops information from the page
            self._extract_stops_info(driver, economy_result, premium_result, business_result)

            return economy_result, premium_result, business_result

        except Exception as e:
            self.log(f"Error extracting cabin classes: {e}")
            return self._unavailable_result(), self._unavailable_result(), self._unavailable_result()

    def _extract_stops_info(self, driver, economy_result, premium_result, business_result):
        """Try to extract stops information from the page"""
        try:
            # Look for stops information on the page
            stops_elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nonstop') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'stop')]")

            if stops_elements:
                stops_text = stops_elements[0].text.strip()
                stops_count, stops_display = self._parse_stops_text(stops_text)

                # Apply to all cabin classes (same flight, different classes)
                if stops_count is not None:
                    for result in [economy_result, premium_result, business_result]:
                        if result.get('available'):
                            result['stops'] = stops_count
                            result['stops_display'] = stops_display
                    self.log(f"  Applied stops info to all classes: {stops_display}")
        except Exception as e:
            self.log(f"Could not extract stops info: {e}")

    def _extract_flight_results(self, driver, count: int = 10) -> List[Dict]:
        """Extract multiple flight results from Alaska Airlines page"""
        results = []
        self.log(f"Extracting up to {count} flight results...")

        try:
            # Alaska Airlines flight result selectors
            # Try multiple selector strategies
            selectors = [
                "div[class*='flight-result']",
                "div[class*='flightResult']",
                "div[class*='flight-card']",
                "div[data-test*='flight']",
                "li[class*='flight']"
            ]

            flight_containers = []
            for selector in selectors:
                flight_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if flight_containers:
                    self.log(f"Found {len(flight_containers)} flight containers using selector: {selector}")
                    break

            if not flight_containers:
                self.log("No flight containers found, trying alternative approach")
                # Fallback: look for any containers with price information
                flight_containers = driver.find_elements(By.XPATH, "//*[contains(text(), '$') and contains(@class, 'price')]/..")
                if flight_containers:
                    self.log(f"Found {len(flight_containers)} containers via price fallback")

            if not flight_containers:
                self.log("Could not find flight results")
                return results

            # Extract from each container
            for i, container in enumerate(flight_containers[:count]):
                try:
                    self.log(f"Processing flight result {i+1}...")

                    # Extract price
                    price = None
                    price_selectors = [
                        "span[class*='price']",
                        "div[class*='price']",
                        "[data-test*='price']",
                        "[class*='amount']"
                    ]

                    for price_sel in price_selectors:
                        price_elements = container.find_elements(By.CSS_SELECTOR, price_sel)
                        for elem in price_elements:
                            price_text = elem.text.strip()
                            if price_text and '$' in price_text:
                                price_match = re.search(r'\$[\d,]+', price_text)
                                if price_match:
                                    price = int(price_match.group().replace('$', '').replace(',', ''))
                                    self.log(f"  Price: ${price}")
                                    break
                        if price:
                            break

                    if not price:
                        continue

                    # Extract airline (Alaska or partner)
                    airline = 'Alaska Airlines'
                    airline_selectors = [
                        "img[alt*='Alaska']",
                        "img[alt*='airline']",
                        "[class*='airline']",
                        "[class*='carrier']"
                    ]

                    for airline_sel in airline_selectors:
                        airline_elements = container.find_elements(By.CSS_SELECTOR, airline_sel)
                        if airline_elements:
                            for elem in airline_elements:
                                alt = elem.get_attribute('alt') if elem.tag_name == 'img' else elem.text
                                if alt and len(alt) > 0 and len(alt) < 50:
                                    airline = alt.strip()
                                    self.log(f"  Airline: {airline}")
                                    break
                            if airline != 'Alaska Airlines':
                                break

                    # Extract stops
                    stops_count = None
                    stops_display = 'Not available'
                    stops_keywords = ['nonstop', 'non-stop', 'direct', 'stop', 'layover']

                    # Look for stops text
                    container_text = container.text.lower()
                    for keyword in stops_keywords:
                        if keyword in container_text:
                            # Try to extract the full stops text
                            stops_elements = container.find_elements(By.XPATH, f".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                            if stops_elements:
                                for elem in stops_elements:
                                    text = elem.text.strip()
                                    if text:
                                        stops_count, stops_display = self._parse_stops_text(text)
                                        if stops_count is not None:
                                            self.log(f"  Stops: {stops_display}")
                                            break
                            if stops_count is not None:
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

    def _wait_for_results(self, driver, timeout=45):
        """Wait for search results to load"""
        try:
            self.log("Waiting for results to load...")

            # Wait for page to load - Alaska Airlines needs time to render all fare types
            # Increased wait time since we need Premium and First prices to appear
            time.sleep(15)

            self.log("Initial wait complete")

            # Explicitly wait for price elements to appear
            try:
                WebDriverWait(driver, 20).until(
                    lambda d: len(d.find_elements(By.XPATH, "//*[contains(text(), '$')]")) >= 3
                )
                self.log("Price elements detected on page")
            except TimeoutException:
                self.log("WARNING: Timeout waiting for price elements, continuing anyway")

            # Check if we're on the right page
            current_url = driver.current_url
            self.log(f"Current URL after wait: {current_url}")

            # Try to find ANY content
            body = driver.find_element(By.TAG_NAME, 'body')
            body_text = body.text[:500] if body.text else "EMPTY"
            self.log(f"Page content preview: {body_text}...")

            # Look for prices
            price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
            self.log(f"Found {len(price_elements)} elements with '$' after wait")

            self.log("Results page loaded (or timeout reached)")

        except Exception as e:
            self.log(f"Error in wait_for_results: {e}")
            # Don't raise - allow scraper to attempt extraction anyway
