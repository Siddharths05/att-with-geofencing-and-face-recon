import logging

from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    func,
    or_,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base

from audit import ActivityLog, init_audit
from database import engine, get_db

from model import (
    ContDepartment,
    SalaryEmployee,
)

from security import get_current_user


log = logging.getLogger(__name__)

# Switch the audit trail on as soon as the dashboard is loaded (i.e. when
# main.py imports this file at startup). Creates activity_log if needed;
# safe to run every start. No separate init_audit call needed in main.py.
if init_audit(engine):
    print("[audit] activity_log ready - auditing is ON")
else:
    print("[audit] could not create activity_log - auditing is OFF (see error above)")


# ==================================================
# DASHBOARD ROUTER
# Mounted in main.py under the same /api prefix:
#     app.include_router(dashboard_router, prefix="/api")
# ==================================================

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


# ==================================================
# READ-ONLY MODELS FOR THE ATTENDANCE-APP TABLES
#
# These use their OWN declarative base on purpose.
# main.py runs Base.metadata.create_all(), and if these
# were on the shared Base, a wrong table name would make
# it silently create an empty ghost table (the exact bug
# the attendance app's main.py warns about). On a
# separate base, create_all never sees them.
#
# Table names mirror the attendance app exactly:
#   "AttendancePunch"  (mixed case, quoted)
#   "LoanRequest"      (mixed case, quoted)
#   salleaverequest    (lowercase -- its DDL was unquoted)
#   salholidays        (lowercase)
# ==================================================

DashBase = declarative_base()


class AttendancePunch(DashBase):

    __tablename__ = "AttendancePunch"

    pkEAId = Column(Numeric(18, 0), primary_key=True)
    EmpCode = Column(String(30))
    AtDate = Column(String(50))          # 'YYYY-MM-DD'
    PunchInTime = Column(String(8))      # 'HH:MM:SS'
    PunchOutTime = Column(String(8))     # 'HH:MM:SS'


class LoanRequest(DashBase):

    __tablename__ = "LoanRequest"

    pkLoanReqId = Column(Integer, primary_key=True)
    fkEmpId = Column(Numeric(18, 0))
    LoanReqNo = Column(String(20))
    DateApplied = Column(DateTime)
    LoanType = Column(String(10))        # 'Advance' | 'Loan'
    Amount = Column(Numeric(12, 2))
    Installments = Column(Integer)


class LeaveRequest(DashBase):

    __tablename__ = "salleaverequest"

    pkLRId = Column(Numeric(18, 0), primary_key=True)
    RequestNo = Column(String(20))
    RequestDate = Column(DateTime)
    FromDate = Column(DateTime)
    ToDate = Column(DateTime)
    fkEmpId = Column(Numeric(18, 0))
    TotalLeave = Column(Numeric(18, 2))
    Authorize = Column(Boolean)
    Accepted = Column(String(10))        # 'Pending' by default


class Holiday(DashBase):

    __tablename__ = "salholidays"

    pkSHId = Column(Numeric(18, 0), primary_key=True)
    PaidHoliday = Column(String(40))     # the holiday's name
    HolidayDate = Column(DateTime)


# ==================================================
# "ACTIVE EMPLOYEE" RULE
# An employee is active until their date of leaving (DOL).
# No DOL, or a DOL in the future, means still employed.
# ==================================================

def _active_filter(now: datetime):

    return or_(
        SalaryEmployee.DOL.is_(None),
        SalaryEmployee.DOL > now,
    )


def _get_active_employees(db: Session, now: datetime) -> list:

    return (
        db.query(SalaryEmployee)
        .filter(_active_filter(now))
        .all()
    )


def _dept_names(db: Session) -> dict:

    return {
        d.pkDepId: (d.Department or "").strip()
        for d in db.query(ContDepartment).all()
    }


def _code(value) -> str:

    return (value or "").strip().lower()


def _err(exc) -> str:

    """One-line, human-readable database error for the diagnostics."""

    text = str(getattr(exc, "orig", exc)).strip().splitlines()

    return (text[0] if text else exc.__class__.__name__)[:200]


def _num(value) -> float:

    return float(value) if value is not None else 0.0


# ==================================================
# EMPLOYEE / DEPARTMENT NUMBERS
# ==================================================

