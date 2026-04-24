import sys
import os

# Vercel은 프로젝트 루트에서 실행되므로 backend를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: F401  — Vercel이 이 모듈에서 app을 탐지
