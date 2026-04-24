import subprocess
import sys
import os
from datetime import datetime

from tasks.celery_app import celery_app
from models.database import SessionLocal, CrawlJob, Review

# tasks/ 기준으로 상위 경로 계산 — Docker(/app)와 로컬 양쪽 대응
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CRAWLER_DIR = os.getenv("CRAWLER_DIR", os.path.join(_BACKEND_DIR, "crawler"))
_EXPORT_DIR  = os.getenv("EXPORT_DIR",  os.path.join(os.path.dirname(_BACKEND_DIR), "exports"))


def detect_store(url: str) -> str:
    if "apps.apple.com" in url or "itunes.apple.com" in url:
        return "appstore"
    if "play.google.com" in url:
        return "playstore"
    return "unknown"


def _update_job(db, job_id: str, **kwargs):
    job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.commit()


def _export_to_txt(job_id: str, reviews: list, url: str, store: str) -> str:
    export_dir = _EXPORT_DIR
    os.makedirs(export_dir, exist_ok=True)
    filename = f"{job_id}.txt"
    filepath = os.path.join(export_dir, filename)

    store_name = "앱스토어" if store == "appstore" else "플레이스토어"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"{'=' * 60}\n")
        f.write(f"  앱 리뷰 크롤링 결과\n")
        f.write(f"{'=' * 60}\n")
        f.write(f"스토어  : {store_name}\n")
        f.write(f"URL     : {url}\n")
        f.write(f"수집 수 : {len(reviews)}개\n")
        f.write(f"수집 일 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'=' * 60}\n\n")

        for i, r in enumerate(reviews, 1):
            stars = "★" * r.rating + "☆" * (5 - r.rating)
            f.write(f"[{i:3d}] {r.author or 'Unknown'}\n")
            f.write(f"      {stars}  {r.review_date}\n")
            if r.title:
                f.write(f"      제목 : {r.title}\n")
            if r.version:
                f.write(f"      버전 : {r.version}\n")
            f.write(f"      {r.content}\n")
            f.write(f"      {'-' * 50}\n\n")

    return filename


def _build_txt(reviews: list, url: str, store: str) -> str:
    """리뷰 목록을 텍스트로 변환 (파일 저장 없이 문자열 반환)."""
    store_name = "앱스토어" if store == "appstore" else "플레이스토어"
    lines = [
        f"{'=' * 60}",
        f"  앱 리뷰 크롤링 결과",
        f"{'=' * 60}",
        f"스토어  : {store_name}",
        f"URL     : {url}",
        f"수집 수 : {len(reviews)}개",
        f"수집 일 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"{'=' * 60}",
        "",
    ]
    for i, r in enumerate(reviews, 1):
        stars = "★" * r.rating + "☆" * (5 - r.rating)
        lines.append(f"[{i:3d}] {r.author or 'Unknown'}")
        lines.append(f"      {stars}  {r.review_date}")
        if r.title:
            lines.append(f"      제목 : {r.title}")
        if r.version:
            lines.append(f"      버전 : {r.version}")
        lines.append(f"      {r.content}")
        lines.append(f"      {'-' * 50}")
        lines.append("")
    return "\n".join(lines)


@celery_app.task(bind=True, name="tasks.crawl_tasks.run_crawl")
def run_crawl(self, job_id: str, url: str, count: int):
    db = SessionLocal()
    try:
        _update_job(db, job_id, status="running")

        store = detect_store(url)
        spider_name = "appstore" if store == "appstore" else "playstore"

        log_path = os.path.join(_EXPORT_DIR, f"{job_id}_spider.log")
        os.makedirs(_EXPORT_DIR, exist_ok=True)

        result = subprocess.run(
            [
                sys.executable, "-m", "scrapy", "crawl", spider_name,
                "-a", f"url={url}",
                "-a", f"count={count}",
                "-a", f"job_id={job_id}",
                "--logfile", log_path,
            ],
            cwd=_CRAWLER_DIR,
            env={**os.environ},
            capture_output=True,
            text=True,
            timeout=360,
        )

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "Spider 실행 실패")[-800:]
            raise RuntimeError(err)

        reviews = db.query(Review).filter(Review.job_id == job_id).all()

        _update_job(
            db, job_id,
            status="done",
            total_reviews=len(reviews),
            completed_at=datetime.utcnow(),
        )

    except Exception as exc:
        _update_job(
            db, job_id,
            status="failed",
            error_message=str(exc)[:500],
            completed_at=datetime.utcnow(),
        )
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.crawl_tasks.run_insights")
def run_insights(self, job_id: str):
    import anthropic

    db = SessionLocal()
    try:
        _update_job(db, job_id, insights_status="running")

        job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
        reviews = db.query(Review).filter(Review.job_id == job_id).all()
        negative = [r for r in reviews if r.rating <= 2]

        if not negative:
            _update_job(
                db, job_id,
                insights="부정적인 리뷰(1~2점)가 없습니다. 전반적으로 긍정적인 평가를 받고 있습니다! 🎉",
                insights_status="done",
            )
            return

        store_name = "앱스토어" if job.store == "appstore" else "플레이스토어"
        reviews_text = "\n".join(
            f"[{r.rating}점] {r.content}" for r in negative[:80]
        )

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=[{
                "type": "text",
                "text": (
                    "당신은 앱 서비스 개선 전문가입니다. "
                    "사용자 리뷰를 분석해 팀이 바로 행동할 수 있는 구체적인 인사이트를 제공합니다. "
                    "반드시 한국어로 답변하세요."
                ),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    f"아래는 {store_name}에 올라온 부정적 리뷰 {len(negative)}개입니다.\n\n"
                    f"{reviews_text}\n\n"
                    "다음 형식으로 분석해 주세요.\n\n"
                    "## 🔴 핵심 불만 카테고리\n"
                    "각 카테고리명, 해당 리뷰 비율, 대표 사례 1~2개\n\n"
                    "## 📌 이슈별 요약\n"
                    "각 카테고리의 구체적인 문제점\n\n"
                    "## ✅ 개선 제안 (우선순위 순)\n"
                    "팀이 즉시 실행할 수 있는 3~5가지 액션 아이템"
                ),
            }],
        )

        _update_job(
            db, job_id,
            insights=msg.content[0].text,
            insights_status="done",
        )

    except Exception as exc:
        _update_job(db, job_id, insights_status="failed")
        raise
    finally:
        db.close()
