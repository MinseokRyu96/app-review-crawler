import re
import math
import scrapy

from review_crawler.items import ReviewItem


class AppStoreSpider(scrapy.Spider):
    name = "appstore"

    def __init__(self, url="", count="50", job_id="", **kwargs):
        super().__init__(**kwargs)
        self.crawl_url = url
        self.max_count = int(count)
        self.job_id = job_id
        self.collected = 0

        m = re.search(r"/id(\d+)", url)
        self.app_id = m.group(1) if m else None

        # apps.apple.com/kr/app/... 에서 국가 코드 추출, 없으면 us
        c = re.search(r"apps\.apple\.com/([a-z]{2})/", url)
        self.country = c.group(1) if c else "us"

    def start_requests(self):
        if not self.app_id:
            self.logger.error(f"앱 ID를 추출할 수 없습니다: {self.crawl_url}")
            return

        pages = min(10, math.ceil(self.max_count / 50))
        for page in range(1, pages + 1):
            yield scrapy.Request(
                (
                    f"https://itunes.apple.com/{self.country}/rss/customerreviews/"
                    f"page={page}/id={self.app_id}/sortby=mostrecent/json"
                ),
                callback=self.parse,
                meta={"page": page},
            )

    def parse(self, response):
        data = response.json()
        entries = data.get("feed", {}).get("entry", [])

        if not entries:
            return

        # 단일 항목은 dict로 반환됨
        if isinstance(entries, dict):
            entries = [entries]

        for entry in entries:
            if self.collected >= self.max_count:
                return

            # 첫 번째 entry는 앱 정보 (rating 없음)
            if "im:rating" not in entry:
                continue

            self.collected += 1
            yield ReviewItem(
                job_id=self.job_id,
                store="appstore",
                author=entry.get("author", {}).get("name", {}).get("label", ""),
                rating=int(entry.get("im:rating", {}).get("label", 0)),
                title=entry.get("title", {}).get("label", ""),
                content=entry.get("content", {}).get("label", ""),
                date=entry.get("updated", {}).get("label", "")[:10],
                version=entry.get("im:version", {}).get("label", ""),
            )
