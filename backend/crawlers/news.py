import re
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote
from typing import List, Dict


def fetch_articles(keyword: str, count: int) -> List[Dict]:
    encoded = quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"

    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    items = channel.findall("item") if channel else []

    articles: List[Dict] = []
    for item in items[:count]:
        title_raw = item.findtext("title", "")
        # Google News 제목 형식: "제목 - 언론사"
        m = re.match(r"^(.+?)\s+-\s+([^-]+)$", title_raw)
        title  = m.group(1).strip() if m else title_raw
        source = m.group(2).strip() if m else ""

        pub_raw = item.findtext("pubDate", "")
        try:
            pub_date = datetime.strptime(pub_raw, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d")
        except Exception:
            pub_date = pub_raw[:10] if pub_raw else ""

        desc = re.sub(r"<[^>]+>", "", item.findtext("description", "") or "").strip()

        articles.append({
            "title":       title,
            "source":      source,
            "link":        item.findtext("link", ""),
            "pub_date":    pub_date,
            "description": desc,
        })

    return articles
