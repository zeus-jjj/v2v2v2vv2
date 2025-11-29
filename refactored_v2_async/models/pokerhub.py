
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class UTMData(BaseModel):
    utm_medium: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None


class PokerHubCourse(BaseModel):
    name: str
    lessons: List[str] = Field(default_factory=list)


class PokerHubUser(BaseModel):
    user_id: int = Field(..., alias='user_id')
    tg_id: int
    ph_nickname: Optional[str] = None
    ph_username: Optional[str] = None
    tg_username: Optional[str] = None
    tg_nickname: Optional[str] = None

    authorization_date: Optional[datetime] = None
    last_visit_date: Optional[datetime] = None

    referer: Optional[str] = None
    utm: Optional[UTMData] = None
    rc: Optional[str] = None

    group: List[str] = Field(default_factory=list)
    courses: Dict[str, List[str]] = Field(default_factory=dict)
    lessons: Optional[List[str]] = None

    class Config:
        populate_by_name = True
