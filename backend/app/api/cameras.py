from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.camera import Camera
from app.models.user import User
from app.schemas.camera import CameraCreate, CameraUpdate, CameraOut
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("/", response_model=List[CameraOut])
async def list_cameras(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Camera).order_by(Camera.name))
    return result.scalars().all()


@router.post("/", response_model=CameraOut, status_code=201)
async def create_camera(
    body: CameraCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    cam = Camera(**body.model_dump())
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.patch("/{cam_id}", response_model=CameraOut)
async def update_camera(
    cam_id: int,
    body: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Camera).where(Camera.id == cam_id))
    cam = result.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(cam, field, val)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.delete("/{cam_id}", status_code=204)
async def delete_camera(
    cam_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Camera).where(Camera.id == cam_id))
    cam = result.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    await db.delete(cam)
    await db.commit()
