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
    # None = altitude wasn't checked (device sent no altitude reading).
    # True/False = whether it matched OFFICE_ALTITUDE_METERS within tolerance.
    altitude_ok: Optional[bool] = None
    altitude_diff_meters: Optional[float] = None


class AttendanceOut(BaseModel):
    """Mirrors EmpAttendancePunch. face_match/face_similarity_percent are
    NOT columns on that table (the physical ERP table has no such
    columns) -- they're only ever returned on the check-in response
    itself, computed fresh for that request, and are None on anything
    read back later (e.g. /attendance/history). If you need to audit
    historical face-match outcomes, that needs a separate table keyed by
    pkEAId -- flagging rather than silently dropping the data."""

    pkEAId: int
    emp_code: str
    pay_code: str
    at_date: str
    punch_in_time: Optional[str] = None
    punch_out_time: Optional[str] = None
    device: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    status: str  # "present" or "rejected" -- computed, not stored (see main.py)
    face_match: Optional[bool] = None
    face_similarity_percent: Optional[float] = None

    class Config:
        from_attributes = True