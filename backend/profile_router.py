"""
Employee profile endpoint. Import and mount this in main.py:

    from profile_router import router as profile_router
    app.include_router(profile_router)

No changes needed to your existing main.py routes -- this is additive.
"""
import base64

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import auth
import models
from database import get_db


def _photo_to_data_uri(photo_bytes) -> str | None:
    """SalEmployee.Photo is stored as raw image bytes (whatever format was
    uploaded) with no separate column recording the format, so sniff the
    magic bytes to pick a mime type for the data URI. Defaults to jpeg,
    which is what the app's own photo-capture flow produces."""
    if not photo_bytes:
        return None
    raw = bytes(photo_bytes)
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif raw.startswith(b"\xff\xd8"):
        mime = "image/jpeg"
    else:
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


from profile_models import (
    SalEmpContact,
    SalEmpDocuments,
    SalEmpRelation,
    ContDepartment,
    ContDesignation,
    ContQualification,
    ContRelationship,
    ContMOC,
    ContCommon,
    AcctAccount,
    DocMasRecords,
)
from profile_schemas import (
    EmployeeProfileOut,
    BasicInfo,
    MoreInfo,
    ContactEntry,
    DocumentEntry,
    RelationEntry,
)

router = APIRouter()


# ==================================================
# CALL-TIME LOOKUP RESOLUTION
# No caching, no joins baked into the queries above -- each code is
# looked up against its master table right here, at request time,
# via a plain by-PK SELECT. Simplest option and always fresh (picks
# up edits made in the ERP admin panel immediately); the tradeoff is
# one extra small query per code per request, which is fine at
# single-profile scale. Swap for a join or an in-memory cache later
# if this route ever needs to return many employees at once.
# ==================================================

def _resolve(db: Session, model, pk_attr: str, label_attr: str, code):
    """Look up `code` in `model` by its PK column and return the label
    column's value, or None if there's no code or no matching row."""
    if not code:
        return None
    row = db.query(model).filter(getattr(model, pk_attr) == code).first()
    return getattr(row, label_attr) if row else None


def _resolve_employee_name(db: Session, emp_id):
    """referred_by / witness fields point at another SalEmployee row
    (fkREmpId / fkW1EmpId / fkW2EmpId), not a lookup master table."""
    if not emp_id:
        return None
    row = (
        db.query(models.SalEmployee)
        .filter(models.SalEmployee.pkEmpId == emp_id)
        .first()
    )
    return row.Employee if row else None


@router.get("/profile", response_model=EmployeeProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Returns the logged-in employee's own profile, categorized into
    basic info / contacts / documents / family. Codes stored on
    SalEmployee (fkDepId, fkDegId, fkQualId, fkBnkId, fkAcctId, ...) are
    resolved to their display names here, at call time, against the same
    master tables the ERP admin backend uses -- see the _resolve() note
    above for why this isn't cached/joined instead."""

    basic = BasicInfo(
        emp_code=current_user.EmpCode,
        name=current_user.Employee,
        username=current_user.UserName,
        date_of_birth=current_user.DOB.date().isoformat() if current_user.DOB else None,
        # Male is nullable on the real table (not every legacy row has it
        # set) -- collapsing that straight to "Female" would misreport an
        # unknown value as a known one, so keep None distinct.
        gender=(
            "Male" if current_user.Male is True
            else "Female" if current_user.Male is False
            else None
        ),
        marital_status=(
            "Married" if current_user.Married is True
            else "Unmarried" if current_user.Married is False
            else None
        ),
        department_code=_resolve(db, ContDepartment, "pkDepId", "Department", current_user.fkDepId),
        designation_code=_resolve(db, ContDesignation, "pkDesId", "Designation", current_user.fkDegId),
        # DOJ is nullable on the real table even though it's meant to
        # always be set -- guard rather than crash the whole profile
        # response over one missing date.
        joining_date=current_user.DOJ.date().isoformat() if current_user.DOJ else None,
        leaving_date=current_user.DOL.date().isoformat() if current_user.DOL else None,
        blood_group=current_user.BloodGrp,
        aadhar_no=current_user.Aadhar,
        qualification_code=_resolve(db, ContQualification, "pkQuaId", "Qualification", current_user.fkQualId),
        anniversary=current_user.Anni.date().isoformat() if current_user.Anni else None,
        resident_address=current_user.PAddress,
        native_address=current_user.NAddress,
        bank_code=_resolve(db, ContCommon, "pkContId", "ContactName", current_user.fkBnkId),
        account_no=current_user.AccountNo,
        uan_no=current_user.PFNo,
        esic_no=current_user.ESICNo,
        pan_no=current_user.PANNo,
        rtgs=current_user.RTGS,
        short_address=current_user.SAddress,
        work_place=current_user.WP,
        height=str(current_user.Height) if current_user.Height is not None else None,
        weight=str(current_user.Weight) if current_user.Weight is not None else None,
        cash_account_code=_resolve(db, AcctAccount, "pkAcctId", "Account", current_user.fkAcctId),
        photo_base64=_photo_to_data_uri(current_user.Photo),
    )

    more_info = MoreInfo(
        identification_mark=current_user.Mark,
        total_experience=current_user.Experience,
        referred_by_emp_id=_resolve_employee_name(db, current_user.fkREmpId),
        police_station=current_user.Police,
        police_address=current_user.AddPolice,
        police_contact=current_user.ContPolice,
        witness1_emp_id=_resolve_employee_name(db, current_user.fkW1EmpId),
        witness2_emp_id=_resolve_employee_name(db, current_user.fkW2EmpId),
        inform_uan_on_leaving=current_user.InformPF,
        inform_esic_on_leaving=current_user.InformESIC,
        personality1_name=current_user.Personality1,
        personality1_designation_code=_resolve(db, ContDesignation, "pkDesId", "Designation", current_user.fkP1DesId),
        personality1_address=current_user.P1Address,
        personality1_contact=current_user.P1Contact,
        personality2_name=current_user.Personality2,
        personality2_designation_code=_resolve(db, ContDesignation, "pkDesId", "Designation", current_user.fkP2DesId),
        personality2_address=current_user.P2Address,
        personality2_contact=current_user.P2Contact,
    )

    contacts = (
        db.query(SalEmpContact)
        .filter(SalEmpContact.fkEmpId == current_user.pkEmpId)
        .order_by(SalEmpContact.SrNo)
        .all()
    )
    contact_entries = [
        ContactEntry(
            contact_type_code=_resolve(db, ContMOC, "pkMOCId", "MOC", c.fkMOCId),
            contact=c.Contact,
            ext=c.Ext,
        )
        for c in contacts
    ]

    documents = (
        db.query(SalEmpDocuments)
        .filter(SalEmpDocuments.fkEmpId == current_user.pkEmpId)
        .all()
    )
    document_entries = [
        DocumentEntry(
            document_type_code=_resolve(db, DocMasRecords, "pkMDocId", "Title", d.fkDTId),
            doc_file=d.DocFile,
            valid_until=d.ValidUntil,
        )
        for d in documents
    ]

    relations = (
        db.query(SalEmpRelation)
        .filter(SalEmpRelation.fkEmpId == current_user.pkEmpId)
        .all()
    )
    family_entries = [
        RelationEntry(
            relative_name=r.RelativeName,
            relationship_code=_resolve(db, ContRelationship, "pkRelId", "Relationship", r.fkRelId),
            date_of_birth=r.DOB,
            marital_status=r.MS,
        )
        for r in relations
    ]

    return EmployeeProfileOut(
        basic=basic,
        more_info=more_info,
        contacts=contact_entries,
        documents=document_entries,
        family=family_entries,
    )