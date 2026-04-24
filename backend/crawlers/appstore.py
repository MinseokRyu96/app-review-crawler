import re
import httpx
from typing import List, Dict

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _detect_country(url: str) -> str:
    m = re.search(r"apps\.apple\.com/([a-z]{2})/", url)
    return m.group(1) if m else "kr"


def _extract_app_id(url: str) -> str:
    # URL-encoded 또는 유니코드 한국어 앱 이름 모두 처리
    m = re.search(r"/id(\d+)", url)
    return m.group(1) if m else ""


def fetch_reviews(url: str, count: int) -> List[Dict]:
    country = _detect_country(url)
    app_id  = _extract_app_id(url)
    if not app_id:
        raise ValueError("앱 ID를 URL에서 찾을 수 없습니다.")

    reviews: List[Dict] = []
    page = 1

    with httpx.Client(timeout=30, follow_redirects=True, headers=_HEADERS) as client:
        while len(reviews) < count and page <= 10:
            rss_url = (
                f"https://itunes.apple.com/{country}/rss/customerreviews"
                f"/page={page}/id={app_id}/sortby=mostrecent/json"
            )
            resp = client.get(rss_url)
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("feed", {}).get("entry", [])

            # iTunes RSS는 리뷰가 1개일 때 list 대신 dict을 반환
            if isinstance(entries, dict):
                entries = [entries]

            # 1페이지 첫 번째 entry는 앱 정보 (리뷰 아님)
            if page == 1 and entries:
                entries = entries[1:]

            if not entries:
                break

            for entry in entries:
                if len(reviews) >= count:
                    break
                # entry가 dict이 아닌 경우 방어
                if not isinstance(entry, dict):
                    continue
                reviews.append({
                    "author":      entry.get("author", {}).get("name", {}).get("label", ""),
                    "rating":      int(entry.get("im:rating", {}).get("label", 0)),
                    "title":       entry.get("title",      {}).get("label", ""),
                    "content":     entry.get("content",    {}).get("label", ""),
                    "review_date": entry.get("updated",    {}).get("label", "")[:10],
                    "version":     entry.get("im:version", {}).get("label", ""),
                })
            page += 1

    return reviews
