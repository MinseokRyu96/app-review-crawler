import re
import scrapy
from scrapy_playwright.page import PageMethod

from review_crawler.items import ReviewItem


class PlayStoreSpider(scrapy.Spider):
    name = "playstore"

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30000,
    }

    def __init__(self, url="", count="50", job_id="", **kwargs):
        super().__init__(**kwargs)
        self.crawl_url = url
        self.max_count = int(count)
        self.job_id = job_id

        m = re.search(r"id=([^&\s]+)", url)
        self.package_name = m.group(1) if m else None

    def start_requests(self):
        if not self.package_name:
            self.logger.error(f"패키지명을 추출할 수 없습니다: {self.crawl_url}")
            return

        yield scrapy.Request(
            f"https://play.google.com/store/apps/details?id={self.package_name}&hl=ko&gl=kr",
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                ],
            },
            callback=self.parse,
            errback=self.errback,
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]

        try:
            title = await page.title()
            self.logger.info(f"앱 페이지 확인: {title}")
        finally:
            await page.close()

        # async def 안에서는 yield from 불가 → for 루프로 순회
        for item in self._fetch_reviews_via_api():
            yield item

    def _fetch_reviews_via_api(self):
        from google_play_scraper import reviews as gp_reviews, Sort

        langs = [("ko", "kr"), ("en", "us")]
        result = []

        for lang, country in langs:
            try:
                fetched, _ = gp_reviews(
                    self.package_name,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=self.max_count,
                )
                result = fetched
                self.logger.info(f"리뷰 {len(result)}개 수집 완료 (lang={lang})")
                break
            except Exception as e:
                self.logger.warning(f"리뷰 수집 실패 (lang={lang}): {e}")

        for r in result[: self.max_count]:
            yield ReviewItem(
                job_id=self.job_id,
                store="playstore",
                author=r.get("userName", ""),
                rating=r.get("score", 0),
                title="",
                content=r.get("content", ""),
                date=str(r.get("at", ""))[:10],
                version=r.get("reviewCreatedVersion", "") or "",
            )

    async def errback(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Playwright 요청 실패: {failure}")
        for item in self._fetch_reviews_via_api():
            yield item
