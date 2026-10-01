"""
Loan/advance request endpoints. Import and mount this in main.py:

    from loan_router import router as loan_router
    app.include_router(loan_router)

No changes needed to your existing main.py routes -- this is additive.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import auth
import models
from database import get_db
from loan_models import LoanRequest
from loan_schemas import LoanRequestIn, LoanRequestOut


router = APIRouter()


def _generate_loan_req_no(pk: int) -> str:
    """'LN' + the row's own pkLoanReqId, zero-padded to 6 digits (e.g.
    'LN000123'). This can only be computed AFTER the row exists (Postgres
    has no way to reference a row's own freshly-generated serial value in
    that same row's default), so create_loan_request inserts first, then
    fills this in with a follow-up update -- see that function below."""
    return f"LN{pk:06d}"


@router.post("/loan-requests", response_model=LoanRequestOut)
def create_loan_request(
    payload: LoanRequestIn,
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Creates a loan/advance request for the logged-in employee.

    - loan_req_no is auto-generated here, never accepted from the client.
    - date_applied is auto-set by the DB (LoanRequest.DateApplied's
      server_default), never accepted from the client.
    - installments is forced to 1 for 'Advance' requests by
      LoanRequestIn's validator, regardless of what was sent.
    """
    record = LoanRequest(
        fkEmpId=current_user.pkEmpId,
        LoanType=payload.loan_type,
        Amount=payload.amount,
        Installments=payload.installments,
    )
    db.add(record)
    db.commit()
    db.refresh(record)  # populates pkLoanReqId (and DateApplied's server default)

    record.LoanReqNo = _generate_loan_req_no(record.pkLoanReqId)
    db.commit()
    db.refresh(record)

    return LoanRequestOut(
        loan_req_no=record.LoanReqNo,
        date_applied=record.DateApplied,
        loan_type=record.LoanType,
        amount=float(record.Amount),
        installments=record.Installments,
    )


@router.get("/loan-requests", response_model=list[LoanRequestOut])
def list_loan_requests(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """The logged-in employee's own loan/advance requests, newest first."""
    records = (
        db.query(LoanRequest)
        .filter(LoanRequest.fkEmpId == current_user.pkEmpId)
        .order_by(LoanRequest.DateApplied.desc())
        .all()
    )
    return [
        LoanRequestOut(
            loan_req_no=r.LoanReqNo,
            date_applied=r.DateApplied,
            loan_type=r.LoanType,
            amount=float(r.Amount),
            installments=r.Installments,
        )
        for r in records
    ]
