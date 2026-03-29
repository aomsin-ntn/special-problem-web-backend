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
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.degree import Degree
from app.models.user import User,Role
from app.database import get_db
from sqlmodel import Session
from app.repository.project_repository import ProjectRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

class UploadServices:
    poppler_path = r"C:\poppler-25.07.0\Library\bin"
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_engine = OCREngine(poppler_path=self.poppler_path)
        self.webhook_services = WebhookServices()

    async def save_file(self, file: UploadFile, page: list[int] = [1],session: AsyncSession = Depends(get_db)):
        ext = Path(file.filename).suffix
        safe_name = f"{uuid4().hex}{ext}"
        dest = self.upload_dir / safe_name

        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        #ocr_text1 = self.ocr_engine.process_document_ocr(str(dest), page_num=page[0])
        #ocr_text2 = self.ocr_engine.process_document_ocr(str(dest), page_num=page[1])
        ext_text1 = self.ocr_engine.pdf_to_text(str(dest), page_num=page[0])
        ext_text2 = self.ocr_engine.pdf_to_text(str(dest), page_num=page[1])
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
        #suggestions1 = checker.compare(ocr_text1, ext_text1)
        suggestions1 = checker.compare(ext_text1, ext_text1)
        #suggestions2 = checker.compare(ocr_text2, ext_text2)
        suggestions2 = checker.compare(ext_text2, ext_text2)
        # print(suggestions)
        if suggestions1["better"] in ["equal", "text1"]: 
            fields1 = checker.extract_fields(ext_text1)
        else:
            fields1 = checker.extract_fields(ext_text1)
        if suggestions2["better"] in ["equal", "text2"]: 
            fields2 = checker.extract_fields(ext_text2)
        else:
            fields2 = checker.extract_fields(ext_text2)
        print(fields1, ext_text2)
        user = User(
            user_id="U000000001",
            student_id="65000001",
            user_name_th="สมชาย ใจสู้",
            user_name_en="Somchai Jaisoo",
            degree_id="CS01",
            role=Role.STUDENT,
            email="somchai@example.com",
            password_hash="$2b$12$examplehashedpassword"
        )
        #result = session.query(Degree).filter(Degree.degree_name_th == fields1.get("ปริญญา")).first()
        result = None
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name="diagram.png",
            file_path="/uploads/projects/diagram.png",
            thumbnail_path="/uploads/thumbnails/diagram_thumb.png",
            upload_time=datetime(2026, 3, 10, 9, 0)
        )
        project=Project(
            title_th=fields1.get("หัวข้อ", ""),
            title_en="apichard",
            # title_en=fields2.get("title", ""),
            abstract_th=fields1.get("คำสำคัญ", ""),
            # abstract_en=fields2.get("abstract", ""),
            abstract_en="Hello",
            academic_year=fields1.get("ปิการศึกษา", ""),
            degree_id=result.id if result else None,
            create_by=user.user_id,
            is_active=False,
            file_id=project_file.file_id,
            download_count=0
        )
        await ProjectRepository.create_user(session, user)
        await ProjectRepository.create_project_file(session, project_file)
        await ProjectRepository.create_project(session, project)

        print(project)
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
            "fields-th": fields1,
            "fields-en": fields2
        }