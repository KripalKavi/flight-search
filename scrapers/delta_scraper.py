from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from .base_scraper import BaseScraper
from typing import Dict, List
import time
import re

class DeltaScraper(BaseScraper):
    """Delta Airlines flight search scraper"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.source_name = "Delta"
        self.base_url = "https://www.delta.com"

    def search_flights(self, origin: str, destination: str,
                      depart_date: str, return_date: str,
                      adults: int, children: int) -> List[Dict]:
        """Search Delta for flights by interacting with the page"""

        driver = self._init_driver()

        try:
            # Navigate to Delta homepage
            self.log(f"Navigating to Delta.com...")
            driver.get(self.base_url)

            # Wait for page to load
            self.log("Waiting for page to load...")
            time.sleep(5)

            # Take screenshot to see initial page state
            try:
                import os
                screenshot_path = os.path.join(os.path.dirname(__file__), '..', 'delta_initial.png')
                driver.save_screenshot(screenshot_path)
                self.log(f"Saved initial screenshot to: {screenshot_path}")
            except Exception as e:
                self.log(f"Could not save screenshot: {e}")

            # Try to close any popups/modals
            try:
                self.log("Checking for popups/modals...")
                # Common close button selectors
                close_selectors = [
                    "button[aria-label*='close']",
                    "button[aria-label*='Close']",
                    "button.close",
                    "[class*='close-button']",
                    "[class*='modal-close']",
                    "button:contains('×')",
                    "button:contains('Close')"
                ]

                for selector in close_selectors:
                    try:
                        close_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in close_buttons:
                            if btn.is_displayed():
                                btn.click()
                                self.log(f"Closed popup/modal with selector: {selector}")
                                time.sleep(1)
                                break
                    except:
                        continue
            except Exception as e:
                self.log(f"No popups to close: {e}")

            # Look for and interact with the flight search form
            self.log("Filling out search form...")

            # Find and click "From" field to open modal
            try:
                # Try to find the "From" clickable element
                from_selectors = [
                    "button:contains('From')",
                    "div:contains('From')",
                    "[aria-label*='From']",
                    "[placeholder*='From']",
                    "span:contains('From')"
                ]

                from_element = None

                # Try XPath for elements containing "From" text
                try:
                    from_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'From') or @placeholder='From' or @aria-label='From']")
                    for elem in from_elements:
                        if elem.is_displayed():
                            from_element = elem
                            self.log(f"Found 'From' element with text: {elem.text[:50]}")
                            break
                except:
                    pass

                if not from_element:
                    self.log("ERROR: Could not find 'From' field")
                    return self._return_unavailable_results()

                # Click the "From" field to open modal
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", from_element)
                time.sleep(1)
                from_element.click()
                self.log("Clicked 'From' field to open modal")
                time.sleep(3)  # Increased wait for modal to fully render

                # Take screenshot of modal for debugging
                try:
                    import os
                    screenshot_path = os.path.join(os.path.dirname(__file__), '..', 'delta_from_modal.png')
                    driver.save_screenshot(screenshot_path)
                    self.log(f"Saved 'From' modal screenshot to: {screenshot_path}")
                except Exception as e:
                    self.log(f"Could not save screenshot: {e}")

                # Now find the input in the modal and enter origin
                # IMPORTANT: Avoid date inputs (readonly) and look for airport search inputs
                modal_input_selectors = [
                    "input[placeholder*='city']",
                    "input[placeholder*='City']",
                    "input[placeholder*='airport']",
                    "input[placeholder*='Airport']",
                    "input[id*='origin']",
                    "input[name*='origin']",
                    "input[aria-label*='origin']",
                    "input[type='text']:not([readonly])"  # Exclude readonly inputs (dates)
                ]

                modal_input = None
                for selector in modal_input_selectors:
                    try:
                        inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                        for inp in inputs:
                            # Make sure it's displayed, enabled, and NOT readonly
                            if inp.is_displayed() and inp.is_enabled() and not inp.get_attribute('readonly'):
                                modal_input = inp
                                self.log(f"Found modal input with selector: {selector}, id={inp.get_attribute('id')}")
                                break
                        if modal_input:
                            break
                    except:
                        continue

                if not modal_input:
                    self.log("ERROR: Could not find input in modal")
                    return self._return_unavailable_results()

                # Wait for input to be clickable and click it to focus
                try:
                    modal_input = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(modal_input)
                    )
                    modal_input.click()
                    self.log("Clicked modal input to focus")
                    time.sleep(1)
                except Exception as e:
                    self.log(f"Could not click modal input: {e}")

                # Enter origin in modal - try different methods
                try:
                    # Method 1: Try normal send_keys
                    modal_input.send_keys(origin)
                    time.sleep(2)
                    modal_input.send_keys(Keys.ENTER)
                    self.log(f"Entered origin: {origin}")
                except Exception as e:
                    self.log(f"Normal input failed, trying JavaScript: {e}")
                    # Method 2: Use JavaScript as fallback
                    try:
                        driver.execute_script(f"arguments[0].value = '{origin}';", modal_input)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", modal_input)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", modal_input)
                        time.sleep(1)
                        modal_input.send_keys(Keys.ENTER)
                        self.log(f"Entered origin via JavaScript: {origin}")
                    except Exception as e2:
                        self.log(f"JavaScript input also failed: {e2}")
                        raise

                time.sleep(2)

            except Exception as e:
                self.log(f"Error entering origin: {e}")
                return self._return_unavailable_results()

            # Find and click "To" field to open modal
            try:
                # Try to find the "To" clickable element
                to_selectors = [
                    "button:contains('To')",
                    "div:contains('To')",
                    "[aria-label*='To']",
                    "[placeholder*='To']",
                    "span:contains('To')"
                ]

                to_element = None

                # Try XPath for elements containing "To" text
                try:
                    to_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'To') or @placeholder='To' or @aria-label='To']")
                    for elem in to_elements:
                        # Make sure it's the right "To" (not "Get to know us" etc)
                        if elem.is_displayed() and len(elem.text.strip()) <= 10:
                            to_element = elem
                            self.log(f"Found 'To' element with text: {elem.text[:50]}")
                            break
                except:
                    pass

                if not to_element:
                    self.log("ERROR: Could not find 'To' field")
                    return self._return_unavailable_results()

                # Click the "To" field to open modal
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", to_element)
                time.sleep(1)
                to_element.click()
                self.log("Clicked 'To' field to open modal")
                time.sleep(3)  # Increased wait for modal to fully render

                # Now find the input in the modal and enter destination
                # IMPORTANT: Avoid date inputs (readonly) and look for airport search inputs
                modal_input_selectors = [
                    "input[placeholder*='city']",
                    "input[placeholder*='City']",
                    "input[placeholder*='airport']",
                    "input[placeholder*='Airport']",
                    "input[id*='destination']",
                    "input[name*='destination']",
                    "input[aria-label*='destination']",
                    "input[type='text']:not([readonly])"  # Exclude readonly inputs (dates)
                ]

                modal_input = None
                for selector in modal_input_selectors:
                    try:
                        inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                        for inp in inputs:
                            # Make sure it's displayed, enabled, and NOT readonly
                            if inp.is_displayed() and inp.is_enabled() and not inp.get_attribute('readonly'):
                                modal_input = inp
                                self.log(f"Found modal input with selector: {selector}, id={inp.get_attribute('id')}")
                                break
                        if modal_input:
                            break
                    except:
                        continue

                if not modal_input:
                    self.log("ERROR: Could not find input in modal")
                    return self._return_unavailable_results()

                # Wait for input to be clickable and click it to focus
                try:
                    modal_input = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(modal_input)
                    )
                    modal_input.click()
                    self.log("Clicked modal input to focus")
                    time.sleep(1)
                except Exception as e:
                    self.log(f"Could not click modal input: {e}")

                # Enter destination in modal - try different methods
                try:
                    # Method 1: Try normal send_keys
                    modal_input.send_keys(destination)
                    time.sleep(2)
                    modal_input.send_keys(Keys.ENTER)
                    self.log(f"Entered destination: {destination}")
                except Exception as e:
                    self.log(f"Normal input failed, trying JavaScript: {e}")
                    # Method 2: Use JavaScript as fallback
                    try:
                        driver.execute_script(f"arguments[0].value = '{destination}';", modal_input)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", modal_input)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", modal_input)
                        time.sleep(1)
                        modal_input.send_keys(Keys.ENTER)
                        self.log(f"Entered destination via JavaScript: {destination}")
                    except Exception as e2:
                        self.log(f"JavaScript input also failed: {e2}")
                        raise

                time.sleep(2)

            except Exception as e:
                self.log(f"Error entering destination: {e}")
                return self._return_unavailable_results()

            # Handle dates - Click "Depart - Return" to open calendar modal
            try:
                self.log("Attempting to select dates...")

                # Parse dates to know which calendar dates to click
                from datetime import datetime
                try:
                    depart_dt = datetime.strptime(depart_date, '%Y-%m-%d')
                    return_dt = datetime.strptime(return_date, '%Y-%m-%d')
                    depart_day = depart_dt.day
                    depart_month = depart_dt.month
                    depart_year = depart_dt.year
                    return_day = return_dt.day
                    return_month = return_dt.month
                    return_year = return_dt.year
                    self.log(f"Parsed dates: Depart {depart_month}/{depart_day}/{depart_year}, Return {return_month}/{return_day}/{return_year}")
                except Exception as e:
                    self.log(f"Could not parse dates: {e}")
                    raise

                # Find and click "Depart - Return" element to open calendar modal
                try:
                    # Try XPath for elements containing "Depart" text
                    date_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Depart') or contains(text(), 'Return')]")
                    date_element = None
                    for elem in date_elements:
                        if elem.is_displayed() and 'depart' in elem.text.lower():
                            date_element = elem
                            self.log(f"Found date element with text: {elem.text[:100]}")
                            break

                    if not date_element:
                        self.log("Could not find 'Depart - Return' element, trying alternative selectors")
                        # Try finding date-related buttons or divs
                        for selector in ["button[aria-label*='date']", "div[class*='date']", "[id*='calendar']"]:
                            try:
                                date_element = driver.find_element(By.CSS_SELECTOR, selector)
                                if date_element and date_element.is_displayed():
                                    self.log(f"Found date element with selector: {selector}")
                                    break
                            except:
                                continue

                    if date_element:
                        # Click to open calendar modal
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", date_element)
                        time.sleep(1)
                        date_element.click()
                        self.log("Clicked 'Depart - Return' to open calendar")
                        time.sleep(3)

                        # Take screenshot of calendar modal
                        try:
                            import os
                            screenshot_path = os.path.join(os.path.dirname(__file__), '..', 'delta_calendar.png')
                            driver.save_screenshot(screenshot_path)
                            self.log(f"Saved calendar screenshot to: {screenshot_path}")
                        except Exception as e:
                            self.log(f"Could not save screenshot: {e}")

                        # TODO: Navigate calendar and select dates
                        # For now, just log that we opened it
                        self.log("Calendar opened successfully - date selection needs implementation")

                    else:
                        self.log("ERROR: Could not find date selector element")

                except Exception as e:
                    self.log(f"Error opening calendar: {e}")

            except Exception as e:
                self.log(f"Error handling dates: {e}")
                # Continue anyway - dates might have defaults

            # Find and click search button
            try:
                self.log("Looking for search button...")
                search_selectors = [
                    "button[type='submit']",
                    "button[id*='search']",
                    "button[class*='search']",
                    "input[type='submit']",
                    "button:contains('Search')",
                    "button:contains('Find')"
                ]

                search_button = None
                for selector in search_selectors:
                    try:
                        search_button = driver.find_element(By.CSS_SELECTOR, selector)
                        if search_button and search_button.is_displayed():
                            self.log(f"Found search button with selector: {selector}")
                            break
                    except:
                        continue

                if not search_button:
                    # Try XPath for buttons with "Search" or "Find" text
                    try:
                        search_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Search') or contains(text(), 'Find') or contains(text(), 'SEARCH')]")
                    except:
                        pass

                if search_button:
                    search_button.click()
                    self.log("Clicked search button")
                    time.sleep(3)
                else:
                    self.log("ERROR: Could not find search button")
                    return self._return_unavailable_results()

            except Exception as e:
                self.log(f"Error clicking search button: {e}")
                return self._return_unavailable_results()

            # Wait for results to load
            self.log("Waiting for results to load...")
            time.sleep(10)  # Delta pages can be slow

            # Check current URL
            self.log(f"Current URL: {driver.current_url}")

            # Extract results
            self.log("Extracting flight results...")
            economy_result, premium_result, business_result = self._extract_results(driver)

            results = {
                'source': 'Delta',
                'economy': economy_result,
                'premium_economy': premium_result,
                'business': business_result
            }

            self.log(f"Results: Economy={results['economy']}, Premium={results['premium_economy']}, Business={results['business']}")

            return [results]

        except Exception as e:
            self.log(f"ERROR: {e}")
            return self._return_unavailable_results()

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

        # Window size
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

    def _extract_results(self, driver) -> tuple:
        """Extract flight prices from Delta results page"""
        try:
            economy_result = self._unavailable_result()
            premium_result = self._unavailable_result()
            business_result = self._unavailable_result()

            # Take screenshot for debugging
            try:
                import os
                screenshot_path = os.path.join(os.path.dirname(__file__), '..', 'delta_debug.png')
                driver.save_screenshot(screenshot_path)
                self.log(f"Saved debug screenshot to: {screenshot_path}")
            except Exception as e:
                self.log(f"Could not save screenshot: {e}")

            # Look for price elements on Delta results page
            # Delta typically shows prices in fare cards or tiles
            self.log("Searching for price elements...")

            # Try multiple strategies to find prices
            all_prices = []

            # Strategy 1: Look for elements with dollar signs
            price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
            self.log(f"Found {len(price_elements)} elements with '$'")

            for elem in price_elements[:20]:  # Check first 20
                try:
                    text = elem.text.strip()
                    if text and '$' in text:
                        price_match = re.search(r'\$[\d,]+', text)
                        if price_match:
                            price_val = int(price_match.group().replace('$', '').replace(',', ''))
                            if 100 <= price_val <= 10000:  # Reasonable range
                                all_prices.append(price_val)
                                self.log(f"  Found price: ${price_val}")
                except:
                    continue

            # If we found prices, assign them to cabin classes
            if len(all_prices) >= 1:
                # Sort prices to get cheapest options
                all_prices = sorted(list(set(all_prices)))  # Remove duplicates and sort
                self.log(f"Found {len(all_prices)} unique prices: {all_prices[:10]}")

                # Assign cheapest prices to cabin classes
                # Typically: Economy = cheapest, Premium = mid, Business = most expensive
                economy_result = {
                    'price': all_prices[0],
                    'currency': 'USD',
                    'available': True,
                    'stops': None,
                    'stops_display': 'Not available',
                    'airline': 'Delta',
                    'is_best_deal': False
                }

                if len(all_prices) >= 2:
                    # Look for prices that might be premium (roughly 1.5-2x economy)
                    for price in all_prices[1:]:
                        if 1.3 <= price / all_prices[0] <= 2.5:
                            premium_result = {
                                'price': price,
                                'currency': 'USD',
                                'available': True,
                                'stops': None,
                                'stops_display': 'Not available',
                                'airline': 'Delta',
                                'is_best_deal': False
                            }
                            break

                if len(all_prices) >= 3:
                    # Business is typically 2-4x economy price
                    for price in reversed(all_prices):
                        if price / all_prices[0] >= 2.0:
                            business_result = {
                                'price': price,
                                'currency': 'USD',
                                'available': True,
                                'stops': None,
                                'stops_display': 'Not available',
                                'airline': 'Delta',
                                'is_best_deal': False
                            }
                            break

            return economy_result, premium_result, business_result

        except Exception as e:
            self.log(f"Error extracting results: {e}")
            return self._unavailable_result(), self._unavailable_result(), self._unavailable_result()

    def _unavailable_result(self) -> Dict:
        """Return structure for unavailable cabin class"""
        return {
            'price': None,
            'currency': 'USD',
            'available': False,
            'stops': None,
            'stops_display': 'Not available',
            'airline': 'Delta',
            'is_best_deal': False
        }

    def _return_unavailable_results(self) -> List[Dict]:
        """Return unavailable results for all cabin classes"""
        return [{
            'source': 'Delta',
            'economy': self._unavailable_result(),
            'premium_economy': self._unavailable_result(),
            'business': self._unavailable_result()
        }]
