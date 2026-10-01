"""
Leave endpoints, backed by the ERP's leave request table. Mount in main.py:

    from leave_router import router as leave_router
    app.include_router(leave_router)

Totals per leave type come from the employee's latest SalStructureTest row
(SL / CL / UCL / PH). "Used" is the sum of the matching request column over
the current calendar year (by FromDate).

Holidays: days in a request that are paid holidays are split out and stored
in the PaidHoliday column; only the remaining days are charged to the chosen
leave type. An employee's holidays are their SalSelHolidays picks if they
have any, otherwise every date in SalHolidays.
"""
import logging
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text, cast, Date
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

import auth
import models
from database import get_db
from leave_models import SalLeaveReq, SalHoliday, SalSelHoliday
from leave_schemas import (
    LeaveRequestIn,
    LeaveRequestOut,
    LeaveBalanceOut,
    LeavePreviewOut,
    HolidayInfo,
)

log = logging.getLogger(__name__)
router = APIRouter()

# (code, label, SalStructureTest column for the yearly total,
#  request-table column that stores days taken of this type).
# Annual Leave has no total column in SalStructureTest -> None = uncapped.
LEAVE_TYPES = [
    ("CL", "Paid Casual Leave", "CL", "PaidCasual"),
    ("SL", "Sick Leave", "SL", "SickLeave"),
    ("PH", "Paid Holiday", "PH", "PaidHoliday"),
    ("AL", "Annual Leave", None, "PaidLeave"),
    ("UCL", "Unpaid Casual Leave", "UCL", "UnpaidCasual"),
    # Plain Unpaid Leave: no yearly total (None = uncapped), so it is always
    # available -- the fallback for an employee with no other leave left.
    ("UL", "Unpaid Leave", None, "UnpaidLeave"),
]
LABELS = {code: label for code, label, _, _ in LEAVE_TYPES}
REQUEST_COL = {code: rcol for code, _, _, rcol in LEAVE_TYPES}


def _latest_structure(db: Session, emp: models.SalEmployee):
    return (
        db.query(models.SalStructure)
        .filter(models.SalStructure.fkEmpId == emp.pkEmpId)
        .order_by(models.SalStructure.SalStart.desc())
        .first()
    )


def _employee_holidays(db: Session, structure, start: date, end: date) -> dict:
    """{date: holiday name} for this employee within [start, end].
    Falls back to "no holidays" (with a warning) if the holiday tables
    don't exist in this database, so leave requests keep working."""
    try:
        q = db.query(SalHoliday).filter(
            SalHoliday.HolidayDate >= datetime.combine(start, time.min),
            SalHoliday.HolidayDate < datetime.combine(end + timedelta(days=1), time.min),
        )
        picked = []
        if structure is not None:
            picked = [
                r[0]
                for r in db.query(SalSelHoliday.fkSHId)
                .filter(SalSelHoliday.fkSSId == structure.pkSSId)
                .all()
            ]
        if picked:
            q = q.filter(SalHoliday.pkSHId.in_(picked))
        return {h.HolidayDate.date(): h.PaidHoliday for h in q.all()}
    except ProgrammingError:
        db.rollback()
        log.warning("Holiday tables not found; treating request as having no holidays.")
        return {}


def _split(db: Session, emp: models.SalEmployee, from_date: date, to_date: date):
    """Returns (total_days, [(date, name), ...], chargeable_days)."""
    total = (to_date - from_date).days + 1
    holidays = _employee_holidays(db, _latest_structure(db, emp), from_date, to_date)
    hol_list = sorted(holidays.items())
    return total, hol_list, total - len(hol_list)


def _build_balances(db: Session, emp: models.SalEmployee) -> list[LeaveBalanceOut]:
    structure = _latest_structure(db, emp)

    year = date.today().year
    sums = [func.coalesce(func.sum(getattr(SalLeaveReq, rcol)), 0) for _, _, _, rcol in LEAVE_TYPES]
    used_row = (
        db.query(*sums)
        .filter(
            SalLeaveReq.fkEmpId == emp.pkEmpId,
            SalLeaveReq.FromDate >= datetime(year, 1, 1),
            SalLeaveReq.FromDate < datetime(year + 1, 1, 1),
        )
        .one()
    )

    out = []
    for (code, label, scol, _), used in zip(LEAVE_TYPES, used_row):
        used = float(used)
        if scol is None:
            total = None
        else:
            raw = getattr(structure, scol, None) if structure else None
            total = float(raw) if raw is not None else 0.0
        out.append(
            LeaveBalanceOut(
                leave_type=code,
                label=label,
                total=total,
                used=used,
                remaining=None if total is None else total - used,
            )
        )
    return out


