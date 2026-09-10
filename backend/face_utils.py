import cv2
import numpy as np

FACE_SIZE = (200, 200)
MATCH_CONFIDENCE_THRESHOLD = 60.0  # LBPH distance: lower = more similar. Below this = match.
# This threshold is a starting point tuned for typical LBPH behavior on real face
# photos (same person under different lighting/angle usually scores well under 60,
# different people usually score well above it). Test with your own photos and
# adjust this constant if you get too many false matches/rejections.

# Uses the Haar cascade that ships inside opencv-python — no need to download
# or bundle a separate .xml file.
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_face_cascade = cv2.CascadeClassifier(_CASCADE_PATH)


class NoFaceFoundError(Exception):
    pass


def _decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode the uploaded image. Please upload a valid JPG/PNG photo.")
    return img


def extract_face(image_bytes: bytes) -> np.ndarray:
    """Detect the largest face in the image and return a normalized grayscale crop."""
    img = _decode_image(image_bytes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        raise NoFaceFoundError("No face detected in the photo. Please try a clearer, front-facing photo.")

    # pick the largest detected face (by area) in case of multiple faces
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y:y + h, x:x + w]
    return cv2.resize(face_crop, FACE_SIZE)


def save_face_ref(face_array: np.ndarray, path: str):
    cv2.imwrite(path, face_array)


def load_face_ref(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Reference face image not found at {path}")
    return img


def compare_faces(reference_face: np.ndarray, current_face: np.ndarray):
    """
    Train an LBPH recognizer on the single reference face, then predict on the
    current face. Returns (is_match: bool, confidence: float, similarity_pct: float).
    LBPH confidence is a distance -> lower means more similar.
    """
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train([reference_face], np.array([0]))
    label, confidence = recognizer.predict(current_face)

    is_match = bool(label == 0 and confidence < MATCH_CONFIDENCE_THRESHOLD)
    similarity_pct = max(0.0, min(100.0, 100.0 - confidence))
    return is_match, float(confidence), round(similarity_pct, 1)