def get_employee_stats(db: Session, now: datetime) -> dict:

    active = _active_filter(now)

    total_employees = (
        db.query(func.count(SalaryEmployee.pkEmpId))
        .filter(active)
        .scalar()
        or 0
    )

    new_joiners_30d = (
        db.query(func.count(SalaryEmployee.pkEmpId))
        .filter(
            active,
            SalaryEmployee.DOJ.isnot(None),
            SalaryEmployee.DOJ >= now - timedelta(days=30),
        )
        .scalar()
        or 0
    )

    # ---- comparison figures (for the trend arrows) ----
    week_ago = now - timedelta(days=7)

    total_7d_ago = (
        db.query(func.count(SalaryEmployee.pkEmpId))
        .filter(
            or_(SalaryEmployee.DOJ.is_(None), SalaryEmployee.DOJ <= week_ago),
            or_(SalaryEmployee.DOL.is_(None), SalaryEmployee.DOL > week_ago),
        )
        .scalar()
        or 0
    )

    prev_joiners = (
        db.query(func.count(SalaryEmployee.pkEmpId))
        .filter(
            active,
            SalaryEmployee.DOJ.isnot(None),
            SalaryEmployee.DOJ >= now - timedelta(days=60),
            SalaryEmployee.DOJ < now - timedelta(days=30),
        )
        .scalar()
        or 0
    )

    # fkDepId is a plain string column (no ORM FK), so this is an
    # explicit outer join. Employees with no / unknown department
    # are grouped as "Unassigned" instead of silently vanishing.
    rows = (
        db.query(
            ContDepartment.Department,
            func.count(SalaryEmployee.pkEmpId),
        )
        .select_from(SalaryEmployee)
        .outerjoin(
            ContDepartment,
            ContDepartment.pkDepId == SalaryEmployee.fkDepId,
        )
        .filter(active)
        .group_by(ContDepartment.Department)
        .all()
    )

    merged = {}
    for name, count in rows:
        key = (name or "").strip() or "Unassigned"
        merged[key] = merged.get(key, 0) + int(count)

    departments = sorted(
        (
            {"name": name, "count": count}
            for name, count in merged.items()
        ),
        key=lambda d: (d["name"] == "Unassigned", -d["count"]),
    )

    return {
        "total_employees": int(total_employees),
        "new_joiners_30d": int(new_joiners_30d),
        "new_joiners_prev_30d": int(prev_joiners),
        "total_employees_7d_ago": int(total_7d_ago),
        "department_count": len(
            [d for d in departments if d["name"] != "Unassigned"]
        ),
        "departments": departments,
    }


# ==================================================
# ATTENDANCE
#
# present   = active employees with a punch-in today
# on_leave  = active, not present, with an approved leave
#             request covering today
# absent    = active - present - on_leave
# holiday   = today is in salholidays -> absent is None
#             (otherwise everyone shows "absent" on holidays)
#
# "Approved" leave = Authorize is true OR Accepted reads
# accepted/approved. Confirm the real Accepted values in
# your data and adjust _APPROVED below if they differ.
# ==================================================

_APPROVED = ("accepted", "approved", "yes")


def _hour_label(h: int) -> str:

    suffix = "AM" if h < 12 else "PM"
    return f"{(h % 12) or 12} {suffix}"


