import logging
from math import radians, cos, sin, asin, sqrt
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("face_match")

import auth
import models
import schemas
from database import Base, engine, get_db, FACES_DIR
from face_utils import extract_face, save_face_ref, load_face_ref, compare_faces, NoFaceFoundError
from profile_router import router as profile_router

Base.metadata.create_all(bind=engine)  # only affects the "attendance" table --
# SalEmployee / SalStructure already exist in the legacy DB and are left alone.

app = FastAPI(title="Attendance App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local testing only
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_router)

ALLOWED_RADIUS_METERS = 50

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two lat/long points, in meters."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Earth's radius in meters
    return c * r


def _get_reference_face(employee: models.SalEmployee):
    """Return the employee's reference face crop, extracted from
    SalEmployee.Photo (BYTEA). Cached to disk keyed by username so we don't
    re-run face detection on every request.
    NOTE: if an employee's Photo is updated in the HR system, this cache goes
    stale until the cache file is deleted -- swap for a proper invalidation
    strategy (e.g. hash the photo bytes) if that turns out to matter."""
    if not employee.Photo:
        return None

    cache_path = FACES_DIR / f"{employee.UserName}.png"
    if cache_path.exists():
        return load_face_ref(str(cache_path))

    face = extract_face(bytes(employee.Photo))
    save_face_ref(face, str(cache_path))
    return face


def _get_office_location(db: Session, employee: models.SalEmployee):
    """Most recent SalStructure row for this employee that has a lat/long
    set. Returns (lat, lon) or None if the employee has no site assigned."""
    structure = (
        db.query(models.SalStructure)
        .filter(
            models.SalStructure.fkEmpId == employee.pkEmpId,
            models.SalStructure.Latitude.isnot(None),
            models.SalStructure.Longitude.isnot(None),
        )
        .order_by(models.SalStructure.SalStart.desc())
        .first()
    )
    if structure is None:
        return None
    return float(structure.Latitude), float(structure.Longitude)


