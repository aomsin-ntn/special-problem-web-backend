from fastapi import UploadFile
from pathlib import Path
import shutil
from uuid import uuid4

from app.core.ocr_engine import OCREngine
from app.services.webhook_services import WebhookServices

class UploadServices:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_engine = OCREngine()
        self.webhook_services = WebhookServices()

    async def save_file(self, file: UploadFile):
        ext = Path(file.filename).suffix
        safe_name = f"{uuid4().hex}{ext}"
        dest = self.upload_dir / safe_name

        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        field = self.ocr_engine.processDocumentOCR(str(dest), page_num=4)
        #field= "Sample extracted text from OCR"
        text = self.webhook_services.send_text(field)

        return {
            "original_filename": file.filename,
            "saved_as": safe_name,
            "fields": text
        }