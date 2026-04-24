import re
import httpx
from typing import List, Dict


def _detect_country(url: str) -> str:
    m = re.search(r"apps\.apple\.com/([a-z]{2})/", url)
    return m.group(1) if m else "us"


def _extract_app_id(url: str) -> str:
    m = re.search(r"/id(\d+)", url)
    return m.group(1) if m else ""


def fetch_reviews(url: str, count: int) -> List[Dict]:
    country = _detect_country(url)
    app_id = _extract_app_id(url)
    if not app_id:
        raise ValueError("앱 ID를 URL에서 찾을 수 없습니다.")

    reviews: List[Dict] = []
    page = 1

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        while len(reviews) < count and page <= 10:
            rss_url = (
                f"https://itunes.apple.com/{country}/rss/customerreviews"
                f"/page={page}/id={app_id}/sortby=mostrecent/json"
            )
            resp = client.get(rss_url)
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("feed", {}).get("entry", [])

            if page == 1 and entries:
                entries = entries[1:]  # 첫 번째 entry는 앱 정보

            if not entries:
                break

            for entry in entries:
                if len(reviews) >= count:
                    break
                reviews.append({
                    "author": entry.get("author", {}).get("name", {}).get("label", ""),
                    "rating": int(entry.get("im:rating", {}).get("label", 0)),
                    "title": entry.get("title", {}).get("label", ""),
                    "content": entry.get("content", {}).get("label", ""),
                    "review_date": entry.get("updated", {}).get("label", "")[:10],
                    "version": entry.get("im:version", {}).get("label", ""),
                })
            page += 1

    return reviews
