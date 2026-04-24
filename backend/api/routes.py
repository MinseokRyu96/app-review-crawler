import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class CrawlRequest(BaseModel):
    url: str
    count: int


class InsightsRequest(BaseModel):
    reviews: list
    store: str


def detect_store(url: str) -> str:
    if "apps.apple.com" in url or "itunes.apple.com" in url:
        return "appstore"
    if "play.google.com" in url:
        return "playstore"
    return "unknown"


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
    import httpx

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY가 설정되지 않았습니다.")

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

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models"
        f"/gemini-1.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "system_instruction": {
            "parts": [{"text": (
                "당신은 앱 서비스 개선 전문가입니다. "
                "사용자 리뷰를 분석해 팀이 바로 행동할 수 있는 구체적인 인사이트를 제공합니다. "
                "반드시 한국어로 답변하세요."
            )}]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2048},
    }

    try:
        resp = httpx.post(url, json=payload, timeout=55)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return {"insights": text}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Gemini API 오류: {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health():
    return {"status": "ok"}
