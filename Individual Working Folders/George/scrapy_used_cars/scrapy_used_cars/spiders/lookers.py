import scrapy
from scrapy_splash import SplashRequest
import json
import random
import scrapy_splash
import re
import datetime
from scrapy import signals


class LookersSpider(scrapy.Spider):
    name = 'lookers'

    custom_settings = {
        'SPLASH_URLS': ['http://localhost:8050', 'http://localhost:8052'],
        'SPLASH_LOG_400': True,
        'DOWNLOADER_MIDDLEWARES': {
           'scrapy_splash.SplashCookiesMiddleware': 723,
           'scrapy_splash.SplashMiddleware': 725,
        },
        'SPIDER_MIDDLEWARES': {
           'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
            "scrapy_used_cars.middlewares.UsedCarsSpiderMiddleware": 543,
        },
        'DUPEFILTER_CLASS':'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE':'scrapy_splash.SplashAwareFSCacheStorage',
        'CONCURRENT_REQUESTS_PER_DOMAIN': 20,
        'CONCURRENT_REQUESTS_PER_IP': None,
        'COOKIES_ENABLED': True,
        'SPLASH_SLOT_POLICY': scrapy_splash.SlotPolicy.PER_DOMAIN,
        'SPLASH_COOKIES_DEBUG': True,
        'DEFAULT_REQUEST_HEADERS': {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
        },
        'DOWNLOADER_MIDDLEWARES': {
            "scrapy_used_cars.middlewares.UsedCarsDownloaderMiddleware": 543,
        },
        'ITEM_PIPELINES': {
            "scrapy_used_cars.pipelines.UsedCarsPipeline": 300,
        },
        'REACTOR_THREADPOOL_MAXSIZE': 40,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.1,
        'AUTOTHROTTLE_MAX_DELAY': 5,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 20,
        'AUTOTHROTTLE_DEBUG': True,
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [400, 429, 500, 503],
        'RETRY_TIMES': 3,
    }
        
    # Define your Lua script for Splash
    lua_script = """
        function main(splash, args)
            -- Set a realistic User-Agent (browser-like)
            splash:set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36")

            -- Clear cookies to start fresh
            splash:clear_cookies()

            -- Add necessary HTTP headers
            splash:on_request(function(request)
                request:set_header("Accept", "application/json, text/plain, */*")
                request:set_header("Accept-Language", "en-US,en;q=0.9")
                request:set_header("Referer", "https://www.lookers.co.uk")
                request:set_header("Connection", "keep-alive")
            end)

            -- Navigate to the URL
            assert(splash:go(args.url))

            -- Wait to allow the page to load
            assert(splash:wait(3))

            -- Return the final rendered HTML and cookies (to debug further)
            return {
                url = splash:url(),
                cookies = splash:get_cookies(),
                html = splash:html()
            }
        end
    """

# Start with the AJAX URL
    start_urls = [
        'https://api.lookers.co.uk/vehiclesearch/vehicle/search?Group=d90377b7-3fdf-460c-8090-10cf0207b7b4&Type=Car&condition=Dealer%20New%2C%20Nearly%20New%2CUsed&ignoreFacet=condition&skip=0&sortGroup=d90377b7-3fdf-460c-8090-10cf0207b7b4&sortOrder=Recommended&srsltid=AfmBOopLXJJMuc30je3HW7swmdHe5qYWNhIPeG1gw7RzM26fQZmZYyQE&take=24'
    ]
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(LookersSpider, cls).from_crawler(crawler, *args, **kwargs)
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
        
        print(f"Spider started at: {self.start_time}")
        print(f"Spider closed at: {end_time}")
        print(f"Total runtime: {runtime}")
        
    def get_splash_url(self):
        # Safely get a random splash URL from the settings
        splash_urls = self.settings.get('SPLASH_URLS', [])
        if splash_urls:
            return random.choice(splash_urls)
        else:
            raise ValueError("SPLASH_URLS is not set correctly in settings.")

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
            
            splash_url = self.get_splash_url()
            # Yield a request to scrape the car details
            yield SplashRequest(
                url=car_url,
                method="GET",
                callback=self.parse_car,
                endpoint="execute",
                args={'lua_source': self.lua_script},
                splash_url=splash_url,
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
