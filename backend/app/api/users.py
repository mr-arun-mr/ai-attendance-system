from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import aiofiles
import os
import uuid
from app.core.database import get_db
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.models.department import Department
from app.schemas.user import UserCreate, UserUpdate, UserOut, DepartmentCreate, DepartmentOut
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserOut])
async def list_users(
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(User)
    if department_id:
        q = q.where(User.department_id == department_id)
    result = await db.execute(q.order_by(User.full_name))
    users = result.scalars().all()

    out = []
    for u in users:
        emb = await db.execute(
            select(func.count()).where(FaceEmbedding.user_id == u.id)
        )
        has_face = emb.scalar() > 0
        data = UserOut.model_validate(u)
        data.has_face = has_face
        out.append(data)
    return out


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        full_name=body.full_name,
        employee_id=body.employee_id,
        hashed_password=hash_password(body.password),
        department_id=body.department_id,
        is_admin=body.is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    data = UserOut.model_validate(user)
    data.has_face = False
    return data


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    emb = await db.execute(select(func.count()).where(FaceEmbedding.user_id == user_id))
    data = UserOut.model_validate(user)
    data.has_face = emb.scalar() > 0
    return data


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(user, field, val)
    await db.commit()
    await db.refresh(user)
    emb = await db.execute(select(func.count()).where(FaceEmbedding.user_id == user_id))
    data = UserOut.model_validate(user)
    data.has_face = emb.scalar() > 0
    return data


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/photo", response_model=UserOut)
async def upload_photo(
    user_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(settings.FACE_DATA_DIR, "photos", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        content = await file.read()
        await f.write(content)
    user.photo_path = f"/face_data/photos/{filename}"
    await db.commit()
    await db.refresh(user)
    emb = await db.execute(select(func.count()).where(FaceEmbedding.user_id == user_id))
    data = UserOut.model_validate(user)
    data.has_face = emb.scalar() > 0
    return data


# Departments
dept_router = APIRouter(prefix="/departments", tags=["departments"])


@dept_router.get("/", response_model=List[DepartmentOut])
async def list_departments(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Department).order_by(Department.name))
    return result.scalars().all()


@dept_router.post("/", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    dept = Department(name=body.name)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@dept_router.delete("/{dept_id}", status_code=204)
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(dept)
    await db.commit()
