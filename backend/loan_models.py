"""
Model for the loan/advance request feature. Kept separate from models.py
so existing code isn't touched -- import this into main.py alongside your
existing models.

Maps to "LoanRequest" -- a table this app OWNS (unlike SalEmployee /
SalStructureTest / AttendancePunch, which belong to the legacy ERP db).
Created via the explicit CREATE TABLE statement already run against
attendance_app, not create_all -- see main.py's top-of-file comment for
why this app never calls create_all.
"""
from sqlalchemy import Column, BigInteger, Numeric, String, DateTime, Integer, func
from database import Base


class LoanRequest(Base):
    __tablename__ = "LoanRequest"

    pkLoanReqId = Column(BigInteger, primary_key=True)
    fkEmpId = Column(Numeric(18, 0), nullable=False, index=True)

    # Filled in by the app right after insert, once pkLoanReqId is known
    # (see loan_router._generate_loan_req_no) -- nullable here only for
    # the brief window between insert and that follow-up update.
    LoanReqNo = Column(String(20), unique=True, nullable=True)

    # DB-side default so "date of applying" is always the server's insert
    # time, never something the client could override.
    DateApplied = Column(DateTime, nullable=False, server_default=func.now())

    LoanType = Column(String(10), nullable=False)  # 'Advance' or 'Loan' -- enforced by a CHECK constraint in the DB
    Amount = Column(Numeric(12, 2), nullable=False)

    # Number of installments. For 'Advance' requests this is always 1,
    # forced server-side in loan_router.create_loan_request regardless of
    # what the client sends -- see that function's docstring.
    Installments = Column(Integer, nullable=False)