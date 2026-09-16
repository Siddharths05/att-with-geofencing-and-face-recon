"""
Models for the employee-profile feature. Kept separate from models.py so
existing code isn't touched -- import these into main.py alongside your
existing models.

Only maps the columns declared in the DDL you shared. Lookup tables
(ContMOC, DocTitle, ContRelationship, ContQualification, ContCommon)
aren't mapped here since their own column structures weren't provided --
the router below returns the raw lookup codes (e.g. fkMOCId) rather than
resolved labels until those are added.
"""
from sqlalchemy import Column, Numeric, String, DateTime, BigInteger, Integer
from database import Base


class SalEmpContact(Base):
    __tablename__ = "SalEmpContact"

    pkContId = Column(BigInteger, primary_key=True)
    fkEmpId = Column(Numeric(18, 0), nullable=False, index=True)
    fkMOCId = Column(String(5), nullable=False)  # mode of contact lookup code
    Contact = Column(String(50), nullable=False)
    Ext = Column(String(10), nullable=False)
    SrNo = Column(Numeric(18, 0), nullable=False)


class SalEmpDocuments(Base):
    __tablename__ = "SalEmpDocuments"

    pkDEmpId = Column(BigInteger, primary_key=True)
    fkEmpId = Column(Numeric(18, 0), nullable=False, index=True)
    fkDTId = Column(Numeric(18, 0), nullable=False)  # document type lookup code
    DocFile = Column(String(100), nullable=False)
    ValidUntil = Column(DateTime, nullable=True)


class SalEmpRelation(Base):
    __tablename__ = "SalEmpRelation"

    pkMRelId = Column(BigInteger, primary_key=True)
    fkEmpId = Column(Numeric(18, 0), nullable=False, index=True)
    RelativeName = Column(String(50), nullable=False)
    fkRelId = Column(String(5), nullable=False)   # relationship lookup code
    DOB = Column(DateTime, nullable=True)
    fkQuaId = Column(String(5), nullable=True)     # qualification lookup code
    fkSchId = Column(String(10), nullable=True)    # school/college lookup code
    MS = Column(String(15), nullable=False)        # marital status, free text per DDL
    fkDesId = Column(String(5), nullable=True)      # occupation/designation lookup code


# ==================================================
# LOOKUP / MASTER TABLES
# Same physical tables the ERP admin backend already reads/writes
# (see that project's model.py -- ContTitle, ContQualification,
# ContRelationship, ContDepartment, ContDesignation, ContMOC,
# ContCommon, AcctAccount, DocMasRecords, etc). Declared read-only
# here -- pk + label column only, nothing else this app needs.
# Values are resolved at request time in profile_router.py rather
# than stored/cached, so any change made in the ERP admin panel
# shows up immediately here on the next /profile call.
# ==================================================

class ContDepartment(Base):
    __tablename__ = "ContDepartment"

    pkDepId = Column(String(5), primary_key=True)
    Department = Column(String(60), nullable=False)


class ContDesignation(Base):
    __tablename__ = "ContDesignation"

    pkDesId = Column(String(5), primary_key=True)
    Designation = Column(String(60), nullable=False)


class ContQualification(Base):
    __tablename__ = "ContQualification"

    pkQuaId = Column(String(5), primary_key=True)
    Qualification = Column(String(80), nullable=False)


class ContRelationship(Base):
    __tablename__ = "ContRelationship"

    pkRelId = Column(String(5), primary_key=True)
    Relationship = Column(String(50), nullable=False)


class ContMOC(Base):
    __tablename__ = "ContMOC"

    pkMOCId = Column(String(5), primary_key=True)
    MOC = Column(String(50), nullable=False)


class ContCommon(Base):
    """"Bank Name" lookup -- same generic contacts table the ERP backend
    calls "banks". Only pk + label mapped; the real table has several
    other NOT NULL columns this app never touches."""
    __tablename__ = "ContCommon"

    pkContId = Column(String(10), primary_key=True)
    ContactName = Column(String(100), nullable=False)


class AcctAccount(Base):
    __tablename__ = "AcctAccount"

    pkAcctId = Column(String(10), primary_key=True)
    Account = Column(String(100), nullable=False)


class DocMasRecords(Base):
    """Document-type lookup for SalEmpDocuments.fkDTId ("Medical Document
    Ref." master in the ERP backend). pkMDocId is a numeric IDENTITY
    column there, matching the Numeric(18,0) fkDTId on SalEmpDocuments."""
    __tablename__ = "DocMasRecords"

    pkMDocId = Column(Integer, primary_key=True)
    Title = Column(String(100), nullable=False)