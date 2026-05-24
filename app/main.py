from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import get_db, engine, Base
from app.schemas import ShortenRequest, ShortenResponse, StatsResponse
from app import crud
from app.limiter import limiter

app = FastAPI(
    title="Clipr",
    description="A fast, async URL shortener with rate limiting.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.post("/shorten", response_model=ShortenResponse, status_code=201)
@limiter.limit("10/minute")
async def shorten_url(request: Request, body: ShortenRequest, db: AsyncSession = Depends(get_db)):
    url = await crud.create_url(db, str(body.url), body.ttl_days)
    return ShortenResponse(
        code=url.code,
        short_url=f"{settings.base_url}/{url.code}",
        original_url=url.original_url,
        expires_at=url.expires_at,
    )


@app.get("/stats/{code}", response_model=StatsResponse)
@limiter.limit("30/minute")
async def get_stats(request: Request, code: str, db: AsyncSession = Depends(get_db)):
    url = await _get_url_or_raise(db, code)
    return StatsResponse(
        code=url.code,
        original_url=url.original_url,
        click_count=url.click_count,
        created_at=url.created_at,
        expires_at=url.expires_at,
    )


@app.get("/{code}")
@limiter.limit("60/minute")
async def redirect_url(request: Request, code: str, db: AsyncSession = Depends(get_db)):
    url = await _get_url_or_raise(db, code)
    await crud.increment_click(db, code)
    return RedirectResponse(url=url.original_url, status_code=302)


async def _get_url_or_raise(db: AsyncSession, code: str):
    url = await crud.get_url(db, code)
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    expires = url.expires_at
    if expires:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Short URL has expired")
    return url
