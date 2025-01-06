BOT_NAME = "scrapy_used_cars"

SPIDER_MODULES = ["scrapy_used_cars.spiders"]
NEWSPIDER_MODULE = "scrapy_used_cars.spiders"

ROBOTSTXT_OBEY = False

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = None
FEED_EXPORT_ENCODING = "utf-8"

import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

LOG_LEVEL = 'INFO'
CONCURRENT_REQUESTS = 60
DOWNLOAD_DELAY = 0

ITEM_PIPELINES = {
    "scrapy_used_cars.pipelines.UsedCarsPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
  'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
  'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
  'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
}