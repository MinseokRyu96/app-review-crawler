import scrapy


class ReviewItem(scrapy.Item):
    job_id = scrapy.Field()
    store = scrapy.Field()
    author = scrapy.Field()
    rating = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    date = scrapy.Field()
    version = scrapy.Field()
