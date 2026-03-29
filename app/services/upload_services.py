from app.core.ocr_engine import OCREngine
from app.services.webhook_services import WebhookServices
from fastapi import UploadFile
from pathlib import Path
from uuid import uuid4
import shutil
import json
import easyocr
from attacut import tokenize
from app.services.spellchecker_services import SpellChecker

class UploadServices:
    poppler_path = r"C:\poppler-25.07.0\Library\bin"
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_engine = OCREngine(poppler_path=self.poppler_path)
        self.webhook_services = WebhookServices()

    def extract_fields(self, text: str) -> dict:
        pattern = {
            'หัวข้อ': r'(?:หัวข้อ(?:ปัญหาพิเศษ|สหกิจศึกษา|โครงงานพิเศษ)|สหกิจศึกษา)\s*(.*?)(?=\sชื่อนักศึกษา|$)',
            'ชื่อนักศึกษา': r'ชื่อนักศึกษา\s*(.*?)(?=\sปริญญา|$)',
            'ปริญญา': r'ปริญญา\s*(.*?)(?=\sภาควิชา|$)',
            'ภาควิชา': r'ภาควิชา\s*(.*?)(?=\sคณะ|ปีการศึกษา|$)',
            'คณะ': r'คณะ\s*(.*?)(?=\sมหาวิทยาลัย|$)',
            'มหาวิทยาลัย': r'มหาวิทยาลัย\s*(.*?)(?=\sปีการศึกษา|$)',
            'ปีการศึกษา': r'ปีการศึกษา\s*(.*?)(?=\sอาจารย์ที่ปรึกษา|$)',
            'อาจารย์ที่ปรึกษา': r'อาจารย์ที่ปรึกษา\s*(.*?)(?=\sบทคัดย่อ|$)',
            'บทคัดย่อ': r'บทคัดย่อ\s*(.*?)(?=\sคำสำคัญ|$)',
            'คำสำคัญ': r'(?:คำสำคัญ:|คำสำคัญ)\s*(.*?)(?=\sTitle|$)',
        }
        results = {}
        for key, pat in pattern.items():
            m = re.search(pat, text, flags=re.DOTALL)
            if m:
                results[key] = m.group(1).strip()
        return results

    async def save_file(self, file: UploadFile):
        ext = Path(file.filename).suffix
        safe_name = f"{uuid4().hex}{ext}"
        dest = self.upload_dir / safe_name

        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ocr_text = self.ocr_engine.process_document_ocr(str(dest), page_num=4)
        ext_text = self.ocr_engine.pdf_to_text(str(dest), page_num=4)
        # ocr = self.webhook_services.send_text(ocr_text)
        # ext = self.webhook_services.send_text(ext_text)
        # print(ext)
        error_dict = {
            "ptthn": {"correct": "python", "count": 10},
            "pythn": {"correct": "python", "count": 15},
            "รก": {"correct": "รัก", "count": 5},
            "ออกไป": {"correct": "ออกไป", "count": 10}
        }

        checker = SpellChecker(error_dict, threshold=10)
        suggestions = checker.compare(ocr_text, ext_text)
        print(suggestions)
        # print("Text1:", result1)
        # print("Text2:", result2)
        # print(conclusion)
        # token = tokenize(ocr_text)
        # print(token)
        # print(type(ext))
        # result = list(ext.values())
        # print(result)
        return {
            "original_filename": file.filename,
            "saved_as": safe_name,
            # "fields": ocr,
            # "fields2": ext
        }