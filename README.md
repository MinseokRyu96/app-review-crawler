# 📱 앱 리뷰 크롤러

앱스토어 & 플레이스토어 리뷰를 자동 수집하고, AI로 인사이트를 분석해주는 웹 서비스입니다.

![Last Updated](https://img.shields.io/badge/updated-2026--04--24-blue)
![Vercel](https://img.shields.io/badge/deployed-Vercel-black?logo=vercel)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)

---

## ✨ 주요 기능

- **리뷰 수집** — 앱스토어(iTunes RSS API) / 플레이스토어(google-play-scraper) 리뷰 최대 500개 수집
- **AI 인사이트** — 부정 리뷰(1~2점)를 Groq(Llama 3.3) AI가 분석해 핵심 불만 카테고리 · 개선 제안 제공
- **TXT 다운로드** — 수집된 리뷰를 텍스트 파일로 즉시 다운로드
- **별점 필터** — 수집된 리뷰를 별점별로 필터링

---

## 🛠 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | HTML / CSS / Vanilla JS |
| Backend | FastAPI (Python 3.11) |
| App Store | iTunes RSS API + httpx |
| Play Store | google-play-scraper |
| AI 인사이트 | Groq API (Llama 3.3 70B) |
| 배포 | Vercel |

---

## 🚀 배포 구조

```
Vercel (단일 서비스)
├── FastAPI (api/index.py)
├── App Store 크롤러 (iTunes RSS)
├── Play Store 크롤러 (google-play-scraper)
└── AI 인사이트 (Groq REST API)
```

DB / Redis / 별도 워커 서버 없이 **Vercel 단독**으로 동작합니다.

---

## 📋 환경 변수

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `GROQ_API_KEY` | Groq API 키 ([발급](https://console.groq.com)) | 인사이트 기능에 필요 |

---

## 💻 로컬 실행

```bash
# 1. 의존성 설치
cd backend
pip install -r requirements.txt

# 2. 환경 변수 설정
cp ../.env.example ../.env
# .env 파일에 GROQ_API_KEY 입력

# 3. 서버 실행
uvicorn main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속

---

## 📁 프로젝트 구조

```
.
├── api/
│   ├── index.py          # Vercel 진입점
│   └── requirements.txt  # Vercel 의존성
├── backend/
│   ├── main.py           # FastAPI 앱
│   ├── api/
│   │   └── routes.py     # API 엔드포인트 (/crawl, /insights)
│   ├── crawlers/
│   │   ├── appstore.py   # 앱스토어 크롤러
│   │   └── playstore.py  # 플레이스토어 크롤러
│   └── static/           # 프론트엔드 (HTML/CSS/JS)
└── vercel.json
```

---

## 🔌 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/crawl` | 리뷰 수집 `{ url, count }` |
| `POST` | `/api/insights` | AI 인사이트 분석 `{ reviews, store }` |
| `GET` | `/api/health` | 서버 상태 확인 |
