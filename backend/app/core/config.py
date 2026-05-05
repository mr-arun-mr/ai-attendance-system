from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://attendance:attendance_secret@db:5432/attendance_db"
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    RECOGNITION_THRESHOLD: float = 0.55
    MIN_FACE_SIZE: int = 60  # minimum face height/width in pixels to attempt recognition
    ADMIN_EMAIL: str = "admin@attendance.local"
    ADMIN_PASSWORD: str = "admin123"
    FACE_DATA_DIR: str = "/app/face_data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **values):
        super().__init__(**values)
        # Allow BACKEND_CORS_ORIGINS as JSON string
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            self.BACKEND_CORS_ORIGINS = json.loads(self.BACKEND_CORS_ORIGINS)


settings = Settings()
