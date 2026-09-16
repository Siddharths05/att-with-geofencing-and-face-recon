import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# ==================================================
# DATABASE CONNECTION
# Was Postgres against a throwaway "attendance_app" DB during
# development. Switched to the real SQL Server IERPSystem DB --
# same instance the ERP admin backend already talks to -- so this
# app reads the live SalEmployee / SalStructure tables instead of
# an empty local copy.
#
# Named instance ("ACER\AAASOLUTIONS") goes in the host segment,
# NOT combined with an explicit port -- SQL Server resolves the
# instance's port itself via the SQL Browser service. Mirrors the
# ERP backend's database.py exactly, so if that one connects, this
# one will too with the same .env values.
# ==================================================

DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_INSTANCE = os.getenv("DATABASE_INSTANCE", "")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_PORT = os.getenv("DATABASE_PORT", "1433")

# Must match an ODBC driver actually installed on this machine --
# check with `odbcinst -j` on Linux/Mac or the "ODBC Data Sources"
# app on Windows.
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

_missing = [
    name
    for name, value in {
        "DATABASE_USER": DATABASE_USER,
        "DATABASE_PASSWORD": DATABASE_PASSWORD,
        "DATABASE_HOST": DATABASE_HOST,
        "DATABASE_NAME": DATABASE_NAME,
    }.items()
    if not value
]
if _missing:
    raise RuntimeError(
        "Missing database environment variables: " + ", ".join(_missing)
    )

host = f"{DATABASE_HOST}\\{DATABASE_INSTANCE}" if DATABASE_INSTANCE else DATABASE_HOST

DATABASE_URL = URL.create(
    drivername="mssql+pyodbc",
    username=DATABASE_USER,
    password=DATABASE_PASSWORD,
    host=host,
    port=None if DATABASE_INSTANCE else int(DATABASE_PORT),
    database=DATABASE_NAME,
    query={
        "driver": ODBC_DRIVER,
        # Self-signed/local dev cert -- same tradeoff the ERP
        # backend makes, drop once on a trusted cert or driver 17.
        "TrustServerCertificate": "yes",
    },
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Storage for uploaded reference/check-in photos and the cropped grayscale
# face used internally for face matching. Created next to this file.
PHOTOS_DIR = BASE_DIR / "photos"
FACES_DIR = BASE_DIR / "faces_ref"
PHOTOS_DIR.mkdir(exist_ok=True)
FACES_DIR.mkdir(exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()