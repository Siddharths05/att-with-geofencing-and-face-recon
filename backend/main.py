import logging
from datetime import date, datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, File, Form, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("face_match")

import auth
import models
import schemas
from database import get_db, FACES_DIR
from face_utils import extract_face, save_face_ref, load_face_ref, compare_faces, NoFaceFoundError
from profile_router import router as profile_router
from loan_router import router as loan_router
from leave_router import router as leave_router
# NOTE: create_all() intentionally removed. Every table this app touches
# (SalEmployee, SalStructure, AttendancePunch) already exists in the live
# ERP database and is owned by that system, not this app. Previously,
# a __tablename__ that didn't exactly match the real table
# ("EmpAttendancePunch" vs the real "AttendancePunch") caused create_all
# to silently create a brand-new, empty ghost table matching the ORM
# model instead of erroring -- the app then happily read/wrote to that
# ghost table while the real one stayed empty, with no error anywhere.
# If you ever add a table this app DOES own, create it with an explicit
# migration (Alembic) instead of create_all, so a typo'd tablename fails
# loudly (relation does not exist) instead of quietly fabricating a table.

app = FastAPI(title="Attendance App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local testing only
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_router)
app.include_router(loan_router)
app.include_router(leave_router)

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


def _today_str() -> str:
    """'YYYY-MM-DD', matching EmpAttendancePunch.AtDate's stored format.
    Uses the app server's local date -- if the app server and your
    employees aren't in the same timezone, this needs to become an
    explicit tz-aware conversion instead."""
    return date.today().isoformat()


def _now_time_str() -> str:
    """'HH:MM:SS', matching PunchInTime/PunchOutTime's format/width."""
    return datetime.now().strftime("%H:%M:%S")


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
    set. Returns (lat, lon) or None if the employee has no site assigned.

    NOTE: SalStructureTest (the table this now reads -- see models.py)
    also has an Altitude column, but nothing here reads it yet. Altitude
    checking was deliberately deferred, not forgotten -- see the comment
    on Altitude in models.py's SalStructure class if/when that gets
    picked back up."""
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


def _get_today_punch(db: Session, employee: models.SalEmployee):
    """The employee's EmpAttendancePunch row for today, if any -- one row
    per (EmpCode, AtDate). This is also what prevents duplicate check-ins:
    a row already existing with PunchInTime set means they're done for
    the day."""
    return (
        db.query(models.EmpAttendancePunch)
        .filter(
            models.EmpAttendancePunch.EmpCode == employee.EmpCode,
            models.EmpAttendancePunch.AtDate == _today_str(),
        )
        .first()
    )


def _record_to_out(record: models.EmpAttendancePunch, status_str: str,
                    is_match: Optional[bool] = None,
                    similarity_pct: Optional[float] = None) -> schemas.AttendanceOut:
    """EmpAttendancePunch has no Status/face-match columns (removed / never
    existed on the physical table), so build the response explicitly
    rather than relying on response_model's automatic from_attributes
    conversion -- status and face-match fields only ever reflect the
    current request, never a stored value."""
    return schemas.AttendanceOut(
        pkEAId=int(record.pkEAId),
        emp_code=record.EmpCode,
        pay_code=record.PayCode,
        at_date=record.AtDate,
        punch_in_time=record.PunchInTime,
        punch_out_time=record.PunchOutTime,
        device=record.Device,
        latitude=float(record.Latitude) if record.Latitude is not None else None,
        longitude=float(record.Longitude) if record.Longitude is not None else None,
        altitude=float(record.Altitude) if record.Altitude is not None else None,
        status=status_str,
        face_match=is_match,
        face_similarity_percent=similarity_pct,
    )


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


@app.get("/attendance/today", response_model=Optional[schemas.AttendanceOut])
def today_status(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Lets the frontend know, on login/screen load, whether this employee
    has already checked in and/or out today -- without this, the app has
    no way to tell and always renders the check-in UI regardless of
    actual state (which is exactly the bug where check-in returns 409
    but the button stays a check-in button). Returns null if there's no
    row for today yet."""
    record = _get_today_punch(db, current_user)
    if record is None:
        return None
    return _record_to_out(record, "present")


