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
"""
import base64
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.face_embedding import FaceEmbedding
from app.models.user import User
from app.services.face_service import detect_faces_in_frame
from app.services.attendance_service import mark_attendance

router = APIRouter(tags=["camera-ws"])


async def _load_embeddings(db):
    result = await db.execute(
        select(FaceEmbedding.user_id, FaceEmbedding.embedding, User.full_name)
        .join(User, FaceEmbedding.user_id == User.id)
    )
    rows = result.all()
    return [(r.user_id, r.full_name, json.loads(r.embedding)) for r in rows]


@router.websocket("/ws/camera/{camera_id}")
async def camera_websocket(websocket: WebSocket, camera_id: int):
    await websocket.accept()
    try:
        async with AsyncSessionLocal() as db:
            embeddings = await _load_embeddings(db)
            last_reload = asyncio.get_event_loop().time()

            while True:
                now = asyncio.get_event_loop().time()
                if now - last_reload > 60:
                    embeddings = await _load_embeddings(db)
                    last_reload = now

                try:
                    frame_bytes = await asyncio.wait_for(websocket.receive_bytes(), timeout=30)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "ping"})
                    continue

                annotated, recognitions = detect_faces_in_frame(frame_bytes, embeddings)
                jpeg_b64 = base64.b64encode(annotated).decode()

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
                        # include times so the frontend can display them
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
