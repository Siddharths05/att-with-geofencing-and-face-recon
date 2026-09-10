import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Format: postgresql://<user>:<password>@<host>:<port>/<database_name>
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:yourpassword@localhost:5432/attendance_app",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Storage for uploaded reference/check-in photos and the cropped grayscale
# face used internally for face matching. Created next to this file.
BASE_DIR = Path(__file__).parent
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