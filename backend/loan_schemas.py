"""
Request/response models for the loan-request feature. Separate from
schemas.py so existing code isn't touched -- import these into main.py
alongside your existing schemas.
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator


class LoanRequestIn(BaseModel):
    """What the client sends. loan_req_no and date_applied are NOT here --
    both are auto-generated server-side (see loan_router.create_loan_request),
    never accepted from the client."""

    loan_type: Literal["Advance", "Loan"]
    amount: float = Field(gt=0)

    # Only meaningful when loan_type == "Loan". Optional here because an
    # "Advance" request doesn't need the client to send it at all -- if it
    # is sent for an Advance, it's silently overridden to 1 below rather
    # than rejected, since the UI may just leave the field's last value in
    # place while disabling it.
    installments: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _apply_advance_rule(self):
        """An Advance is always a single, one-shot installment -- that's
        the whole distinction between it and a Loan. Force it here (not
        just in the UI) so the rule holds no matter what the client sends."""
        if self.loan_type == "Advance":
            self.installments = 1
        elif self.installments is None:
            raise ValueError("installments is required when loan_type is 'Loan'")
        return self


class LoanRequestOut(BaseModel):
    loan_req_no: Optional[str] = None
    date_applied: datetime
    loan_type: str
    amount: float
    installments: int

    class Config:
        from_attributes = True
