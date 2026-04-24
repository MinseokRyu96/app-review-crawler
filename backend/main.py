import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from api.routes import router

_HERE = os.path.dirname(os.path.abspath(__file__))
_STATIC = os.path.join(_HERE, "static")

app = FastAPI(title="앱 리뷰 크롤러")
app.include_router(router, prefix="/api")
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(os.path.join(_STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()
