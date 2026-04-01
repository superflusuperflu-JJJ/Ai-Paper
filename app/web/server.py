from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.database import PaperDB

app = FastAPI(title="AI Paper Daily")
WEB_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
db = PaperDB(settings.db_path, settings.database_url)


@app.get("/")
def index(request: Request):
    today = date.today()
    papers = db.get_daily(today)
    history = db.list_recent_days(30)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "today": today.isoformat(),
            "papers": papers,
            "history": history,
        },
    )


@app.get("/api/day/{run_date}")
def api_day(run_date: str):
    try:
        d = date.fromisoformat(run_date)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "invalid date"})
    return {"date": run_date, "papers": db.get_daily(d)}
