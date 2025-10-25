# %%
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


# %%
class GoogleMapsScraper:
    def __init__(self, headless=True):
        self.setup_logging()
        self.driver = self.setup_driver(headless)
        self.data = []

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self, headless=True):
        options = Options()

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        # options.add_argument("--disable-web-security")
        # options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--incognito")

        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )

        if headless:
            options.add_argument("--headless")

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print("Clearing WebDriver cache and retrying...")
            service = Service(ChromeDriverManager().clearDriverCache().install())
            driver = webdriver.Chrome(service=service, options=options)

        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        return driver

    def navigate_to_maps(self):
        try:
            self.driver.get("https://www.google.com/maps")
            self.logger.info("Successfully navigated to Google Maps")

            try:
                consent_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//button[contains(text(), 'Accept') or contains(text(), 'I agree')]",
                        )
                    )
                )
                consent_button.click()
                self.logger.info("Accepted GDPR consent")
            except TimeoutException:
                self.logger.info("No GDPR consent dialog found")

            time.sleep(3)

        except Exception as e:
            self.logger.error(f"Error navigating to Google Maps: {e}")
            raise

    def search_business(self, query, location=""):
        try:
            search_query = f"{query}"
            if location:
                search_query += f" {location}"

            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )

            search_box.clear()
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.ENTER)

            self.logger.info(f"Searching for: {search_query}")

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="feed"]'))
            )

            time.sleep(5)

        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            raise

    def extract_business_data(self):
        businesses = []

        try:
            result_found = False
            selectors_to_try = [
                "[data-result-index]",
                '[role="feed"] > div',
                'div[jsaction*="mouseover:pane"]',
            ]

            for selector in selectors_to_try:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    result_found = True
                    break
                except:
                    continue

            if not result_found:
                self.logger.warning("Could not find results with any selector")
                return []

            business_cards = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div[jsaction*="mouseover:pane"] a[href*="/maps/place/"]',
            )

            if not business_cards:
                business_cards = self.driver.find_elements(
                    By.CSS_SELECTOR, 'a[href*="/maps/place/"]'
                )

            top_cards = business_cards[:1]

            self.logger.info(
                f"Found {len(business_cards)} total businesses, processing top {len(top_cards)}"
            )

            for i, card in enumerate(top_cards):
                try:
                    business_data = self.extract_single_business(card)
                    if business_data and business_data.get("name"):
                        businesses.append(business_data)
                        self.logger.info(
                            f"Extracted TOP {i+1}: {business_data.get('name', 'Unknown')}"
                        )
                    else:
                        self.logger.warning(f"Could not extract data from card {i+1}")

                except Exception as e:
                    self.logger.error(f"Error extracting business {i+1}: {e}")
                    continue

            self.data.extend(businesses)
            return businesses

        except Exception as e:
            self.logger.error(f"Error extracting business data: {e}")
            return []

    def extract_single_business(self, card_element):
        try:
            business = {
                "name": "",
                "maps_url": "",
            }

            # Get Google Maps URL
            maps_url = card_element.get_attribute("href")
            business["maps_url"] = maps_url

            # Find parent container with business information
            parent = card_element.find_element(
                By.XPATH, './ancestor::div[contains(@jsaction, "mouseover:pane")]'
            )

            # Extract business name
            try:
                name_element = parent.find_element(
                    By.CSS_SELECTOR, '[data-value="Name"]'
                )
                business["name"] = name_element.text.strip()
            except NoSuchElementException:
                try:
                    name_element = parent.find_element(By.CSS_SELECTOR, ".qBF1Pd")
                    business["name"] = name_element.text.strip()
                except:
                    pass

            return business

        except Exception as e:
            self.logger.error(f"Error extracting single business data: {e}")
            return None

    def run_scraper(self, query, location=""):
        try:
            self.logger.info("Starting Google Maps scraping...")

            self.navigate_to_maps()

            self.search_business(query, location)

            self.extract_business_data()

            self.logger.info(f"Scraping completed. Total businesses: {len(self.data)}")

        except Exception as e:
            self.logger.error(f"Error in main scraping process: {e}")
            raise
        finally:
            self.close()

    def close(self):
        if self.driver:
            self.driver.quit()
            self.logger.info("Web driver closed")
