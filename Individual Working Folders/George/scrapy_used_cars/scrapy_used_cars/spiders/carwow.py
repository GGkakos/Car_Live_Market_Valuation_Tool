import scrapy  # Import the base Spider class
from scrapy.http import Request  # Import Scrapy's Request class
from selenium import webdriver  # Import Selenium for browser automation
from selenium.webdriver.common.by import By  # Import By for finding elements
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re


class CarwowSpider(scrapy.Spider):
    name = "carwow"
    start_urls = [
        "https://www.carwow.co.uk/used-cars"
    ]

    base_url = "https://www.carwow.co.uk/used-cars?age=0%2C9&body_types_slug={body_type}&budget=0%2C150000&mileage=0%2C100000&safety_rating=0&stock_type=used&pagination%5Bcurrent_page%5D={page}&pagination%5Bper_page%5D=12&sort_order%5Bkey%5D=offer&sort_order%5Bdirection%5D=asc&filter_options%5Bdefault_make_slugs%5D=&filter_options%5Bdefault_model_slugs%5D=&filter_options%5Ballowed_stock_types%5D=used&filter_options%5Bhidden_filters%5D=stock_type%2Csupplier_distance&filter_options%5Bexcluded_filters%5D="
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize Selenium WebDriver
        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Variables to maintain scraping state
        self.scraped_links = []
        self.scroll_pause_time = 0.5
        self.scroll_step = 500
        

    def parse_listing(self, car_data, body_type):
        """
        Converts the car data dictionary to the format required by the database pipeline.
        """
        # List of multi-word car makes
        multi_word_makes = [
            "Aston Martin", "Alfa Romeo", "GWM Ora", "KGM Motors", "Land Rover"
        ]

        # Split car name into words
        car_name = car_data.get("car_name")
        car_name_parts = car_name.split()

        # Initialize make and model
        make = ""
        model = ""

        # Check if the first two words form a multi-word make
        if len(car_name_parts) >= 2 and f"{car_name_parts[0]} {car_name_parts[1]}" in multi_word_makes:
            make = f"{car_name_parts[0]} {car_name_parts[1]}"
            model = " ".join(car_name_parts[2:])  # Remaining parts as model
        else:
            make = car_name_parts[0]  # First word as make
            model = " ".join(car_name_parts[1:])  # Remaining parts as model
            
        return {
            "make": make if make else None,
            "model": model if model else None,
            "price": float(car_data.get("price").replace("£", "").replace(",", "")) if car_data.get("price") else None,
            "mileage": float(car_data.get("mileage").replace(" miles", "").replace(",", "")) if car_data.get("mileage") else None,
            "fuel_type": car_data.get("fuel"),
            "body_style": body_type.capitalize(),
            "engine_size": car_data.get("engine_size").replace(" litres", "") if car_data.get("engine_size") else None,
            "hp": car_data.get("hp"),
            "transmission": car_data.get("transmission"),
            "year": int(car_data.get("year")) if car_data.get("year") else None,
            "dealership_name": car_data.get("dealer_name"),
            "mpg": car_data.get("mpg"),
            "n_doors": car_data.get("n_doors"),
            "previous_owners": car_data.get("previous_owners"),
            "droplet": car_data.get("droplet"),
            "feature_list": None  # Could be populated if feature extraction is added
        }
    def scrape_page_content(self, body_type):
        """
        Scrapes content from a single page of cars and yields data to the pipeline.
        """
        def extract_numeric(value):
            return re.sub(r'[^\d\.]', '', str(value).strip()) if re.search(r'\d', str(value)) else None
        
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        current_scroll_position = 0
        last_scroll_position = 0

        while True:
            cars = self.driver.find_elements(By.CSS_SELECTOR, "article.card-generic")
            for car_index in range(len(cars)):
                try:
                    # Re-fetch car elements to avoid stale references
                    cars = self.driver.find_elements(By.CSS_SELECTOR, "article.card-generic")
                    link = cars[car_index].find_element(By.CSS_SELECTOR, "div.card-generic__section div.card-generic__ctas a").get_attribute("href")

                    # Skip already scraped links
                    if link in self.scraped_links:
                        continue

                    # Open the car's individual page
                    self.driver.get(link)
                    time.sleep(3)  # Allow the page to load

                    # Extract car details
                    dealer_name = None
                    try:
                        dealer_name = self.driver.find_element(By.CSS_SELECTOR, "div.dealership-info__title").text
                    except:
                        self.logger.info(f"Dealer details not found for {link}")

                    car_data = {
                        "link": link,
                        "dealer_name": dealer_name,
                        "car_name": None,
                        "price": None,
                        "year": None,
                        "mileage": None,
                        "engine_size": None,
                        "transmission": None,
                        "fuel": None,
                    }

                    try:
                        car_data["car_name"] = self.driver.find_element(By.CSS_SELECTOR, "span.deal-title__model").text
                    except:
                        pass

                    try:
                        car_data["price"] = self.driver.find_element(By.CSS_SELECTOR, "div.deal-pricing__carwow-price").text
                    except:
                        pass

                    details = self.driver.find_elements(By.CSS_SELECTOR, "div.summary-list__item")
                    for div in details:
                        try:
                            title = div.find_element(By.CSS_SELECTOR, "dt").text
                            detail = div.find_element(By.CSS_SELECTOR, "dd").text
                            if title.lower() == "year":
                                car_data["year"] = detail
                            elif title.lower() == "mileage":
                                car_data["mileage"] = detail
                            elif title.lower() == "engine size":
                                car_data["engine_size"] = detail
                            elif title.lower() == "transmission":
                                car_data["transmission"] = detail
                            elif title.lower() == "fuel":
                                car_data["fuel"] = detail
                            elif title.lower() == "colour":
                                car_data["droplet"] = detail
                            elif title.lower() == "engine power":
                                car_data["hp"] = int(extract_numeric(detail))
                            elif title.lower() == "previous owners":
                                car_data["previous_owners"] = detail
                            elif title.lower() == "average mpg":
                                car_data["mpg"] = float(extract_numeric(detail))
                            elif title.lower() == "doors":
                                car_data["n_doors"] = detail
                        except Exception as e:
                            self.logger.warning(f"Error fetching detail: {e}")

                    # Convert to pipeline-compatible data and yield
                    yield self.parse_listing(car_data, body_type)

                    # Track scraped links
                    self.scraped_links.append(link)

                    # Return to the main page
                    self.driver.back()
                    time.sleep(3)
                except Exception as e:
                    self.logger.warning(f"Error processing car: {e}")

            # Scroll down
            current_scroll_position += self.scroll_step
            self.driver.execute_script(f"window.scrollTo(0, {current_scroll_position});")
            time.sleep(self.scroll_pause_time)

            # Check if new content has loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_scroll_position:  # If no new content is loaded, stop
                self.logger.info("No more new cars to scrape on this page.")
                break
            last_scroll_position = new_height
            
            
    def parse(self, response):
        """
        Main entry point to start scraping all pages.
        """
        body_type_list = ['cabriolet', 'convertible', 'coupe', 'estate', 'hardtop', 'hatchback', 'roadster','saloon','soft-top','station-wagon']
        
        total_pages = 0
        for body_type in body_type_list:
            page = 1
            while total_pages < 100:
                link = self.base_url.format(body_type=body_type, page=page)
                try:
                    self.driver.get(link)
                    time.sleep(1)  
                    yield from self.scrape_page_content(body_type)
                    total_pages += 1
                    page += 1
                except Exception as e:
                    self.logger.warning(f"Error processing page {link}: {e}")
                    break


    def closed(self, reason):
        """
        Cleanup method to quit Selenium WebDriver.
        """
        self.driver.quit()