def _to_out(r: SalLeaveReq) -> LeaveRequestOut:
    # A request can carry several types (e.g. 2 casual + 1 sick + a holiday).
    # Paid Holiday is shown separately via holiday_days, so skip it here.
    parts = [
        (c, float(getattr(r, rcol) or 0))
        for c, _, _, rcol in LEAVE_TYPES
        if c != "PH"
    ]
    parts = [(c, d) for c, d in parts if d > 0]
    if len(parts) == 1:
        label = LABELS[parts[0][0]]
    elif parts:
        label = " + ".join(f"{LABELS[c]} {d:g}" for c, d in parts)
    elif (r.PaidHoliday or 0) > 0:
        label = LABELS["PH"]
    else:
        label = "Other leave"
    code = parts[0][0] if parts else ("PH" if (r.PaidHoliday or 0) > 0 else "OTHER")
    return LeaveRequestOut(
        leave_req_no=r.RequestNo,
        date_applied=r.RequestDate,
        leave_type=code,
        leave_label=label,
        from_date=r.FromDate.date(),
        to_date=r.ToDate.date(),
        days=float(r.TotalLeave),
        holiday_days=float(r.PaidHoliday or 0),
        reason=r.Reason,
    )


@router.get("/leave-balances", response_model=list[LeaveBalanceOut])
def get_leave_balances(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    return _build_balances(db, current_user)


@router.get("/leave-preview", response_model=LeavePreviewOut)
def preview_leave(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Which days in the range are paid holidays for this employee, and how
    many days would actually be charged to leave. Used by the form to show
    the split before the employee applies."""
    if to_date < from_date:
        raise HTTPException(status_code=400, detail="to_date cannot be before from_date")
    total, hol_list, chargeable = _split(db, current_user, from_date, to_date)
    return LeavePreviewOut(
        total_days=total,
        holidays=[HolidayInfo(date=d, name=n) for d, n in hol_list],
        chargeable_days=chargeable,
    )


@router.post("/leave-requests", response_model=LeaveRequestOut)
def create_leave_request(
    payload: LeaveRequestIn,
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    # Holiday lookup happens BEFORE the table lock below: on a missing
    # holiday table it does a rollback, which would release the lock.
    total, hol_list, chargeable = _split(db, current_user, payload.from_date, payload.to_date)
    if chargeable <= 0:
        raise HTTPException(
            status_code=400,
            detail="Every selected day is already a paid holiday, so no leave is needed.",
        )

    # pkLRId has no sequence, so serialize writers: the lock is held until
    # commit/rollback, which keeps max+1 (and the balance check) race-free.
    db.execute(text(f'LOCK TABLE "{SalLeaveReq.__tablename__}" IN SHARE ROW EXCLUSIVE MODE'))

    allocated = sum(a.days for a in payload.allocations)
    if allocated != chargeable:
        raise HTTPException(
            status_code=400,
            detail=f"This request needs exactly {chargeable} day(s) of leave "
                   f"(after holidays), but you entered {allocated}.",
        )

    balances = {b.leave_type: b for b in _build_balances(db, current_user)}
    for a in payload.allocations:
        balance = balances[a.leave_type]
        if balance.remaining is not None and a.days > balance.remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Only {balance.remaining:g} day(s) of {balance.label} remaining; "
                       f"you asked for {a.days}.",
            )

    overlap = (
        db.query(SalLeaveReq)
        .filter(
            SalLeaveReq.fkEmpId == current_user.pkEmpId,
            cast(SalLeaveReq.FromDate, Date) <= payload.to_date,
            cast(SalLeaveReq.ToDate, Date) >= payload.from_date,
        )
        .first()
    )
    if overlap:
        raise HTTPException(
            status_code=400,
            detail=f"These dates overlap an existing request ({overlap.RequestNo}).",
        )

    next_pk = int(db.query(func.coalesce(func.max(SalLeaveReq.pkLRId), 0) + 1).scalar())

    record = SalLeaveReq(
        pkLRId=next_pk,
        RequestNo=f"LV{next_pk:06d}",
        FromDate=datetime.combine(payload.from_date, time.min),
        ToDate=datetime.combine(payload.to_date, time.min),
        fkEmpId=current_user.pkEmpId,
        Reason=payload.reason,
        TotalLeave=total,
        PaidHoliday=len(hol_list),
        **{REQUEST_COL[a.leave_type]: a.days for a in payload.allocations},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record)


@router.get("/leave-requests", response_model=list[LeaveRequestOut])
def list_leave_requests(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    rows = (
        db.query(SalLeaveReq)
        .filter(SalLeaveReq.fkEmpId == current_user.pkEmpId)
        .order_by(SalLeaveReq.RequestDate.desc())
        .all()
    )
    return [_to_out(r) for r in rows]