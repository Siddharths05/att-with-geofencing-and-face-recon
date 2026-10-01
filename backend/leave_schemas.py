"""Request/response models for the leave-request feature."""
from datetime import date, datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class LeaveAllocation(BaseModel):
    # PH (Paid Holiday) is intentionally NOT applicable -- holidays are
    # granted automatically; they're split out of a request, not requested.
    leave_type: Literal["CL", "SL", "AL", "UCL", "UL"]
    days: int = Field(gt=0)


class LeaveRequestIn(BaseModel):
    # One request can be split across several leave types, e.g.
    # [{"CL", 2}, {"SL", 1}]. The router checks that the days add up to the
    # chargeable days in the date range (total days minus holidays).
    allocations: list[LeaveAllocation] = Field(min_length=1)
    from_date: date
    to_date: date
    reason: str = Field(max_length=255)

    @field_validator("allocations")
    @classmethod
    def _no_duplicate_types(cls, v: list[LeaveAllocation]) -> list[LeaveAllocation]:
        types = [a.leave_type for a in v]
        if len(types) != len(set(types)):
            raise ValueError("each leave type can appear only once")
        return v

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("reason is required")
        return v

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.to_date < self.from_date:
            raise ValueError("to_date cannot be before from_date")
        return self


class LeaveBalanceOut(BaseModel):
    leave_type: str
    label: str
    total: Optional[float] = None      # None = no limit configured (e.g. Annual Leave)
    used: float
    remaining: Optional[float] = None  # None when total is None


class HolidayInfo(BaseModel):
    date: date
    name: str


class LeavePreviewOut(BaseModel):
    total_days: int
    holidays: list[HolidayInfo]
    chargeable_days: int  # total_days minus holidays -- what comes off the leave balance


class LeaveRequestOut(BaseModel):
    leave_req_no: Optional[str] = None
    date_applied: datetime
    leave_type: str
    leave_label: str
    from_date: date
    to_date: date
    days: float
    holiday_days: float = 0
    reason: str