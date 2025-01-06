import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from scrapy.http import HtmlResponse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import re


class MasterSpider(scrapy.Spider):
    name = "cargiant"
    start_urls = ["https://www.cargiant.co.uk/search/all/all"]
    scraped_urls = set()  # Set to keep track of scraped URLs
    
    def __init__(self, *args, **kwargs):
        super(MasterSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    def parse(self, response):
        self.driver.get(response.url)

        # for page_num in range(PAGES):
        #     self.logger.info(f"Processing page {page_num + 1}")
        while True:
            # Wait for the listings to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div[data-vehicle]")
                    )
                )
            except Exception as e:
                self.logger.error(f"Error loading listings: {e}")
                break

            # Grab the current HTML source
            body = self.driver.page_source
            response_obj = HtmlResponse(
                url=self.driver.current_url,
                body=body,
                encoding="utf-8",
            )

            # Parse car listing links
            listings = response_obj.css("a.car-listing-item__details")
            if not listings:
                self.logger.warning("No listings found!")

            for listing in listings:
                car_url = listing.attrib.get("href")
                if car_url:
                    # Construct the absolute URL
                    full_url = f"https://www.cargiant.co.uk{car_url}"
                    if full_url not in self.scraped_urls:
                        self.scraped_urls.add(full_url)
                        yield scrapy.Request(url=full_url, callback=self.parse_listing)
                else:
                    self.logger.warning("No URL found in a listing.")

            # Handle pagination by clicking the "Next" button
            try:
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a.paging__item--next")
                    )
                )
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)  # Allow time for the next page to load
            except Exception as e:
                self.logger.error(f"Error clicking next button: {e}")
                break

    def parse_listing(self, response):
        self.logger.info(f"Processing next listing ...")
        self.driver.get(response.url)
        time.sleep(1)  # Wait for the page to load

        # Initialize dictionary for output
        output = {}
        output["url"] = response.url

        # Helper function to clean numeric fields
        def clean_numeric(value):
            try:
                value = re.sub(r'[^\d\.]', '', str(value).strip())
                return float(value)
            except (ValueError, TypeError):
                return None

        # Extract the title which includes both make and model
        try:
            title_element = self.driver.find_element(
                By.CSS_SELECTOR, "h1.title__main.set-h3"
            )
            title = title_element.text.strip()
            title_parts = title.split(None, 1)  # Split into make and model
            # List of multi-word car makes
            multi_word_makes = ["Land Rover"]

            # Initialize make and model
            make = ""
            model = ""

            # Check if the first two words form a multi-word make
            if len(title_parts) >= 2 and f"{title_parts[0]} {title_parts[1]}" in multi_word_makes:
                make = f"{title_parts[0]} {title_parts[1]}"
                model = " ".join(title_parts[2:])  # Remaining parts as model
            else:
                make = title_parts[0]  # First word as make
                model = " ".join(title_parts[1:])  # Remaining parts as model
            
            output["make"] = make
            output["model"] = model
            
        except Exception as e:
            self.logger.error(f"Error extracting title: {e}")
            output["make"] = None
            output["model"] = None

        # Extract price
        try:
            price_element = self.driver.find_element(
                By.CSS_SELECTOR, "div.price-block__price"
            )
            price = price_element.text.strip()
            output["price"] = clean_numeric(price)
        except Exception as e:
            self.logger.error(f"Error extracting price: {e}")
            output["price"] = None

        # Collect all items from details section on page
        details = {}
        try:
            items = self.driver.find_elements(
                By.CSS_SELECTOR, "li.details-panel-item__list__item"
            )
            for item in items:
                spans = item.find_elements(By.CSS_SELECTOR, "span")
                if len(spans) >= 2:
                    key = spans[0].text.strip()
                    value = spans[1].text.strip()
                    details[key] = value
        except Exception as e:
            self.logger.error(f"Error extracting details: {e}")

        # Clean and store relevant details
        output["year"] = int(details.get("Year")) if details.get("Year") else None
        output["mileage"] = clean_numeric(details.get("Mileage"))
        output["fuel_type"] = details.get("Fuel Type")
        output["transmission"] = details.get("Transmission")
        output["body_style"] = details.get("Body Type")
        output["n_doors"] = clean_numeric(details.get("Doors"))
        output["previous_owners"] = clean_numeric(details.get("Keepers"))

        # Extract Colour
        output["droplet"] = details.get("Colour")

        # Extract Features List
        try:
            feature_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "div.row-wrap__row .text-content p"
            )
            features = []
            for feature in feature_elements:
                text = feature.text.strip()
                if text:
                    features.append(text)
            output["feature_list"] = ", ".join(features)
        except Exception as e:
            self.logger.error(f"Error extracting feature list: {e}")
            output["feature_list"] = None

        # Performance tab for additional data
        try:
            performance_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div.tab-wrap__head__inner__tabs__tab[data-tab="tab1"]')
                )
            )
            performance_tab.click()
            time.sleep(0.2)  # Wait for the Performance tab to load

            # Extract CC and WLTP - MPG - Comb - TEH (MPG)
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            cc = None
            bhp = None
            mpg = None

            for row in rows:
                try:
                    key_element = row.find_elements(By.CSS_SELECTOR, "td.key")
                    value_element = row.find_elements(By.CSS_SELECTOR, "td.value")

                    if key_element and value_element:
                        key = key_element[0].text.strip()
                        value = value_element[0].text.strip()

                        if key == "CC":
                            cc = value
                        elif key == "Engine Power - BHP":
                            bhp = value
                        elif key == "WLTP - MPG - Comb - TEH":
                            mpg = value
                except Exception as e:
                    self.logger.error(f"Error parsing row: {e}")
                    continue

            # Clean and store engine size (convert CC to litres if available)
            output["engine_size"] = (
                str(float(cc.replace(",", "").strip()) / 1000) if cc else None
            )
            output["hp"] = clean_numeric(bhp)
            output["mpg"] = clean_numeric(mpg)

        except Exception as e:
            self.logger.error(f"Error extracting Performance data: {e}")
            output["engine_size"] = None
            output["hp"] = None
            output["mpg"] = None
        output["dealership_name"] = 'Cargiant'
        
        # Yield the output as an item
        yield output

    def closed(self, reason):
        self.driver.quit()
