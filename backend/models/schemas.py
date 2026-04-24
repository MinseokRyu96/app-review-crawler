from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CrawlRequest(BaseModel):
    url: str
    count: int = 50


class JobResponse(BaseModel):
    id: str
    url: str
    store: str
    count: int
    status: str
    total_reviews: int
    error_message: Optional[str] = None
    insights: Optional[str] = None
    insights_status: str = "none"
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    id: int
    job_id: str
    store: str
    author: str
    rating: int
    title: str
    content: str
    review_date: str
    version: str

    class Config:
        from_attributes = True