@app.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    employee = (
        db.query(models.SalEmployee)
        .filter(models.SalEmployee.UserName == credentials.username)
        .first()
    )
    if not employee or not auth.verify_password(credentials.password, employee.Password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = auth.create_access_token({"sub": employee.UserName})
    return {"access_token": token}


@app.post("/attendance/check-location", response_model=schemas.LocationCheckOut)
def check_location(
    latitude: float = Form(...),
    longitude: float = Form(...),
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Pre-check called before the camera opens. Tells the app which checks
    actually apply to this employee -- location is only enforced if they
    have a SalStructure row with lat/long set, and face matching is only
    enforced if they have a reference Photo on file. Missing data = that
    check is SKIPPED, not failed. Does NOT create an attendance record."""
    office_location = _get_office_location(db, current_user)
    location_required = office_location is not None
    photo_required = _get_reference_face(current_user) is not None

    if not location_required:
        return {
            "location_required": False,
            "photo_required": photo_required,
            "within_range": True,
            "distance_meters": None,
            "allowed_radius_meters": ALLOWED_RADIUS_METERS,
        }

    office_lat, office_lon = office_location
    distance = haversine(latitude, longitude, office_lat, office_lon)
    within_range = distance <= ALLOWED_RADIUS_METERS
    return {
        "location_required": True,
        "photo_required": photo_required,
        "within_range": within_range,
        "distance_meters": distance,
        "allowed_radius_meters": ALLOWED_RADIUS_METERS,
    }


@app.post("/face/live-check", response_model=schemas.FaceCheckOut)
def live_face_check(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Lightweight endpoint polled repeatedly by the app while the camera is
    open, so the UI can show a live 'no face / detecting / matched' state
    before the real check-in photo is submitted. Does NOT create an
    attendance record."""
    reference_face = _get_reference_face(current_user)
    if reference_face is None:
        raise HTTPException(
            status_code=400,
            detail="No reference photo on file for your account. Contact HR to add a photo before checking in.",
        )

    image_bytes = photo.file.read()
    try:
        current_face = extract_face(image_bytes)
    except NoFaceFoundError:
        return {"face_detected": False, "is_match": False, "similarity_percent": 0.0}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    is_match, confidence, similarity_pct = compare_faces(reference_face, current_face)
    logger.info(
        "live-check user=%s is_match=%s confidence=%.2f similarity=%.1f%%",
        current_user.UserName, is_match, confidence, similarity_pct,
    )
    return {
        "face_detected": True,
        "is_match": is_match,
        "similarity_percent": similarity_pct,
    }


@app.post("/attendance/check-in", response_model=schemas.AttendanceOut)
def check_in(
    latitude: float = Form(...),
    longitude: float = Form(...),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Checks location and/or face match, but ONLY for whichever ones this
    employee actually has data for:
      - no SalStructure lat/long on file  -> location check SKIPPED
      - no reference Photo on file        -> face check SKIPPED
      - neither on file                   -> check-in auto-succeeds
    This is a deliberate tradeoff: an employee missing setup data is fully
    unverifiable rather than blocked. Every attempt is still saved to
    `attendance` for audit regardless of outcome."""
    office_location = _get_office_location(db, current_user)
    location_required = office_location is not None

    reference_face = _get_reference_face(current_user)
    photo_required = reference_face is not None

    distance = None
    within_range = True
    if location_required:
        office_lat, office_lon = office_location
        distance = haversine(latitude, longitude, office_lat, office_lon)
        within_range = distance <= ALLOWED_RADIUS_METERS

        if not within_range:
            # Short-circuit: don't bother with face detection if they're not
            # even at the right location.
            logger.info(
                "check-in user=%s REJECTED (out of range) distance=%.1fm",
                current_user.UserName, distance,
            )
            record = models.Attendance(
                emp_id=current_user.pkEmpId,
                username=current_user.UserName,
                latitude=latitude,
                longitude=longitude,
                distance_meters=distance,
                face_match=None,
                face_similarity_percent=None,
                status="rejected",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            raise HTTPException(
                status_code=403,
                detail=f"Check-in rejected: you are {distance:.1f}m from your assigned site (must be within {ALLOWED_RADIUS_METERS}m).",
            )

    is_match = True
    similarity_pct = None
    if photo_required:
        if photo is None:
            raise HTTPException(
                status_code=400,
                detail="A live photo is required for your account (reference photo on file).",
            )
        image_bytes = photo.file.read()
        try:
            current_face = extract_face(image_bytes)
        except NoFaceFoundError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        is_match, confidence, similarity_pct = compare_faces(reference_face, current_face)
        logger.info(
            "check-in user=%s is_match=%s confidence=%.2f similarity=%.1f%% location_required=%s within_range=%s",
            current_user.UserName, is_match, confidence, similarity_pct, location_required, within_range,
        )
    else:
        logger.info(
            "check-in user=%s NO PHOTO ON FILE -- face check skipped location_required=%s within_range=%s",
            current_user.UserName, location_required, within_range,
        )

    status_str = "present" if is_match else "rejected"

    record = models.Attendance(
        emp_id=current_user.pkEmpId,
        username=current_user.UserName,
        latitude=latitude,
        longitude=longitude,
        distance_meters=distance,
        face_match=(is_match if photo_required else None),
        face_similarity_percent=similarity_pct,
        status=status_str,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "attendance id=%s user=%s status=%s at=%s",
        record.id, current_user.UserName, status_str, record.checked_in_at,
    )

    if status_str == "rejected":
        raise HTTPException(
            status_code=403,
            detail=f"Check-in rejected: face did not match your reference photo ({similarity_pct}% similarity).",
        )

    return record


@app.get("/attendance/history", response_model=list[schemas.AttendanceOut])
def history(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    return (
        db.query(models.Attendance)
        .filter(models.Attendance.username == current_user.UserName)
        .order_by(models.Attendance.checked_in_at.desc())
        .all()
    )