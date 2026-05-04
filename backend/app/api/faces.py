import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from app.core.database import get_db
from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.schemas.user import UserOut
from app.api.deps import get_current_user, require_admin
from app.services.face_service import extract_embedding

router = APIRouter(prefix="/faces", tags=["faces"])


@router.post("/register/{user_id}")
async def register_faces(
    user_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Upload 1–10 face photos for a user. Each photo's embedding is stored individually."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    embeddings = []
    for f in files:
        content = await f.read()
        emb = extract_embedding(content)
        if emb:
            embeddings.append(emb)

    if not embeddings:
        raise HTTPException(status_code=422, detail="No valid face found in any uploaded image")

    # Store one embedding row per photo so every angle is preserved for matching
    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user_id))
    for emb in embeddings:
        db.add(FaceEmbedding(user_id=user_id, embedding=json.dumps(emb)))
    await db.commit()
    return {"message": f"Face registered from {len(embeddings)} photo(s)", "user_id": user_id}


@router.post("/register-from-frame/{user_id}")
async def register_face_from_frame(
    user_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Append a face embedding captured from a CCTV frame to the user's registration.

    Use this after HD enrollment to add a reference embedding in the CCTV domain
    (same camera angle, lighting, resolution), which reduces the HD-vs-CCTV
    domain gap and improves live recognition accuracy.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    emb = extract_embedding(await file.read())
    if emb is None:
        raise HTTPException(status_code=422, detail="No face detected in frame")

    db.add(FaceEmbedding(user_id=user_id, embedding=json.dumps(emb)))
    await db.commit()

    count_result = await db.execute(
        select(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
    )
    total = len(count_result.scalars().all())
    return {"message": "Frame registered", "user_id": user_id, "total_embeddings": total}


@router.delete("/register/{user_id}", status_code=204)
async def delete_face(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user_id))
    await db.commit()


@router.post("/identify")
async def identify_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Identify a single uploaded photo against all registered faces."""
    content = await file.read()
    query_emb = extract_embedding(content)
    if query_emb is None:
        raise HTTPException(status_code=422, detail="No face detected in image")

    all_emb = await db.execute(
        select(FaceEmbedding.user_id, FaceEmbedding.embedding)
    )
    rows = all_emb.all()
    if not rows:
        return {"match": None}

    from app.services.face_service import match_embedding
    pairs = [(r.user_id, json.loads(r.embedding)) for r in rows]
    match = match_embedding(query_emb, pairs)
    if not match:
        return {"match": None}

    user_id, confidence = match
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return {
        "match": {
            "user_id": user_id,
            "full_name": user.full_name if user else "Unknown",
            "employee_id": user.employee_id if user else None,
            "confidence": confidence,
        }
    }
