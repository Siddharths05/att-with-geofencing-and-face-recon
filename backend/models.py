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