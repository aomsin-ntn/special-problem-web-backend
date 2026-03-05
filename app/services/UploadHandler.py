from fastapi import UploadFile
from pathlib import Path
import shutil
from uuid import uuid4

class UploadHandler:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile):
        ext = Path(file.filename).suffix
        safe_name = f"{uuid4().hex}{ext}"
        dest = self.upload_dir / safe_name

        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "original_filename": file.filename,
            "saved_as": safe_name,
            "path": str(dest)
        }