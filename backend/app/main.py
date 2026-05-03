import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal, Base
from app.core.security import hash_password

# Import all models so SQLAlchemy registers them before create_all
from app.models import User, Department, FaceEmbedding, AttendanceLog, Camera

from app.api.auth import router as auth_router
from app.api.users import router as users_router, dept_router
from app.api.faces import router as faces_router
from app.api.attendance import router as attendance_router
from app.api.reports import router as reports_router
from app.api.cameras import router as cameras_router
from app.api.camera_ws import router as ws_router


async def _seed_admin(db):
    result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
    if result.scalar_one_or_none():
        return
    admin = User(
        email=settings.ADMIN_EMAIL,
        full_name="System Admin",
        employee_id="ADMIN001",
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        is_admin=True,
        is_active=True,
    )
    db.add(admin)
    await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    os.makedirs(os.path.join(settings.FACE_DATA_DIR, "photos"), exist_ok=True)
    async with AsyncSessionLocal() as db:
        await _seed_admin(db)
    yield
    await engine.dispose()


app = FastAPI(
    title="AI Attendance System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded face photos as static files
face_data_dir = settings.FACE_DATA_DIR
os.makedirs(face_data_dir, exist_ok=True)
app.mount("/face_data", StaticFiles(directory=face_data_dir), name="face_data")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(dept_router)
app.include_router(faces_router)
app.include_router(attendance_router)
app.include_router(reports_router)
app.include_router(cameras_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
