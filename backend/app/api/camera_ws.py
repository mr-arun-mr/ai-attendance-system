"""
WebSocket endpoint for live camera feed processing.

Protocol:
  Client → Server: raw JPEG frame bytes
  Server → Client: JSON message
    { "type": "frame", "jpeg": "<base64>", "detections": [...] }
    detection = {
        "user_id": int, "name": str, "confidence": float,
        "event": "checked_in" | "checked_out" | "already_done" | "too_soon"
    }
    { "type": "ping" }
    { "type": "error", "detail": str }

Unknown face buffering:
  Faces that don't match any registered user are saved as UnknownFaceCapture rows
  (embedding + JPEG thumbnail) for later clustering via POST /clusters/run.
  Per-connection deduplication: a face is only saved if its embedding is at least
  UNKNOWN_DEDUP_DIST away from any face saved in the last UNKNOWN_DEDUP_WINDOW_S
  seconds, preventing repeated frames of the same person from flooding the table.
"""
import base64
import json
import asyncio
import time
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.face_embedding import FaceEmbedding
from app.models.unknown_face_capture import UnknownFaceCapture
from app.models.user import User
from app.services.face_service import detect_faces_in_frame
from app.services.attendance_service import mark_attendance
from app.services.cluster_service import save_unknown_thumbnail

router = APIRouter(tags=["camera-ws"])

# Minimum L2 distance between a new unknown embedding and any recently saved
# one before we bother writing another row (deduplication).
UNKNOWN_DEDUP_DIST = 0.30
# How long (seconds) a saved embedding is kept in the dedup window.
UNKNOWN_DEDUP_WINDOW_S = 60


async def _load_embeddings(db):
    result = await db.execute(
        select(FaceEmbedding.user_id, FaceEmbedding.embedding, User.full_name)
        .join(User, FaceEmbedding.user_id == User.id)
    )
    rows = result.all()
    return [(r.user_id, r.full_name, json.loads(r.embedding)) for r in rows]


def _should_save_unknown(embedding: list[float], recent: list[tuple[list[float], float]]) -> bool:
    """Return True only if the embedding is far enough from all recently saved ones."""
    if not recent:
        return True
    emb = np.array(embedding)
    for saved_emb, _ in recent:
        if np.linalg.norm(emb - np.array(saved_emb)) < UNKNOWN_DEDUP_DIST:
            return False
    return True


@router.websocket("/ws/camera/{camera_id}")
async def camera_websocket(websocket: WebSocket, camera_id: int):
    await websocket.accept()

    # In-memory dedup buffer: list of (embedding_list, saved_at_epoch)
    recent_unknowns: list[tuple[list[float], float]] = []

    try:
        async with AsyncSessionLocal() as db:
            embeddings = await _load_embeddings(db)
            last_reload = asyncio.get_event_loop().time()

            while True:
                now_loop = asyncio.get_event_loop().time()
                if now_loop - last_reload > 60:
                    embeddings = await _load_embeddings(db)
                    last_reload = now_loop

                # Prune expired dedup entries
                now_ts = time.time()
                recent_unknowns = [
                    (e, t) for e, t in recent_unknowns
                    if now_ts - t < UNKNOWN_DEDUP_WINDOW_S
                ]

                try:
                    frame_bytes = await asyncio.wait_for(websocket.receive_bytes(), timeout=30)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "ping"})
                    continue

                annotated, recognitions, unknowns = detect_faces_in_frame(frame_bytes, embeddings)
                jpeg_b64 = base64.b64encode(annotated).decode()

                # Buffer unknown faces with deduplication
                needs_commit = False
                for face in unknowns:
                    enc = face["embedding"]
                    if not _should_save_unknown(enc, recent_unknowns):
                        continue
                    thumb_path = (
                        save_unknown_thumbnail(face["crop_bytes"])
                        if face["crop_bytes"]
                        else None
                    )
                    db.add(UnknownFaceCapture(
                        embedding=json.dumps(enc),
                        thumbnail_path=thumb_path,
                        camera_id=camera_id,
                    ))
                    recent_unknowns.append((enc, time.time()))
                    needs_commit = True

                if needs_commit:
                    await db.commit()

                detections_out = []
                for rec in recognitions:
                    log, event = await mark_attendance(
                        db,
                        rec["user_id"],
                        confidence=rec["confidence"],
                        camera_id=camera_id,
                    )
                    detections_out.append({
                        "user_id": rec["user_id"],
                        "name": rec["name"],
                        "confidence": rec["confidence"],
                        "event": event,
                        "check_in": log.check_in.isoformat() if log and log.check_in else None,
                        "check_out": log.check_out.isoformat() if log and log.check_out else None,
                    })

                await websocket.send_json({
                    "type": "frame",
                    "jpeg": jpeg_b64,
                    "detections": detections_out,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
