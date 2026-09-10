from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FaceCheckOut(BaseModel):
    face_detected: bool
    is_match: bool
    similarity_percent: float


class LocationCheckOut(BaseModel):
    location_required: bool
    photo_required: bool
    within_range: bool
    distance_meters: Optional[float] = None
    allowed_radius_meters: float


class AttendanceOut(BaseModel):
    id: int
    username: str
    status: str
    distance_meters: Optional[float] = None
    face_match: Optional[bool] = None
    face_similarity_percent: Optional[float] = None
    checked_in_at: datetime

    class Config:
        from_attributes = True