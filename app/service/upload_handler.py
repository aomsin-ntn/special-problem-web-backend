from fastapi import UploadFile
from pathlib import Path
import shutil
from uuid import uuid4
from app.service.ocr_model import Model

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def handle_upload(file: UploadFile):
    ext = Path(file.filename).suffix
    safe_name = f"{uuid4().hex}{ext}"
    dest = UPLOAD_DIR / safe_name

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)


    model = Model()
    poppler = r"C:\poppler-25.07.0\Library\bin"
    fields = model.processDocumentOCR(str(dest), poppler_path=poppler)

    return {
        "status": "ok",
        "filename": file.filename,
        "saved_as": safe_name,
        "fields": fields,
    }


