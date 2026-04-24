from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime
import os


def _make_engine():
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
    if not url:
        known = [k for k in os.environ if "DB" in k or "POSTGRES" in k or "SQL" in k]
        raise RuntimeError(
            f"DATABASE_URL is not set or empty. "
            f"Related env keys found: {known}. "
            f"Total env keys: {len(os.environ)}"
        )
    return create_engine(url)


_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


# 하위 호환 — 기존 코드가 SessionLocal을 직접 import하는 경우
class _LazySessionLocal:
    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)

SessionLocal = _LazySessionLocal()


class Base(DeclarativeBase):
    pass


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    store = Column(String, nullable=False)
    count = Column(Integer, nullable=False)
    status = Column(String, default="pending")
    total_reviews = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    export_filename = Column(String, nullable=True)
    insights = Column(Text, nullable=True)
    insights_status = Column(String, default="none")
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
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
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
