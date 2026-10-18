from pydantic import BaseModel, HttpUrl 
from datetime import datetime
from typing import Optional

class LinkCreate(BaseModel):
    original_url: HttpUrl

class LinkResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    created_at: datetime

    class Config:
        from_attributes = True

class ClickEventCreate(BaseModel):
    link_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None

class ClickEventResponse(BaseModel):
    id: int
    link_id: int
    clicked_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None

        