def get_attendance_today(db: Session, now: datetime, diag: dict) -> dict:

    unavailable = {
        "available": False,
        "present": None,
        "absent": None,
        "on_leave": None,
        "present_yesterday": None,
        "holiday": None,
        "checked_in": [],
        "flow": [],
    }

    try:

        today = now.date()
        today_str = today.isoformat()

        employees = _get_active_employees(db, now)
        by_code = {_code(e.EmpCode): e for e in employees if _code(e.EmpCode)}
        depts = _dept_names(db)

        punches = (
            db.query(AttendancePunch)
            .filter(
                AttendancePunch.AtDate == today_str,
                AttendancePunch.PunchInTime.isnot(None),
            )
            .order_by(AttendancePunch.PunchInTime.desc())
            .all()
        )

        # one entry per active employee (a duplicate row shouldn't double count)
        seen = {}
        for p in punches:
            emp = by_code.get(_code(p.EmpCode))
            if emp is not None and emp.pkEmpId not in seen:
                seen[emp.pkEmpId] = (emp, p)

        present_ids = set(seen)

        # yesterday's headcount, for the "vs yesterday" arrow
        yesterday_str = (today - timedelta(days=1)).isoformat()
        y_codes = {
            _code(p.EmpCode)
            for p in db.query(AttendancePunch).filter(
                AttendancePunch.AtDate == yesterday_str,
                AttendancePunch.PunchInTime.isnot(None),
            )
        }
        present_yesterday = len(y_codes & set(by_code))

        checked_in = []
        for emp, p in seen.values():
            out = (p.PunchOutTime or "").strip()
            checked_in.append(
                {
                    "emp_id": int(emp.pkEmpId),
                    "name": (emp.Employee or "").strip(),
                    "department": depts.get(emp.fkDepId, "") or "Unassigned",
                    "time": (p.PunchInTime or "")[:5],
                    "status": "Checked Out" if out else "Checked In",
                }
            )
        checked_in.sort(key=lambda r: r["time"], reverse=True)

        # ---- hourly flow ----
        hours = [
            int(p.PunchInTime[:2])
            for _, p in seen.values()
            if p.PunchInTime and p.PunchInTime[:2].isdigit()
        ]
        out_hours = [
            int(p.PunchOutTime[:2])
            for _, p in seen.values()
            if p.PunchOutTime and p.PunchOutTime[:2].isdigit()
        ]
        start = min([8] + hours + out_hours)
        end = min(max([now.hour, 10] + hours + out_hours), 23)
        flow = [
            {
                "hour": _hour_label(h),
                "count": hours.count(h),
                "out": out_hours.count(h),
            }
            for h in range(start, end + 1)
        ]

        # ---- holiday? ----
        holiday_name = None
        try:
            hol = (
                db.query(Holiday)
                .filter(
                    Holiday.HolidayDate >= datetime.combine(today, datetime.min.time()),
                    Holiday.HolidayDate < datetime.combine(
                        today + timedelta(days=1), datetime.min.time()
                    ),
                )
                .first()
            )
            holiday_name = (hol.PaidHoliday or "Holiday").strip() if hol else None
        except SQLAlchemyError:
            db.rollback()
            log.warning("salholidays not readable; holidays ignored.")

        # ---- approved leave covering today ----
        on_leave_ids = set()
        try:
            day_start = datetime.combine(today, datetime.min.time())
            leaves = (
                db.query(LeaveRequest)
                .filter(
                    LeaveRequest.FromDate < day_start + timedelta(days=1),
                    LeaveRequest.ToDate >= day_start,
                    or_(
                        LeaveRequest.Authorize.is_(True),
                        func.lower(LeaveRequest.Accepted).in_(_APPROVED),
                    ),
                )
                .all()
            )
            active_ids = {e.pkEmpId for e in employees}
            on_leave_ids = {
                l.fkEmpId for l in leaves if l.fkEmpId in active_ids
            } - present_ids
        except SQLAlchemyError:
            db.rollback()
            log.warning("salleaverequest not readable; leave ignored.")

        total = len(employees)
        present = len(present_ids)
        on_leave = len(on_leave_ids)

        return {
            "available": True,
            "present": present,
            "absent": None if holiday_name else max(total - present - on_leave, 0),
            "on_leave": on_leave,
            "present_yesterday": present_yesterday,
            "holiday": holiday_name,
            "checked_in": checked_in[:15],
            "flow": flow,
        }

    except SQLAlchemyError as exc:
        db.rollback()
        diag["attendance"] = _err(exc)
        log.exception("Attendance summary failed (is AttendancePunch in this DB?)")
        return unavailable


# ==================================================
# ACTIVITY FEED
# sign-ins / sign-outs (today), loan applications and
# leave requests (last 7 days), newest first.
# ==================================================

