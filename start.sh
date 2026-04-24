#!/bin/bash
set -e

PROJ="/Users/minseokryu/Desktop/94_Project/Crawling"
source "$PROJ/venv/bin/activate"

export DATABASE_URL=postgresql://reviewer:reviewpass@localhost:5432/reviewdb
export REDIS_URL=redis://localhost:6379/0
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"

echo "==> PostgreSQL & Redis 상태 확인"
brew services list | grep -E "postgresql|redis"

echo ""
echo "==> FastAPI 서버 시작  (http://localhost:8000)"
cd "$PROJ/backend"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
UVICORN_PID=$!

echo "==> Celery 워커 시작"
celery -A tasks.celery_app worker --loglevel=info --pool=solo &
CELERY_PID=$!

echo ""
echo "--------------------------------------"
echo "  FastAPI : http://localhost:8000"
echo "  Flower  : http://localhost:5555"
echo "  종료    : Ctrl+C"
echo "--------------------------------------"

# Flower (선택)
celery -A tasks.celery_app flower --port=5555 &

trap "kill $UVICORN_PID $CELERY_PID 2>/dev/null; echo 'Stopped.'" SIGINT SIGTERM
wait $UVICORN_PID
