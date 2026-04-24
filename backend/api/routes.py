import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from models.database import get_db, CrawlJob, Review
from models.schemas import CrawlRequest, JobResponse, ReviewResponse
from tasks.crawl_tasks import run_crawl, run_insights, detect_store, _build_txt

router = APIRouter()


@router.post("/crawl", response_model=JobResponse)
def start_crawl(request: CrawlRequest, db: Session = Depends(get_db)):
    store = detect_store(request.url)
    if store == "unknown":
        raise HTTPException(
            status_code=400,
            detail="유효하지 않은 URL입니다. 앱스토어 또는 플레이스토어 URL을 입력해주세요.",
        )
    if not (1 <= request.count <= 500):
        raise HTTPException(status_code=400, detail="크롤링 개수는 1~500 사이여야 합니다.")

    job_id = str(uuid.uuid4())
    job = CrawlJob(
        id=job_id,
        url=request.url,
        store=store,
        count=request.count,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    run_crawl.delay(job_id, request.url, request.count)
    return job


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return (
        db.query(CrawlJob)
        .order_by(CrawlJob.created_at.desc())
        .limit(30)
        .all()
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/reviews", response_model=List[ReviewResponse])
def get_reviews(job_id: str, db: Session = Depends(get_db)):
    return db.query(Review).filter(Review.job_id == job_id).all()


@router.post("/jobs/{job_id}/insights")
def request_insights(job_id: str, db: Session = Depends(get_db)):
    job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=400, detail="크롤링이 완료된 후 인사이트를 요청할 수 있습니다.")
    if job.insights_status in ("running", "pending"):
        raise HTTPException(status_code=400, detail="인사이트 분석이 이미 진행 중입니다.")

    job.insights_status = "pending"
    db.commit()

    run_insights.delay(job_id)
    return {"message": "인사이트 분석을 시작했습니다."}


@router.get("/jobs/{job_id}/download")
def download_reviews(job_id: str, db: Session = Depends(get_db)):
    job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=400, detail="크롤링이 완료된 후 다운로드할 수 있습니다.")

    reviews = db.query(Review).filter(Review.job_id == job_id).all()
    content = _build_txt(reviews, job.url, job.store)

    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="reviews_{job_id[:8]}.txt"'},
        media_type="text/plain; charset=utf-8",
    )
