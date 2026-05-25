"""刻迹 — FastAPI Backend — Vercel compatible."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    from starlette.formparsers import MultiPartParser
    from starlette.requests import Request
    _10MB = 10 * 1024 * 1024
    MultiPartParser.__init__.__kwdefaults__["max_part_size"] = _10MB
    Request.form.__kwdefaults__["max_part_size"] = _10MB
    Request._get_form.__kwdefaults__["max_part_size"] = _10MB
except Exception:
    pass

from database import init_db, shutdown_executor
from routers import collectibles, location, generate, qrcode

app = FastAPI(title="刻迹 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

app.include_router(collectibles.router)
app.include_router(location.router)
app.include_router(generate.router)
app.include_router(qrcode.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.on_event("shutdown")
def on_shutdown():
    shutdown_executor()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"msg": "keji API", "version": "1.0.0"}


# Vercel ASGI handler — 'app' is the FastAPI ASGI instance itself
# Vercel Python runtime auto-detects: if top-level var is ASGI app, it calls app(scope, receive, send)
handler = app