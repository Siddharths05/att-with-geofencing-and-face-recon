from sqlalchemy import (
    Column,
    Numeric,
    String,
    DateTime,
    Boolean,
    Integer,
    LargeBinary,
)
from database import Base


class SalEmployee(Base):
    """Maps to the existing legacy "SalEmployee" table (created outside this
    app, e.g. via pgAdmin). Only the columns this app actually uses are
    declared here -- the real table has many more columns, and SQLAlchemy is
    fine operating on a subset as long as the table already exists (we never
    run create_all against a fresh DB for this table).

    NOTE ON `nullable=False` BELOW: this app only ever reads SalEmployee, so
    SQLAlchemy never enforces these -- nullable is purely a DDL hint used
    when *creating* a table, and create_all skips this one since it already
    exists. Several columns marked nullable=False here (DOJ, Male, Married,
    BloodGrp, Aadhar, the address/statutory-ID/police/personality fields,
    etc.) are actually nullable on the real table, per the ERP backend's own
    model.py. Left as-is rather than rewritten line-by-line since it's
    cosmetic here -- but profile_schemas.py and profile_router.py were
    fixed to handle the NULLs these columns can genuinely contain, since
    those DO get enforced (by Pydantic) and would 500 otherwise."""

    __tablename__ = "SalEmployee"

    pkEmpId = Column(Numeric(18, 0), primary_key=True)
    EmpCode = Column(String(30), nullable=False)
    Employee = Column(String(50), nullable=False)  # display name

    UserName = Column(String(100), nullable=True, index=True)
    # Real column is VARCHAR(255), not (10) -- widened by the ERP admin
    # backend to hold bcrypt hashes. See auth.verify_password for how
    # this app handles both the old plaintext rows and the new hashed
    # ones living in the same column.
    Password = Column(String(255), nullable=True)

    Photo = Column(LargeBinary, nullable=True)  # BYTEA reference photo

    # --- Added for the employee-profile "Basic" tab -- confirmed real
    # columns from the actual SalEmployee DDL. fkDepId/fkDegId are lookup
    # codes (Department/Designation tables); resolved to names at call
    # time in profile_router.py.
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
    # SalEmployee DDL.
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
    """Maps to "SalStructureTest" -- the table that REPLACES the old,
    5-column "SalStructure" table this app used to read. Kept as a
    physically separate table from "SalStructure" in the ERP DB (not a
    rename at the DB level), so __tablename__ below intentionally does
    NOT match the class name -- same pattern as EmpAttendancePunch /
    "AttendancePunch" in this file. Do NOT "fix" this mismatch; if you
    do, you recreate the exact ghost-table bug described in main.py's
    top-of-file comment (SQLAlchemy will happily create a fresh, empty
    table matching whatever name you put here instead of erroring).

    If SalStructureTest is ever renamed to SalStructure at the DB level,
    or the ERP admin backend starts writing to a table under a different
    final name, update __tablename__ here to match -- and nothing else
    in this app needs to change, since every query goes through this
    class, not the raw table name.

    Full ~90-column schema mapped below since the user supplied the
    complete DDL; only pkSSId / fkEmpId / SalStart / Latitude /
    Longitude / Altitude are actually read by this app today (see
    main.py's _get_office_location()). NOT NULL / nullable below mirrors
    the real DDL for documentation purposes -- SQLAlchemy never enforces
    it since this app only ever reads this table, never inserts into it
    (see the nullable note on SalEmployee above for the same reasoning).
    """

    __tablename__ = "SalStructureTest"

    pkSSId = Column(Numeric(18, 0), primary_key=True)
    fkEmpId = Column(Numeric(18, 0), nullable=False, index=True)
    SalStart = Column(DateTime, nullable=False)
    Basic = Column(Numeric(19, 4), nullable=False)
    BType = Column(String(7), nullable=False)
    Allowance = Column(Numeric(19, 4), nullable=True)
    TAllowance = Column(String(5), nullable=False)
    Travelling = Column(Numeric(19, 4), nullable=True)
    TTravelling = Column(String(5), nullable=False)
    Housing = Column(Numeric(19, 4), nullable=True)
    THousing = Column(String(5), nullable=False)
    Daily = Column(Numeric(19, 4), nullable=True)
    TDaily = Column(String(5), nullable=False)
    Incentive = Column(Numeric(19, 4), nullable=True)
    TIncentive = Column(String(5), nullable=False)
    Education = Column(Numeric(19, 4), nullable=True)
    TEducation = Column(String(5), nullable=False)
    Medical = Column(Numeric(19, 4), nullable=True)
    TMedical = Column(String(5), nullable=False)
    Other = Column(Numeric(19, 4), nullable=True)
    TOther = Column(String(5), nullable=False)
    OTI = Column(Numeric(19, 4), nullable=True)
    TOTI = Column(Boolean, nullable=False)
    OTII = Column(Numeric(19, 4), nullable=True)
    TOTII = Column(Boolean, nullable=False)
    RDayI = Column(String(10), nullable=False)
    RDayII = Column(String(10), nullable=False)
    PH = Column(Integer, nullable=False)
    SL = Column(Numeric(10, 1), nullable=False)
    CL = Column(Numeric(10, 1), nullable=False)
    UCL = Column(Numeric(10, 1), nullable=False)
    WH = Column(Numeric(18, 2), nullable=False)
    RWH = Column(Numeric(18, 2), nullable=False)
    BL = Column(Integer, nullable=False)
    BLD = Column(Integer, nullable=False)
    ARule = Column(String(10), nullable=False)
    OTB = Column(Numeric(18, 0), nullable=False)
    CalPT = Column(Boolean, nullable=False)
    CalPF = Column(Boolean, nullable=False)
    CalESIC = Column(Boolean, nullable=False)
    CalTDS = Column(Boolean, nullable=False)
    SlabTDS = Column(Integer, nullable=True)
    Revise = Column(DateTime, nullable=False)
    ScanMB = Column(Boolean, nullable=True)
    fkSAcctId = Column(String(10), nullable=False)
    Remarks = Column(String(100), nullable=False)
    fkUserId = Column(String(5), nullable=False)
    OtherBasic = Column(Boolean, nullable=False)
    EOT = Column(Boolean, nullable=False)
    EWHour = Column(Boolean, nullable=False)
    LYEWHour = Column(Numeric(19, 2), nullable=False)
    fkLAcctId = Column(String(10), nullable=False)
    MABasic = Column(Boolean, nullable=False)
    EABasic = Column(Boolean, nullable=False)
    IncentiveBasic = Column(Boolean, nullable=False)
    DABasic = Column(Boolean, nullable=False)
    HABasic = Column(Boolean, nullable=False)
    TABasic = Column(Boolean, nullable=False)
    AllowanceBasic = Column(Boolean, nullable=False)
    fkFContId = Column(String(10), nullable=True)
    fkTContId = Column(String(10), nullable=True)
    SalGross = Column(Numeric(19, 4), nullable=False)
    fkIAcctId = Column(String(10), nullable=True)
    AbPenalty = Column(Numeric(19, 4), nullable=False)
    Variant = Column(Boolean, nullable=False)
    PFA = Column(Boolean, nullable=False)
    PFTA = Column(Boolean, nullable=False)
    PFHA = Column(Boolean, nullable=False)
    PFI = Column(Boolean, nullable=False)
    PFEA = Column(Boolean, nullable=False)
    PFMA = Column(Boolean, nullable=False)
    PFOA = Column(Boolean, nullable=False)
    RDVariant = Column(Boolean, nullable=False)
    Retention = Column(Numeric(19, 4), nullable=True)
    fkEmp1Id = Column(Numeric(18, 0), nullable=True)
    fkEmp2Id = Column(Numeric(18, 0), nullable=True)
    fkRAcctId = Column(String(10), nullable=True)
    SalDaily = Column(Numeric(19, 4), nullable=True)
    SetPF = Column(Boolean, nullable=False)
    Sandwich = Column(Boolean, nullable=False)
    GHA = Column(Boolean, nullable=False)
    RDA = Column(Boolean, nullable=False)
    IORF = Column(Boolean, nullable=False)
    OAOP = Column(Boolean, nullable=False)
    LTimeROff = Column(Integer, nullable=True)
    # --- The three columns this app actually queries directly ---
    Latitude = Column(Numeric(18, 6), nullable=True)
    Longitude = Column(Numeric(18, 6), nullable=True)
    Altitude = Column(Numeric(18, 6), nullable=True)
    TDSDeduct = Column(Numeric(18, 0), nullable=True)
    MDeduction = Column(Numeric(18, 2), nullable=True)
    DedDescription = Column(String(100), nullable=True)
    fkDesId = Column(String(5), nullable=True)


