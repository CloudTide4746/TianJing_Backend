"""刻迹 — FastAPI Backend.

Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from starlette.formparsers import MultiPartParser
from starlette.requests import Request

# Increase multipart part size limit: 1MB → 10MB (for base64 photos)
_10MB = 10 * 1024 * 1024
MultiPartParser.__init__.__kwdefaults__["max_part_size"] = _10MB
Request.form.__kwdefaults__["max_part_size"] = _10MB
Request._get_form.__kwdefaults__["max_part_size"] = _10MB

from database import init_db, shutdown_executor
from routers import collectibles, location, generate, qrcode

app = FastAPI(title="刻迹 API", version="1.0.0")

# CORS — allow Expo dev clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files — serve uploaded photos (only if uploads dir exists)
uploads_dir = Path(__file__).parent / "uploads"
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Routers
app.include_router(collectibles.router)
app.include_router(location.router)
app.include_router(generate.router)
app.include_router(qrcode.router)


@app.on_event("startup")
def on_startup():
    uploads_dir.mkdir(exist_ok=True)
    init_db()


@app.on_event("shutdown")
def on_shutdown():
    shutdown_executor()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"msg": "刻迹 API", "version": "1.0.0"}


# Vercel serverless handler — ASGI callable interface
async def handler(scope, receive, send):
    await app(scope, receive, send)