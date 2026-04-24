import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────

class CrawlRequest(BaseModel):
    url: str
    count: int


class InsightsRequest(BaseModel):
    reviews: list
    store: str


class NewsCrawlRequest(BaseModel):
    keyword: str
    count: int


class NewsInsightsRequest(BaseModel):
    articles: list
    keyword: str


# ── Helpers ──────────────────────────────────────────────────────

def detect_store(url: str) -> str:
    if "apps.apple.com" in url or "itunes.apple.com" in url:
        return "appstore"
    if "play.google.com" in url:
        return "playstore"
    return "unknown"


def _call_groq(system: str, prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY가 설정되지 않았습니다.")

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 2048,
    }
    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=55,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Groq API 오류: {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── App Review endpoints ──────────────────────────────────────────

@router.post("/crawl")
def crawl(request: CrawlRequest):
    store = detect_store(request.url)
    if store == "unknown":
        raise HTTPException(
            status_code=400,
            detail="유효하지 않은 URL입니다. 앱스토어 또는 플레이스토어 URL을 입력해주세요.",
        )
    if not (1 <= request.count <= 500):
        raise HTTPException(status_code=400, detail="크롤링 개수는 1~500 사이여야 합니다.")

    try:
        if store == "appstore":
            from crawlers.appstore import fetch_reviews
        else:
            from crawlers.playstore import fetch_reviews
        reviews = fetch_reviews(request.url, request.count)
        return {"store": store, "reviews": reviews, "total": len(reviews)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights")
def get_insights(request: InsightsRequest):
    negative = [r for r in request.reviews if r.get("rating", 5) <= 2]
    if not negative:
        return {"insights": "부정적인 리뷰(1~2점)가 없습니다. 전반적으로 긍정적인 평가를 받고 있습니다! 🎉"}

    store_name = "앱스토어" if request.store == "appstore" else "플레이스토어"
    reviews_text = "\n".join(f"[{r['rating']}점] {r['content']}" for r in negative[:80])

    prompt = (
        f"아래는 {store_name}에 올라온 부정적 리뷰 {len(negative)}개입니다.\n\n"
        f"{reviews_text}\n\n"
        "다음 형식으로 분석해 주세요.\n\n"
        "## 🔴 핵심 불만 카테고리\n"
        "각 카테고리명, 해당 리뷰 비율, 대표 사례 1~2개\n\n"
        "## 📌 이슈별 요약\n"
        "각 카테고리의 구체적인 문제점\n\n"
        "## ✅ 개선 제안 (우선순위 순)\n"
        "팀이 즉시 실행할 수 있는 3~5가지 액션 아이템"
    )

    text = _call_groq(
        system=(
            "당신은 앱 서비스 개선 전문가입니다. "
            "사용자 리뷰를 분석해 팀이 바로 행동할 수 있는 구체적인 인사이트를 제공합니다. "
            "반드시 한국어로 답변하세요."
        ),
        prompt=prompt,
    )
    return {"insights": text}


# ── News endpoints ────────────────────────────────────────────────

@router.post("/news/crawl")
def news_crawl(request: NewsCrawlRequest):
    if not request.keyword.strip():
        raise HTTPException(status_code=400, detail="키워드를 입력해주세요.")
    if not (1 <= request.count <= 100):
        raise HTTPException(status_code=400, detail="뉴스 개수는 1~100 사이여야 합니다.")

    try:
        from crawlers.news import fetch_articles
        articles = fetch_articles(request.keyword.strip(), request.count)
        return {"keyword": request.keyword, "articles": articles, "total": len(articles)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/news/insights")
def news_insights(request: NewsInsightsRequest):
    if not request.articles:
        raise HTTPException(status_code=400, detail="분석할 기사가 없습니다.")

    articles_text = "\n\n".join(
        f"[{i+1}] 제목: {a.get('title', '')}\n"
        f"    출처: {a.get('source', '')} | {a.get('pub_date', '')}\n"
        f"    내용: {a.get('description', '')}"
        for i, a in enumerate(request.articles[:50])
    )

    prompt = (
        f'아래는 "{request.keyword}" 키워드로 수집한 뉴스 기사 {len(request.articles)}개입니다.\n\n'
        f"{articles_text}\n\n"
        "다음 형식으로 분석해 주세요.\n\n"
        "## 📰 주요 토픽\n"
        "기사들에서 반복적으로 나타나는 핵심 주제 3~5가지\n\n"
        "## 📊 트렌드 분석\n"
        "현재 이슈의 흐름과 방향성, 주목할 변화\n\n"
        "## 💡 핵심 인사이트\n"
        "이 키워드와 관련해 주목해야 할 3~5가지 포인트\n\n"
        "## ✅ 시사점 & 제언\n"
        "독자가 바로 활용할 수 있는 액션 아이템"
    )

    text = _call_groq(
        system=(
            "당신은 미디어 트렌드 분석 전문가입니다. "
            "뉴스 기사들을 종합 분석해 핵심 인사이트를 제공합니다. "
            "반드시 한국어로 답변하세요."
        ),
        prompt=prompt,
    )
    return {"insights": text}


@router.get("/health")
def health():
    return {"status": "ok"}
