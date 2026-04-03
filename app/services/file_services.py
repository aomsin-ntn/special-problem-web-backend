from pathlib import Path
from uuid import uuid4
import shutil
import cv2

class FileService:
    def __init__(self, upload_dir="uploads", thumbnail_dir="thumbnails"):
        self.upload_dir = Path(upload_dir)
        self.thumbnail_dir = Path(thumbnail_dir)

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file):
        ext = Path(file.filename).suffix
        safe_name = f"{uuid4().hex}{ext}"
        dest = self.upload_dir / safe_name

        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return dest, safe_name

    def save_thumbnail(self, image):
        thumbnail_path = self.thumbnail_dir / f"{uuid4().hex}_thumb.png"
        cv2.imwrite(str(thumbnail_path), image)
        return str(thumbnail_path)