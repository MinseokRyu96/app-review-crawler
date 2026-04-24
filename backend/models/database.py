from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime
import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://reviewer:reviewpass@localhost:5432/reviewdb"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    store = Column(String, nullable=False)   # 'appstore' | 'playstore'
    count = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending | running | done | failed
    total_reviews = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    export_filename = Column(String, nullable=True)
    insights = Column(Text, nullable=True)
    insights_status = Column(String, default="none")  # none | pending | running | done | failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, nullable=False, index=True)
    store = Column(String, nullable=False)
    author = Column(String)
    rating = Column(Integer)
    title = Column(String)
    content = Column(Text)
    review_date = Column(String)
    version = Column(String)
    crawled_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)
    # 기존 테이블에 새 컬럼 추가 (migrate)
    with engine.connect() as conn:
        for col, definition in [
            ("insights",        "TEXT"),
            ("insights_status", "VARCHAR DEFAULT 'none'"),
        ]:
            try:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE crawl_jobs ADD COLUMN IF NOT EXISTS {col} {definition}"
                    )
                )
                conn.commit()
            except Exception:
                conn.rollback()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