def get_activity_feed(db: Session, now: datetime, diag: dict) -> dict:

    items = []
    any_source = False

    employees = {}
    try:
        employees = {
            e.pkEmpId: e for e in _get_active_employees(db, now)
        }
    except SQLAlchemyError:
        db.rollback()

    def name_of(emp_id) -> str:
        e = employees.get(emp_id)
        return (e.Employee or "").strip() if e else "An employee"

    since = now - timedelta(days=7)
    today_str = now.date().isoformat()

    # ---------- sign-ins / sign-outs ----------
    try:
        by_code = {_code(e.EmpCode): e for e in employees.values()}
        rows = (
            db.query(AttendancePunch)
            .filter(
                AttendancePunch.AtDate == today_str,
                AttendancePunch.PunchInTime.isnot(None),
            )
            .all()
        )
        any_source = True

        for p in rows:
            emp = by_code.get(_code(p.EmpCode))
            if emp is None:
                continue

            def stamp(t):
                try:
                    return datetime.fromisoformat(f"{today_str}T{t.strip()}").isoformat()
                except (ValueError, AttributeError):
                    return None

            t_in = stamp(p.PunchInTime)
            if t_in:
                items.append(
                    {
                        "type": "signin",
                        "title": f"{name_of(emp.pkEmpId)} signed in",
                        "description": f"Checked in at {p.PunchInTime[:5]}",
                        "time": t_in,
                    }
                )

            t_out = stamp(p.PunchOutTime) if (p.PunchOutTime or "").strip() else None
            if t_out:
                items.append(
                    {
                        "type": "signin",
                        "title": f"{name_of(emp.pkEmpId)} signed out",
                        "description": f"Checked out at {p.PunchOutTime[:5]}",
                        "time": t_out,
                    }
                )
    except SQLAlchemyError as exc:
        db.rollback()
        diag["signins"] = _err(exc)
        log.warning("AttendancePunch not readable; sign-ins skipped.")

    # ---------- loan applications ----------
    try:
        loans = (
            db.query(LoanRequest)
            .filter(LoanRequest.DateApplied >= since)
            .order_by(LoanRequest.DateApplied.desc())
            .limit(20)
            .all()
        )
        any_source = True

        for r in loans:
            n = r.Installments or 1
            items.append(
                {
                    "type": "loan",
                    "title": f"{name_of(r.fkEmpId)} applied for "
                             f"{'an advance' if r.LoanType == 'Advance' else 'a loan'}",
                    "description": f"\u20b9{_num(r.Amount):,.0f}"
                                   f" \u00b7 {n} installment{'s' if n != 1 else ''}"
                                   f" \u00b7 {r.LoanReqNo or ''}".rstrip(" \u00b7"),
                    "time": r.DateApplied.isoformat() if r.DateApplied else None,
                }
            )
    except SQLAlchemyError as exc:
        db.rollback()
        diag["loans"] = _err(exc)
        log.warning("LoanRequest not readable; loans skipped.")

    # ---------- leave requests ----------
    try:
        leaves = (
            db.query(LeaveRequest)
            .filter(LeaveRequest.RequestDate >= since)
            .order_by(LeaveRequest.RequestDate.desc())
            .limit(20)
            .all()
        )
        any_source = True

        for r in leaves:
            days = _num(r.TotalLeave)
            status = (r.Accepted or "Pending").strip()
            items.append(
                {
                    "type": "leave",
                    "title": f"{name_of(r.fkEmpId)} applied for leave",
                    "description": f"{r.FromDate:%d %b} \u2192 {r.ToDate:%d %b}"
                                   f" \u00b7 {days:g} day{'s' if days != 1 else ''}"
                                   f" \u00b7 {status}",
                    "time": r.RequestDate.isoformat() if r.RequestDate else None,
                }
            )
    except SQLAlchemyError as exc:
        db.rollback()
        diag["leave"] = _err(exc)
        log.warning("salleaverequest not readable; leave skipped.")

    # ---------- audit trail: created / updated / deleted ... ----------
    try:
        logs = (
            db.query(ActivityLog)
            .filter(ActivityLog.created_at >= since)
            .order_by(ActivityLog.created_at.desc())
            .limit(30)
            .all()
        )
        any_source = True

        for r in logs:

            entity = (r.entity or "record")
            entity = entity[:1].upper() + entity[1:]
            verb = "were" if entity.lower().endswith("rights") else "was"
            name = f" \u201c{r.entity_name}\u201d" if r.entity_name else ""

            by = f"by {r.actor_name}" if r.actor_name else ""
            desc = " \u00b7 ".join(p for p in (r.detail, by) if p)

            items.append(
                {
                    "type": r.action,
                    "title": f"{entity}{name} {verb} {r.action}",
                    "description": desc,
                    "time": r.created_at.isoformat() if r.created_at else None,
                }
            )
    except SQLAlchemyError as exc:
        db.rollback()
        diag["audit"] = _err(exc)
        log.warning("activity_log not readable; audit entries skipped.")

    items = [i for i in items if i["time"]]
    items.sort(key=lambda i: i["time"], reverse=True)

    return {
        "available": any_source,
        "items": items[:15],
    }


# ==================================================
# GET /api/dashboard/summary
# One call for the whole page. Any authenticated user,
# same rule as the other GET routes (see the pending
# view-rights decision in security.py).
# ==================================================

@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):

    now = datetime.now()

    # per-source failure reasons, shown by the UI instead of a bare
    # "not connected" so a wrong table name is obvious at a glance
    diag = {}

    return {
        "generated_at": now.isoformat(),
        "employees": get_employee_stats(db, now),
        "attendance": get_attendance_today(db, now, diag),
        "activity": get_activity_feed(db, now, diag),
        "diagnostics": diag,
    }

#end of file
