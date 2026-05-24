import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models import URL


def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


async def create_url(db: AsyncSession, original_url: str, ttl_days: Optional[int] = None) -> URL:
    for _ in range(5):
        code = _generate_code()
        result = await db.execute(select(URL).where(URL.code == code))
        if not result.scalar_one_or_none():
            break

    expires_at = None
    if ttl_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)

    url = URL(code=code, original_url=original_url, expires_at=expires_at)
    db.add(url)
    await db.commit()
    await db.refresh(url)
    return url


async def get_url(db: AsyncSession, code: str) -> Optional[URL]:
    result = await db.execute(
        select(URL).where(URL.code == code, URL.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def increment_click(db: AsyncSession, code: str) -> None:
    await db.execute(
        update(URL).where(URL.code == code).values(click_count=URL.click_count + 1)
    )
    await db.commit()
