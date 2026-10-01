"""
Model for the ERP's existing SalLeaveReq table (no new table for leave).

Every column is declared because most are NOT NULL with no DB default, so
an INSERT has to supply them. The ones this app doesn't deal with get
neutral client-side defaults below (zeros / empty strings / 'Pending').
The ERP's own screens are the source of truth for those columns.

NOTE: pkLRId has no identity/sequence in the DDL, so leave_router assigns
it as max+1 under a table lock -- see create_leave_request there.
"""
from sqlalchemy import Column, Numeric, String, DateTime, Boolean, func
from database import Base

ZERO = 0


def _num(**kw):
    return Column(Numeric(18, 2), nullable=False, default=ZERO, **kw)


class SalLeaveReq(Base):
    # The DDL for this table was run unquoted (CREATE TABLE SalLeaveReq), so
    # Postgres stored the name lowercase. Column names were quoted, so they
    # keep their exact case. If this table is ever recreated with a quoted
    # name, change this string to match.
    __tablename__ = "salleaverequest"

    # --- Columns this app actually uses ---
    pkLRId = Column(Numeric(18, 0), primary_key=True, autoincrement=False)
    RequestNo = Column(String(20), nullable=False)
    RequestDate = Column(DateTime, nullable=False, default=func.now())
    FromDate = Column(DateTime, nullable=False)
    ToDate = Column(DateTime, nullable=False)
    fkEmpId = Column(Numeric(18, 0), nullable=False, index=True)
    Reason = Column(String(255), nullable=False)
    TotalLeave = _num()  # total days requested

    # One column per leave type -- the requested days go in exactly one.
    PaidLeave = _num()      # Annual Leave (AL)
    PaidHoliday = _num()    # Paid Holiday (PH)
    SickLeave = _num()      # Sick Leave (SL)
    PaidCasual = _num()     # Paid Casual Leave (CL)
    UnpaidCasual = _num()   # Unpaid Casual Leave (UCL)

    # --- Not dealt with by this app: neutral defaults so INSERT succeeds ---
    BalLeave = _num()
    BalPaid = _num()
    BalSick = _num()
    BalPaidCasual = _num()
    BalUnpaidCasual = _num()
    Absent = _num()
    RestDay = _num()
    UnpaidLeave = _num()  # Unpaid Leave (UL) -- used by this app
    Maternity = _num()
    Sync = Column(String(1), nullable=False, default="N")
    SysDefined = Column(Boolean, nullable=False, default=False)
    DateTimestamp = Column(DateTime, nullable=False, default=func.now())
    fkUserId = Column(String(5), nullable=False, default="")
    LastStatus = Column(String(10), nullable=False, default="Pending")
    Authorize = Column(Boolean, nullable=False, default=False)
    ATimestamp = Column(DateTime, nullable=True)
    fkAUserId = Column(String(5), nullable=True)
    Accepted = Column(String(10), nullable=False, default="Pending")
    ARemarks = Column(String(255), nullable=False, default="")
    Remarks = Column(String(255), nullable=False, default="")


class SalHoliday(Base):
    """Master list of government holidays (ERP table SalHolidays).
    Read-only here -- pk, name and date only."""
    __tablename__ = "salholidays"

    pkSHId = Column(Numeric(18, 0), primary_key=True, autoincrement=False)
    PaidHoliday = Column(String(40), nullable=False)  # the holiday's name
    HolidayDate = Column(DateTime, nullable=False)


class SalSelHoliday(Base):
    """Links a salary structure (fkSSId = SalStructureTest.pkSSId) to the
    specific holidays chosen for that employee (fkSHId = SalHolidays.pkSHId).
    Read-only here."""
    __tablename__ = "salselholidays"

    pkSSHId = Column(Numeric(18, 0), primary_key=True, autoincrement=False)
    fkSHId = Column(Numeric(18, 0), nullable=False)
    fkSSId = Column(Numeric(18, 0), nullable=False)