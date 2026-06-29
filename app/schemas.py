from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field, HttpUrl


class ShortenRequest(BaseModel):
    url: Annotated[HttpUrl, Field(max_length=2048)]
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
