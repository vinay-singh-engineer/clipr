from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    url: HttpUrl
    ttl_days: Optional[int] = None


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    original_url: str
    expires_at: Optional[datetime] = None


class StatsResponse(BaseModel):
    code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
