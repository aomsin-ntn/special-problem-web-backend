from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
import shutil
import cv2

from app.models.session import Session
from app.services.project_services import ProjectServices

class FileServices:
    def __init__(self, upload_dir="uploads", thumbnail_dir="thumbnails"):
        self.upload_dir = Path(upload_dir)
        self.thumbnail_dir = Path(thumbnail_dir)

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file):
        ext = Path(file.filename).suffix
        save_name = f"{uuid4().hex}{ext}"
        dest = self.upload_dir / save_name

        with dest.open("wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                buffer.write(chunk)

        return dest, save_name

    def save_thumbnail(self, image):
        thumbnail_path = self.thumbnail_dir / f"{uuid4().hex}_thumb.png"
        cv2.imwrite(str(thumbnail_path), image)
        return str(thumbnail_path)
    
    @staticmethod
    async def cleanup_temp_files(db: Session):
        expired_time = datetime.utcnow() - timedelta(hours=24)

        temp_files = await ProjectServices.get_expired_temp_files(db, expired_time)

        for file in temp_files:
            try:
                if file.file_path and Path(file.file_path).exists():
                    Path(file.file_path).unlink()

                if file.thumbnail_path and Path(file.thumbnail_path).exists():
                    Path(file.thumbnail_path).unlink()
            except Exception as e:
                print(f"Delete error: {e}")

            await ProjectServices.delete_project_file(db, file.file_id)

        db.commit()

    @staticmethod
    def safe_delete(path: str | None):
        if not path:
            return

        file_path = Path(path)

        if file_path.exists() and file_path.is_file():
            file_path.unlink()