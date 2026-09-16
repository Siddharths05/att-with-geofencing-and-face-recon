from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    LargeBinary,
)
from sqlalchemy.sql import func
from database import Base


class SalEmployee(Base):
    """Maps to the existing legacy "SalEmployee" table (created outside this
    app, e.g. via pgAdmin). Only the columns this app actually uses are
    declared here -- the real table has many more columns, and SQLAlchemy is
    fine operating on a subset as long as the table already exists (we never
    run create_all against a fresh DB for this table)."""

    __tablename__ = "SalEmployee"

    pkEmpId = Column(Numeric(18, 0), primary_key=True)
    EmpCode = Column(String(30), nullable=False)
    Employee = Column(String(50), nullable=False)  # display name

    UserName = Column(String(15), nullable=False, unique=True, index=True)
    # NOTE: legacy column is VARCHAR(10) -- too short to hold a bcrypt hash,
    # so this is almost certainly stored as plaintext today. auth.py compares
    # it directly rather than hashing. Flagging as a security gap to revisit.
    Password = Column(String(10), nullable=False)

    Photo = Column(LargeBinary, nullable=True)  # BYTEA reference photo

    # --- Added for the employee-profile "Basic" tab -- confirmed real
    # columns from the actual SalEmployee DDL. fkDepId/fkDegId are lookup
    # codes (Department/Designation tables); no lookup table structure was
    # provided yet, so profile_router.py returns the raw code for now.
    DOB = Column(DateTime, nullable=True)
    DOJ = Column(DateTime, nullable=False)
    DOL = Column(DateTime, nullable=True)  # date of leaving
    Male = Column(Boolean, nullable=False)  # True = Male, False = Female
    Married = Column(Boolean, nullable=False)
    BloodGrp = Column(String(6), nullable=False)
    Aadhar = Column(String(50), nullable=False)
    fkDepId = Column(String(5), nullable=True)  # department lookup code
    fkDegId = Column(String(5), nullable=True)  # designation lookup code

    # --- Added for the fuller "Basic" tab, matching fields visible on the
    # legacy desktop Employee screen. All confirmed real columns from the
    # SalEmployee DDL; lookup codes (fkQualId) are returned raw same as
    # fkDepId/fkDegId until a lookup table is wired in.
    fkQualId = Column(String(5), nullable=True)  # qualification lookup code
    Anni = Column(DateTime, nullable=True)  # anniversary
    PAddress = Column(String(255), nullable=False)  # "Resident Address" on screen
    NAddress = Column(String(255), nullable=False)  # "Native Address" on screen
    fkBnkId = Column(String(10), nullable=True)  # bank lookup code
    AccountNo = Column(String(20), nullable=False)
    PFNo = Column(String(25), nullable=False)  # shown as "Universal Account No. (UAN)" on screen
    ESICNo = Column(String(25), nullable=False)
    PANNo = Column(String(25), nullable=False)
    RTGS = Column(String(20), nullable=False)  # RTGS/NEFT/IFSC
    SAddress = Column(String(30), nullable=False)  # "Short Address" on screen
    WP = Column(String(50), nullable=False)  # "Work Place" on screen
    Height = Column(Numeric(18, 0), nullable=True)
    Weight = Column(Numeric(18, 2), nullable=True)
    fkAcctId = Column(String(10), nullable=True)  # "Cash Account" lookup code

    # --- Added for the "More info" tab (identification/police/witness/
    # personality-reference fields from the legacy "leaving" screen).
    # Login credentials (UserName/Password/Question/Answer) already exist
    # above and are intentionally NOT re-exposed on the profile response.
    Mark = Column(String(50), nullable=False)  # "Identification Mark" on screen
    Experience = Column(String(5), nullable=True)  # "Total Experience"
    fkREmpId = Column(Numeric(18, 0), nullable=True)  # "Referred By" -- another employee
    Police = Column(String(50), nullable=False)  # "Police Station"
    AddPolice = Column(String(255), nullable=False)  # police station address
    ContPolice = Column(String(25), nullable=False)  # police station contact no.
    fkW1EmpId = Column(Numeric(18, 0), nullable=True)  # "1) Witness"
    fkW2EmpId = Column(Numeric(18, 0), nullable=True)  # "2) Witness"
    InformPF = Column(Boolean, nullable=True)  # "Inform UAN about leaving"
    InformESIC = Column(Boolean, nullable=True)  # "Inform ESIC about leaving"
    Personality1 = Column(String(50), nullable=False)
    fkP1DesId = Column(String(5), nullable=True)
    P1Address = Column(String(255), nullable=False)
    P1Contact = Column(String(25), nullable=False)
    Personality2 = Column(String(50), nullable=False)
    fkP2DesId = Column(String(5), nullable=True)
    P2Address = Column(String(255), nullable=False)
    P2Contact = Column(String(25), nullable=False)


class SalStructure(Base):
    """Maps to the existing legacy "SalStructure" table. Only the columns
    needed for the check-in location lookup are declared."""

    __tablename__ = "SalStructure"

    pkSSId = Column(Numeric(18, 0), primary_key=True)
    fkEmpId = Column(Numeric(18, 0), ForeignKey("SalEmployee.pkEmpId"), index=True)
    SalStart = Column(DateTime, nullable=True)
    Latitude = Column(Numeric(18, 6), nullable=True)
    Longitude = Column(Numeric(18, 6), nullable=True)


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    # Keyed off SalEmployee.pkEmpId, but the JWT/session identifies users by
    # username, so we also store it denormalized for convenient querying.
    emp_id = Column(Numeric(18, 0), ForeignKey("SalEmployee.pkEmpId", ondelete="CASCADE"))
    username = Column(String(15), nullable=False, index=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    distance_meters = Column(Float)
    face_match = Column(Boolean, nullable=True)
    face_similarity_percent = Column(Float, nullable=True)
    status = Column(String(20), nullable=False)  # 'present' or 'rejected'
    checked_in_at = Column(DateTime(timezone=True), server_default=func.now())