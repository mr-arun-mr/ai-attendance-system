import json
import numpy as np
import face_recognition
import cv2
from typing import Optional
from app.core.config import settings


def extract_embedding(image_bytes: bytes) -> Optional[list[float]]:
    """Return 128-dim face embedding from raw image bytes, or None if no face found."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return None
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(img_rgb)
    if not encodings:
        return None
    return encodings[0].tolist()


def match_embedding(
    query: list[float],
    stored_embeddings: list[tuple[int, list[float]]],
    threshold: float | None = None,
) -> Optional[tuple[int, float]]:
    """
    Compare query embedding against a list of (user_id, embedding) pairs.
    Returns (user_id, confidence) of the best match if within threshold, else None.
    confidence = 1 - distance (higher is better).
    """
    if not stored_embeddings:
        return None

    thr = threshold if threshold is not None else settings.RECOGNITION_THRESHOLD
    query_arr = np.array(query)
    best_user_id = None
    best_dist = float("inf")

    for user_id, emb in stored_embeddings:
        dist = float(np.linalg.norm(query_arr - np.array(emb)))
        if dist < best_dist:
            best_dist = dist
            best_user_id = user_id

    if best_dist <= thr:
        confidence = round(1.0 - best_dist, 4)
        return best_user_id, confidence
    return None


def annotate_frame(
    frame_bytes: bytes,
    detections: list[dict],
) -> bytes:
    """
    Draw bounding boxes and labels on a frame.
    detections: list of {top, right, bottom, left, name, confidence}
    Returns JPEG bytes.
    """
    nparr = np.frombuffer(frame_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return frame_bytes

    for det in detections:
        top, right, bottom, left = det["top"], det["right"], det["bottom"], det["left"]
        name = det.get("name", "Unknown")
        conf = det.get("confidence")
        label = f"{name} ({conf:.2f})" if conf else name
        color = (0, 200, 0) if name != "Unknown" else (0, 0, 220)
        cv2.rectangle(img, (left, top), (right, bottom), color, 2)
        cv2.rectangle(img, (left, bottom - 28), (right, bottom), color, cv2.FILLED)
        cv2.putText(img, label, (left + 4, bottom - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buf.tobytes()


def detect_faces_in_frame(
    frame_bytes: bytes,
    stored_embeddings: list[tuple[int, str, list[float]]],
) -> tuple[bytes, list[dict], list[dict]]:
    """
    Run face detection + recognition on a frame.
    stored_embeddings: list of (user_id, full_name, embedding)

    Returns:
      (annotated_jpeg_bytes, recognised_results, unknown_faces)

    recognised_results: list of {user_id, name, confidence}
    unknown_faces: list of {embedding: list[float], crop_bytes: bytes | None}
      — one entry per unmatched face above MIN_FACE_SIZE, for external buffering.
    """
    nparr = np.frombuffer(frame_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return frame_bytes, [], []

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(img_rgb)
    face_encodings = face_recognition.face_encodings(img_rgb, face_locations)

    id_emb_pairs = [(uid, emb) for uid, _, emb in stored_embeddings]
    name_map = {uid: name for uid, name, _ in stored_embeddings}

    results = []
    unknowns = []
    detections = []

    for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
        if (bottom - top) < settings.MIN_FACE_SIZE or (right - left) < settings.MIN_FACE_SIZE:
            continue  # face too small (distant/partial) to match reliably
        match = match_embedding(encoding.tolist(), id_emb_pairs)
        if match:
            user_id, confidence = match
            name = name_map[user_id]
            results.append({"user_id": user_id, "name": name, "confidence": confidence})
            detections.append({
                "top": top, "right": right, "bottom": bottom, "left": left,
                "name": name, "confidence": confidence,
            })
        else:
            detections.append({
                "top": top, "right": right, "bottom": bottom, "left": left,
                "name": "Unknown", "confidence": None,
            })
            # Crop the face for thumbnail storage
            pad = 10
            h, w = img_bgr.shape[:2]
            crop = img_bgr[
                max(0, top - pad):min(h, bottom + pad),
                max(0, left - pad):min(w, right + pad),
            ]
            crop_bytes: Optional[bytes] = None
            if crop.size > 0:
                _, cbuf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
                crop_bytes = cbuf.tobytes()
            unknowns.append({"embedding": encoding.tolist(), "crop_bytes": crop_bytes})

    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
    annotated = annotate_frame(buf.tobytes(), detections)
    return annotated, results, unknowns
