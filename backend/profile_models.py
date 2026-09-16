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
from sqlalchemy import Column, Numeric, String, DateTime, BigInteger
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
