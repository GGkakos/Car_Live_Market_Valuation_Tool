# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class UsedCarsLookerItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class CarItem(scrapy.Item):
    make = scrapy.Field()
    model = scrapy.Field()
    price = scrapy.Field()
    mileage = scrapy.Field()
    fuel_type = scrapy.Field()
    body_style = scrapy.Field()
    engine_size = scrapy.Field()
    transmission = scrapy.Field()
    year = scrapy.Field()
    dealership_name = scrapy.Field()
    mpg = scrapy.Field()
    n_doors = scrapy.Field()
    previous_owners = scrapy.Field()
    droplet = scrapy.Field()
    feature_list = scrapy.Field()