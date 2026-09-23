import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# ==================================================
# POSTGRESQL DATABASE CONNECTION
# Local development currently uses PostgreSQL 15.4
# database: attendance_app
#
# For Render later, set the same PG_* variables there
# using Render's PostgreSQL connection details.
# ==================================================

PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "attendance_app")

_missing = [
    name
    for name, value in {
        "PG_USER": PG_USER,
        "PG_PASSWORD": PG_PASSWORD,
        "PG_HOST": PG_HOST,
        "PG_DATABASE": PG_DATABASE,
    }.items()
    if not value
]

if _missing:
    raise RuntimeError(
        "Missing PostgreSQL environment variables: "
        + ", ".join(_missing)
    )

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=PG_USER,
    password=PG_PASSWORD,
    host=PG_HOST,
    port=int(PG_PORT),
    database=PG_DATABASE,
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# Storage for uploaded reference/check-in photos and the cropped
# grayscale face used internally for face matching.
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
