"""
One-off helper: attach a reference face photo to an EXISTING employee row.

Usage:
    python add_reference_photo.py <username> <path_to_photo.jpg>

Example:
    python add_reference_photo.py testuser1 ./sample_faces/suresh.jpg

Validates that a face is detectable in the photo, then stores the raw image
bytes in SalEmployee.Photo (that's what main.py's _get_reference_face() reads
from at request time). Also clears any cached face crop under faces_ref/ for
this username so the app re-extracts from the new photo on the next request,
rather than serving a stale cached one.

Run it from the same folder as database.py / models.py / face_utils.py (your
backend root).
"""

import sys
from pathlib import Path

from database import SessionLocal, FACES_DIR
from face_utils import extract_face, NoFaceFoundError
import models


def main():
    if len(sys.argv) != 3:
        print("Usage: python add_reference_photo.py <username> <path_to_photo.jpg>")
        sys.exit(1)

    username = sys.argv[1]
    photo_path = Path(sys.argv[2])

    if not photo_path.exists():
        print(f"Photo not found: {photo_path}")
        sys.exit(1)

    db = SessionLocal()
    try:
        employee = (
            db.query(models.SalEmployee)
            .filter(models.SalEmployee.UserName == username)
            .first()
        )
        if not employee:
            print(f"No SalEmployee found with UserName: {username}")
            sys.exit(1)

        image_bytes = photo_path.read_bytes()

        # Validate a face is actually detectable before storing it -- same
        # rejection behavior as the old signup flow. We don't keep the
        # cropped result here; main.py extracts + caches its own crop from
        # SalEmployee.Photo lazily on first use.
        try:
            extract_face(image_bytes)
        except NoFaceFoundError as e:
            print(f"Rejected: {e}")
            sys.exit(1)
        except ValueError as e:
            print(f"Rejected: {e}")
            sys.exit(1)

        employee.Photo = image_bytes
        db.commit()

        # Drop any previously cached crop for this username so the app
        # re-derives it from the new photo instead of serving a stale one.
        cache_path = FACES_DIR / f"{username}.png"
        if cache_path.exists():
            cache_path.unlink()

        print(f"Done. {employee.Employee} ({employee.UserName}) now has a reference photo on file.")
    finally:
        db.close()


if __name__ == "__main__":
    main()