import scrapy_splash

BOT_NAME = "used_cars_looker"

SPIDER_MODULES = ["used_cars_looker.spiders"]
NEWSPIDER_MODULE = "used_cars_looker.spiders"

# Splash Setup
SPLASH_URL = 'http://localhost:8050'

# Enable Splash downloader middleware and set its priority
DOWNLOADER_MIDDLEWARES = {
    'scrapy_splash.SplashCookiesMiddleware': 723,
    'scrapy_splash.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
}

# Enable Splash Deduplicate Args Filter
SPIDER_MIDDLEWARES = {
    'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
}

# Define the Splash DupeFilter and Cache Storage
DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'
HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Set User-Agent (optional, can be removed if default is preferred)
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
    "User-Agent" :"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
}

SPLASH_COOKIES_DEBUG = True
COOKIES_ENABLED = True

# Set settings whose default value is deprecated to a future-proof value
# REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
# FEED_EXPORT_ENCODING = "utf-8"
