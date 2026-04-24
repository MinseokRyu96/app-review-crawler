import re
from typing import List, Dict
from google_play_scraper import reviews, Sort


def _extract_app_id(url: str) -> str:
    m = re.search(r"id=([^&\s]+)", url)
    return m.group(1) if m else ""


def fetch_reviews(url: str, count: int) -> List[Dict]:
    app_id = _extract_app_id(url)
    if not app_id:
        raise ValueError("앱 ID를 URL에서 찾을 수 없습니다.")

    result, _ = reviews(
        app_id,
        lang="ko",
        country="kr",
        sort=Sort.NEWEST,
        count=count,
    )

    return [
        {
            "author": r.get("userName", ""),
            "rating": r.get("score", 0),
            "title": "",
            "content": r.get("content", ""),
            "review_date": r["at"].strftime("%Y-%m-%d") if r.get("at") else "",
            "version": r.get("reviewCreatedVersion", "") or "",
        }
        for r in result
    ]