class EmpAttendancePunch(Base):
    """Replaces the old local `attendance` table. This is the real ERP
    punch table (same shape as EmpAttendance, minus EmpName/Status/Manual
    which this app doesn't need, plus Altitude which the old table never
    had). One row per employee per day, keyed by (EmpCode, AtDate) --
    check-in fills PunchInTime; PunchOutTime stays NULL until a
    check-out flow exists (see main.py).

    NOTE: the physical table is named "AttendancePunch" (no "Emp" prefix)
    -- the class is named EmpAttendancePunch here only to avoid clashing
    with anything else, __tablename__ is what actually matters and must
    stay pointed at the real table.

    AtDate is stored as 'YYYY-MM-DD' so plain string ordering/filtering
    works -- if the ERP admin backend writes a different date format into
    this same physical table, switch AtDate comparisons in main.py to
    parse accordingly.
    """

    __tablename__ = "AttendancePunch"

    pkEAId = Column(Numeric(18, 0), primary_key=True, autoincrement=True)
    EmpCode = Column(String(30), nullable=False, index=True)
    PayCode = Column(String(50), nullable=False)
    AtDate = Column(String(50), nullable=False, index=True)  # 'YYYY-MM-DD'
    PunchInTime = Column(String(8), nullable=True)   # 'HH:MM:SS'
    PunchOutTime = Column(String(8), nullable=True)  # 'HH:MM:SS'
    Device = Column(String(100), nullable=True)
    Latitude = Column(Numeric(18, 6), nullable=True)
    Longitude = Column(Numeric(18, 6), nullable=True)
    Altitude = Column(Numeric(18, 6), nullable=True)

    # Not physical DB columns -- populated in main.py before returning a
    # response, since face-match results were never part of this table
    # and have nowhere else to live right now. See main.py's TODO there
    # if you want these persisted (e.g. a small side table keyed by
    # pkEAId) rather than recomputed/discarded per request.