import scrapy
from scrapy_splash import SplashRequest
import json
from used_cars_looker.items import CarItem
from scrapy import signals
from datetime import datetime
import re

class LookerSpider(scrapy.Spider):
    name = 'lookers'
    
    # Define your Lua script
    lua_script = """
    function main(splash, args)
    -- Set user agent
    splash:set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36")

    -- Add request headers
    splash:on_request(function(request)
        request:set_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        request:set_header("Accept-Language", "en-US,en;q=0.5")
        request:set_header("Referer", "https://www.google.com")
        request:set_header("Upgrade-Insecure-Requests", "1")
    end)

    -- Navigate to the URL
    assert(splash:go(args.url))

    -- Wait for the page to load (up to 3 seconds)
    assert(splash:wait(3))

    -- Interact with the cookie consent button, if present
    local cookie_button = splash:select('#cookie-accept')
    if cookie_button then
        cookie_button:mouse_click()
        splash:wait(1) -- Wait briefly after clicking
    end

    -- Return the page content
    return {
        url = splash:url(),
        html = splash:html(),
    }
end
    """

    start_urls = [
        'https://api.lookers.co.uk/vehiclesearch/vehicle/search?Group=d90377b7-3fdf-460c-8090-10cf0207b7b4&Type=Car&condition=Dealer%20New%2C%20Nearly%20New%2CUsed&ignoreFacet=condition&skip=0&sortGroup=d90377b7-3fdf-460c-8090-10cf0207b7b4&sortOrder=Recommended&srsltid=AfmBOopLXJJMuc30je3HW7swmdHe5qYWNhIPeG1gw7RzM26fQZmZYyQE&take=24'
    ]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(LookerSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_opened(self):
        self.start_time = datetime.now()
        self.log(f"Spider started at {self.start_time}")

    def spider_closed(self):
        end_time = datetime.now()
        runtime = end_time - self.start_time
        self.log(f"Spider closed at {end_time}")
        self.log(f"Total runtime: {runtime}")

    def parse(self, response):
        # Parse the JSON response
        data = json.loads(response.text)
        total_matches = data.get('Matches', 0)
        offset = data.get('Offset', 0) + len(data.get('Results', []))

        # Generate car-specific URLs and yield requests
        for car in data.get('Results', []):
            car_name = car.get('Make').lower().replace(" ", "-")
            car_model = car.get('Model').lower().replace(" ", "-")
            car_id = car.get('Id')
            
            car_url = f'https://www.lookers.co.uk/used-car/{car_name}/{car_model}/id/{car_id}'
        
            # Yield a request to scrape the car details
            yield SplashRequest(
                url=car_url,
                method="GET",
                callback=self.parse_car,
                endpoint="execute",
                args={'lua_source': self.lua_script},
                splash_headers={'Content-Type': 'application/json'},
                meta={
                    "id": car.get("Id"),
                    "price": car.get("Price"),
                    "make": car.get("Make"),
                    "model": car.get("Model"),
                    "mileage": car.get("Odometer"),
                    "fuel_type": car.get("FuelType"),
                    "body_style": car.get("BodyStyle"),
                    "engine_size": car.get("EngineSize"),
                    "transmission": car.get("Transmission"),
                    "year": car.get("ModelYear"),
                    "dealership_name": car.get("DealershipName"),
                    "registered_date": car.get("RegisteredDate"),
                }
            )
        
        # Handle pagination (get the next's page ajax)
        if offset < total_matches:
            next_url = f"https://api.lookers.co.uk/vehiclesearch/vehicle/search?Group=d90377b7-3fdf-460c-8090-10cf0207b7b4&Type=Car&condition=Dealer%20New%2C%20Nearly%20New%2CUsed&ignoreFacet=condition&skip={offset}&sortGroup=d90377b7-3fdf-460c-8090-10cf0207b7b4&sortOrder=Recommended&srsltid=AfmBOopLXJJMuc30je3HW7swmdHe5qYWNhIPeG1gw7RzM26fQZmZYyQE&take=24"
            yield scrapy.Request(url=next_url, callback=self.parse)


    def parse_car(self, response):
        
        def extract_numeric(value):
            return re.sub(r'[^\d\.]', '', str(value).strip()) if re.search(r'\d', str(value)) else None
        
        # Extract car details passed via meta
        car_meta = response.meta

        # Extract additional car details from the detailed page
        car_info = response.xpath("//div[contains(@class, 'used-specs__data-col')]").css('span.used-specs__vehicle-data::text').getall()

        # Necessary to handle errors from missing data in the website
        if len(car_info) == 10:
           mpg = car_info[3] 
           previous_owners = car_info[5] 
           n_doors = car_info[7] 
           droplet = car_info[9]
        elif len(car_info) == 9:
            mpg = None 
            previous_owners = car_info[4] 
            n_doors = car_info[6] 
            droplet = car_info[8]
        elif len(car_info) == 8:
            mpg = None
            previous_owners = car_info[3]
            n_doors = car_info[5]
            droplet = car_info[7]
            
        technical_info = response.xpath("//div[contains(@class, 'feature-panel_table tabular-text tabular-text--2col')]")
        rows = technical_info.xpath(".//div[@class='tabular-text__row' and not(contains(@class, 'tabular-text__row--header'))]")
        hp = None
        for row in rows:
            elems = row.xpath(".//div[@class='tabular-text__elem tabular-text__elem--container']")
            if len(elems) == 2:
                name = elems[0].xpath(".//div[@class='tabular-text__elem']/text()").get()
                value = elems[1].xpath(".//div[@class='tabular-text__elem']/text()").get()
                if name.strip() == "Engine Power - BHP":
                    hp = value.strip()
                    break
           
        # Extract feature list
        feature_list = []
        feature_panel = response.css('ul.feature-panel__ul')
        for item in feature_panel:
            features = [text.strip() for text in item.css('li::text').getall()]
            feature_list.extend(features)

        # Create item dictionary compatible with `car_db` schema
        car_item = {
            "make": car_meta.get("make"),
            "model": car_meta.get("model"),
            "price": car_meta.get("price"),
            "mileage": car_meta.get("mileage"),
            "fuel_type": car_meta.get("fuel_type"),
            "body_style": car_meta.get("body_style"),
            "engine_size": car_meta.get("engine_size"),
            "hp": hp,
            "transmission": car_meta.get("transmission"),
            "year": car_meta.get("year"),
            "dealership_name": car_meta.get("dealership_name"),
            "mpg": float(extract_numeric(mpg)) if mpg else None,
            "n_doors": int(extract_numeric(n_doors)) if n_doors else None,
            "previous_owners": int(extract_numeric(previous_owners)) if previous_owners else None,
            "droplet": droplet,
            "feature_list": ", ".join(feature_list),
        }

        # Yield the item to the pipeline
        yield car_item
