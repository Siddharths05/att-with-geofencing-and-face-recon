"""
Response models for GET /profile. Separate from schemas.py so existing
code isn't touched -- import these into main.py alongside your existing
schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class BasicInfo(BaseModel):
    emp_code: str
    name: str
    username: str
    date_of_birth: Optional[str] = None
    gender: str
    marital_status: str
    department_code: Optional[str] = None  # raw fkDepId until a Department lookup table is wired in
    designation_code: Optional[str] = None  # raw fkDegId until a Designation lookup table is wired in
    joining_date: str
    leaving_date: Optional[str] = None
    blood_group: str
    aadhar_no: str

    # --- Added to match the additional fields on the legacy Employee screen
    qualification_code: Optional[str] = None  # raw fkQualId until a Qualification lookup table is wired in
    anniversary: Optional[str] = None
    resident_address: Optional[str] = None
    native_address: Optional[str] = None
    bank_code: Optional[str] = None  # raw fkBnkId until a Bank lookup table is wired in
    account_no: Optional[str] = None
    uan_no: Optional[str] = None  # "Universal Account No. (UAN)" on screen -- PFNo column
    esic_no: Optional[str] = None
    pan_no: Optional[str] = None
    rtgs: Optional[str] = None  # RTGS/NEFT/IFSC
    short_address: Optional[str] = None
    work_place: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    cash_account_code: Optional[str] = None  # raw fkAcctId until a Cash Account lookup table is wired in
    photo_base64: Optional[str] = None  # data URI (e.g. "data:image/jpeg;base64,...") or None if no photo on file

    class Config:
        from_attributes = True


class MoreInfo(BaseModel):
    identification_mark: Optional[str] = None
    total_experience: Optional[str] = None
    referred_by_emp_id: Optional[str] = None  # raw fkREmpId (another employee's pkEmpId)
    police_station: Optional[str] = None
    police_address: Optional[str] = None
    police_contact: Optional[str] = None
    witness1_emp_id: Optional[str] = None
    witness2_emp_id: Optional[str] = None
    inform_uan_on_leaving: Optional[bool] = None
    inform_esic_on_leaving: Optional[bool] = None
    personality1_name: Optional[str] = None
    personality1_designation_code: Optional[str] = None
    personality1_address: Optional[str] = None
    personality1_contact: Optional[str] = None
    personality2_name: Optional[str] = None
    personality2_designation_code: Optional[str] = None
    personality2_address: Optional[str] = None
    personality2_contact: Optional[str] = None

    class Config:
        from_attributes = True


class ContactEntry(BaseModel):
    contact_type_code: str  # raw fkMOCId until ContMOC lookup is wired in
    contact: str
    ext: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentEntry(BaseModel):
    document_type_code: str  # raw fkDTId until DocTitle lookup is wired in
    doc_file: str
    valid_until: Optional[datetime] = None

    class Config:
        from_attributes = True


class RelationEntry(BaseModel):
    relative_name: str
    relationship_code: str  # raw fkRelId until ContRelationship lookup is wired in
    date_of_birth: Optional[datetime] = None
    marital_status: str

    class Config:
        from_attributes = True


class EmployeeProfileOut(BaseModel):
    basic: BasicInfo
    more_info: MoreInfo
    contacts: List[ContactEntry]
    documents: List[DocumentEntry]
    family: List[RelationEntry]