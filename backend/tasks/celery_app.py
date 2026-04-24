from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Upstash는 rediss:// (TLS) 를 사용 — broker_use_ssl 필요
_use_ssl = REDIS_URL.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": None} if _use_ssl else {}

celery_app = Celery(
    "review_crawler",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.crawl_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=10,
    broker_use_ssl=_ssl_opts if _use_ssl else None,
    redis_backend_use_ssl=_ssl_opts if _use_ssl else None,
)
