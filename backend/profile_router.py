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
from profile_models import SalEmpContact, SalEmpDocuments, SalEmpRelation
from profile_schemas import (
    EmployeeProfileOut,
    BasicInfo,
    MoreInfo,
    ContactEntry,
    DocumentEntry,
    RelationEntry,
)

router = APIRouter()


@router.get("/profile", response_model=EmployeeProfileOut)
def get_profile(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Returns the logged-in employee's own profile, categorized into
    basic info / contacts / documents / family. Only queries tables that
    are confirmed to exist with known columns -- basic info fields beyond
    EmpCode/Employee/UserName are placeholders until the real SalEmployee
    schema is confirmed (see profile_schemas.py)."""

    basic = BasicInfo(
        emp_code=current_user.EmpCode,
        name=current_user.Employee,
        username=current_user.UserName,
        date_of_birth=current_user.DOB.date().isoformat() if current_user.DOB else None,
        gender="Male" if current_user.Male else "Female",
        marital_status="Married" if current_user.Married else "Unmarried",
        department_code=current_user.fkDepId,
        designation_code=current_user.fkDegId,
        joining_date=current_user.DOJ.date().isoformat(),
        leaving_date=current_user.DOL.date().isoformat() if current_user.DOL else None,
        blood_group=current_user.BloodGrp,
        aadhar_no=current_user.Aadhar,
        qualification_code=current_user.fkQualId,
        anniversary=current_user.Anni.date().isoformat() if current_user.Anni else None,
        resident_address=current_user.PAddress,
        native_address=current_user.NAddress,
        bank_code=current_user.fkBnkId,
        account_no=current_user.AccountNo,
        uan_no=current_user.PFNo,
        esic_no=current_user.ESICNo,
        pan_no=current_user.PANNo,
        rtgs=current_user.RTGS,
        short_address=current_user.SAddress,
        work_place=current_user.WP,
        height=str(current_user.Height) if current_user.Height is not None else None,
        weight=str(current_user.Weight) if current_user.Weight is not None else None,
        cash_account_code=current_user.fkAcctId,
        photo_base64=_photo_to_data_uri(current_user.Photo),
    )

    more_info = MoreInfo(
        identification_mark=current_user.Mark,
        total_experience=current_user.Experience,
        referred_by_emp_id=str(current_user.fkREmpId) if current_user.fkREmpId is not None else None,
        police_station=current_user.Police,
        police_address=current_user.AddPolice,
        police_contact=current_user.ContPolice,
        witness1_emp_id=str(current_user.fkW1EmpId) if current_user.fkW1EmpId is not None else None,
        witness2_emp_id=str(current_user.fkW2EmpId) if current_user.fkW2EmpId is not None else None,
        inform_uan_on_leaving=current_user.InformPF,
        inform_esic_on_leaving=current_user.InformESIC,
        personality1_name=current_user.Personality1,
        personality1_designation_code=current_user.fkP1DesId,
        personality1_address=current_user.P1Address,
        personality1_contact=current_user.P1Contact,
        personality2_name=current_user.Personality2,
        personality2_designation_code=current_user.fkP2DesId,
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
        ContactEntry(contact_type_code=c.fkMOCId, contact=c.Contact, ext=c.Ext)
        for c in contacts
    ]

    documents = (
        db.query(SalEmpDocuments)
        .filter(SalEmpDocuments.fkEmpId == current_user.pkEmpId)
        .all()
    )
    document_entries = [
        DocumentEntry(
            document_type_code=str(d.fkDTId),
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
            relationship_code=r.fkRelId,
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