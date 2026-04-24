import os

BOT_NAME = "review_crawler"
SPIDER_MODULES = ["review_crawler.spiders"]
NEWSPIDER_MODULE = "review_crawler.spiders"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://reviewer:reviewpass@localhost:5432/reviewdb",
)

# Playwright를 위한 asyncio reactor (scrapy-playwright 필수)
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 1
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 5
AUTOTHROTTLE_TARGET_CONCURRENCY = 2

ITEM_PIPELINES = {
    "review_crawler.pipelines.PostgresPipeline": 300,
}

DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
}

LOG_LEVEL = "INFO"