@app.post("/attendance/check-in", response_model=schemas.AttendanceOut)
def check_in(
    request: Request,
    latitude: float = Form(...),
    longitude: float = Form(...),
    altitude: Optional[float] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Writes to EmpAttendancePunch (the real ERP punch table) instead of
    the old local `attendance` table. One row per (EmpCode, AtDate):

      - a row already existing for today with PunchInTime set -> 409,
        check-in refused (this is what stops the old duplicate-checkin
        bug -- previously every call just inserted a new row)
      - no SalStructure lat/long on file  -> location check SKIPPED
      - no reference Photo on file        -> face check SKIPPED
      - neither on file                   -> check-in auto-succeeds

    NOTE ON REJECTED ATTEMPTS: the old table had a `status` column and
    saved a "rejected" row for every failed attempt, for audit purposes.
    EmpAttendancePunch has no such column (it was dropped along with
    EmpName/Manual per the new schema), so a rejected attempt now writes
    NOTHING -- there's no audit trail of failed check-ins anymore. Flag
    if you need that back; it'd need either a side table or restoring a
    status-like column here.
    """
    existing = _get_today_punch(db, current_user)
    if existing and existing.PunchInTime:
        raise HTTPException(
            status_code=409,
            detail=f"Already checked in today at {existing.PunchInTime}.",
        )

    office_location = _get_office_location(db, current_user)
    location_required = office_location is not None

    reference_face = _get_reference_face(current_user)
    photo_required = reference_face is not None

    distance = None
    if location_required:
        office_lat, office_lon = office_location
        distance = haversine(latitude, longitude, office_lat, office_lon)
        within_range = distance <= ALLOWED_RADIUS_METERS

        if not within_range:
            logger.info(
                "check-in user=%s REJECTED (out of range) distance=%.1fm",
                current_user.UserName, distance,
            )
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
            "check-in user=%s is_match=%s confidence=%.2f similarity=%.1f%% location_required=%s",
            current_user.UserName, is_match, confidence, similarity_pct, location_required,
        )
        if not is_match:
            raise HTTPException(
                status_code=403,
                detail=f"Check-in rejected: face did not match your reference photo ({similarity_pct}% similarity).",
            )
    else:
        logger.info(
            "check-in user=%s NO PHOTO ON FILE -- face check skipped location_required=%s",
            current_user.UserName, location_required,
        )

    device = request.headers.get("user-agent", "unknown")

    if existing:
        # Row for today exists but PunchInTime was never set (shouldn't
        # normally happen given the check above, but covers a row created
        # by some other future flow) -- fill it in rather than inserting.
        record = existing
    else:
        record = models.EmpAttendancePunch(
            EmpCode=current_user.EmpCode,
            PayCode=current_user.EmpCode,  # TODO: swap for the real pay-code
            # source/column once that's confirmed -- EmpCode is a
            # placeholder so this doesn't 500 on a NOT NULL column.
            AtDate=_today_str(),
        )
        db.add(record)

    record.PunchInTime = _now_time_str()
    record.Device = device
    record.Latitude = latitude
    record.Longitude = longitude
    record.Altitude = altitude
    db.commit()
    db.refresh(record)

    logger.info(
        "attendance id=%s user=%s status=present at=%s",
        record.pkEAId, current_user.UserName, record.PunchInTime,
    )

    return _record_to_out(record, "present", is_match=is_match if photo_required else None,
                           similarity_pct=similarity_pct)


@app.post("/attendance/check-out", response_model=schemas.AttendanceOut)
def check_out(
    latitude: float = Form(...),
    longitude: float = Form(...),
    altitude: Optional[float] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Same verification as check_in() -- location required only if the
    employee has a SalStructure site assigned, face match required only
    if they have a reference Photo on file -- but fills PunchOutTime on
    today's existing row instead of inserting a new one.

    NOTE: latitude/longitude/altitude here are used ONLY to verify the
    employee is where they should be at punch-out time -- they are NOT
    written to the record. AttendancePunch has a single Latitude/
    Longitude/Altitude/Device set of columns, already holding the
    check-in location; overwriting them here would destroy that and
    there's nowhere else to put the punch-out location. If you need
    punch-out location on record, this needs OutLatitude/OutLongitude/
    OutAltitude/OutDevice columns added to the table first.
    """
    existing = _get_today_punch(db, current_user)
    if not existing or not existing.PunchInTime:
        raise HTTPException(
            status_code=400,
            detail="You haven't checked in today -- check in before checking out.",
        )
    if existing.PunchOutTime:
        raise HTTPException(
            status_code=409,
            detail=f"Already checked out today at {existing.PunchOutTime}.",
        )

    office_location = _get_office_location(db, current_user)
    location_required = office_location is not None

    reference_face = _get_reference_face(current_user)
    photo_required = reference_face is not None

    if location_required:
        office_lat, office_lon = office_location
        distance = haversine(latitude, longitude, office_lat, office_lon)
        within_range = distance <= ALLOWED_RADIUS_METERS

        if not within_range:
            logger.info(
                "check-out user=%s REJECTED (out of range) distance=%.1fm",
                current_user.UserName, distance,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Check-out rejected: you are {distance:.1f}m from your assigned site (must be within {ALLOWED_RADIUS_METERS}m).",
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
            "check-out user=%s is_match=%s confidence=%.2f similarity=%.1f%% location_required=%s",
            current_user.UserName, is_match, confidence, similarity_pct, location_required,
        )
        if not is_match:
            raise HTTPException(
                status_code=403,
                detail=f"Check-out rejected: face did not match your reference photo ({similarity_pct}% similarity).",
            )
    else:
        logger.info(
            "check-out user=%s NO PHOTO ON FILE -- face check skipped location_required=%s",
            current_user.UserName, location_required,
        )

    existing.PunchOutTime = _now_time_str()
    db.commit()
    db.refresh(existing)

    logger.info(
        "attendance id=%s user=%s punched out at=%s",
        existing.pkEAId, current_user.UserName, existing.PunchOutTime,
    )

    return _record_to_out(existing, "present", is_match=is_match if photo_required else None,
                           similarity_pct=similarity_pct)


@app.get("/attendance/history", response_model=list[schemas.AttendanceOut])
def history(
    db: Session = Depends(get_db),
    current_user: models.SalEmployee = Depends(auth.get_current_user),
):
    """Ordered by AtDate (string) desc -- relies on AtDate being stored as
    'YYYY-MM-DD' everywhere it's written (see EmpAttendancePunch's
    docstring); a different date format breaks this ordering silently."""
    records = (
        db.query(models.EmpAttendancePunch)
        .filter(models.EmpAttendancePunch.EmpCode == current_user.EmpCode)
        .order_by(models.EmpAttendancePunch.AtDate.desc(), models.EmpAttendancePunch.PunchInTime.desc())
        .all()
    )
    # No stored status/face-match on this table -- every past record here
    # reads back as "present" with face fields empty. See check_in()'s
    # docstring re: the lost audit trail for rejected attempts.
    return [_record_to_out(r, "present") for r in records]