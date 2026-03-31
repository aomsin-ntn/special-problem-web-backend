from app.core.ocr_engine import OCREngine
from app.services.webhook_services import WebhookServices
from fastapi import UploadFile
from pathlib import Path
from uuid import uuid4
import shutil
import json
import easyocr
import cv2
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
from app.repository.user_repository import UserRepository

class UploadServices:
    poppler_path = r"C:\poppler-25.07.0\Library\bin"
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.thumbnail_dir = Path("thumbnails")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_engine = OCREngine(poppler_path=self.poppler_path)
        self.webhook_services = WebhookServices()

    async def save_file(self, file: UploadFile, page: list[int] = [1],session: AsyncSession = Depends(get_db)):
        ext = Path(file.filename).suffix
        safe_name = f"{uuid4().hex}{ext}"
        dest = self.upload_dir / safe_name

        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        thumbnail = self.ocr_engine.pdf_to_image(str(dest), page_num=1)
        thumbnail_path = self.thumbnail_dir / f"{uuid4().hex}_thumb.png"
        cv2.imwrite(thumbnail_path, thumbnail)

        error_dict = {
            "ptthn": {"correct": "python", "count": 10},
            "pythn": {"correct": "python", "count": 15},
            "รก": {"correct": "รัก", "count": 5},
            "ออกไป": {"correct": "ออกไป", "count": 10}
        }

        page = sorted(page)[:2]
        ocr_text1 = self.ocr_engine.process_document_ocr(str(dest), page_num=page[0])
        ocr_text2 = self.ocr_engine.process_document_ocr(str(dest), page_num=page[1])
        ext_text1 = self.ocr_engine.pdf_to_text(str(dest), page_num=page[0])
        ext_text2 = self.ocr_engine.pdf_to_text(str(dest), page_num=page[1])

        checker = SpellChecker(error_dict, threshold=10)
        suggestions1 = checker.compare(ocr_text1, ext_text1)
        # suggestions2 = checker.compare(ocr_text2, ext_text2)
        suggestions2 = {"choose": "text2", "result": None}

        # suggestions1 = checker.compare(ext_text1, ext_text1)
        # suggestions2 = checker.compare(ext_text2, ext_text2)
        
        choice1 = suggestions1.get("choose")
        choice2 = suggestions2.get("choose")

        text1 = ocr_text1 if choice1 == "text1" else ext_text1
        text2 = ocr_text2 if choice2 == "text1" else ext_text2

        fields1 = checker.extract_fields(text1)
        fields2 = checker.extract_fields(text2)

        print(fields1, fields2)

        fields1 = {k: checker.clean_text(v) if v else v for k, v in fields1.items()}
        fields2 = {k: checker.clean_text(v) if v else v for k, v in fields2.items()}

        """" !!!check if degree is exits """
        #degree = session.query(Degree).filter(Degree.degree_name_th == fields1.get("ปริญญา")).first()
        degree = None

        """" !!!get the current user via dependency injection (login session)"""
        user = User(
            user_id=uuid4(),
            student_id="65000001",
            user_name_th="สมชาย ใจสู้",
            user_name_en="Somchai Jaisoo",
            degree_id="CS01",
            role=Role.STUDENT,
            email="somchai@example.com",
            password_hash="$2b$12$examplehashedpassword"
        )
        
        """" !!!create the thumbnail and store the path """
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name=file.filename,
            file_path=dest,
            thumbnail_path="/uploads/thumbnails/diagram_thumb.png", 
            uploaded_at=datetime.utcnow
        )


        """" !!!make tge field2 (support the EN)"""
        project=Project(
            title_th=fields1.get("หัวข้อ", ""),
            title_en="apichard",
            # title_en=fields2.get("title", ""),
            abstract_th=fields1.get("คำสำคัญ", ""),
            # abstract_en=fields2.get("abstract", ""),
            abstract_en="Hello",
            academic_year=fields1.get("ปิการศึกษา", ""),
            degree_id=degree.id if degree else None,
            created_by=user.user_id,
            is_active=False,
            file_id=project_file.file_id,
            downloaded_count=0
        )

        user2 = User(
            user_id=uuid4(),
            student_id="65555555",
            user_name_th="ส้มโต่ย ส้มโต้ย",
            user_name_en="Somtoi Somtoy",
            degree_id="CS01",
            role=Role.STUDENT,
            email="lnwsomtoyza@kmitl.ac.th",
            password_hash=None
        )

        project_file2 = ProjectFile(
            file_id=uuid4(),
            file_name=file.filename,
            file_path=str(dest),
            thumbnail_path=thumbnail_path, 
            uploaded_at=datetime.utcnow
        )

        project_detail2 = Project(
            title_th=fields1.get("Title", ""),
            title_en=fields2.get("Title",""),
            abstract_th=fields1.get("Abstract",""),
            abstract_en=fields1.get("Abstract",""),
            academic_year=fields1.get("AcademicYear",""),
            degree_id= None,
            created_by=user2.user_id,
            is_active=True,
            file_id=project_file2.file_id,
            download_count=0
        )

        await UserRepository.create_user(session, user)
        await ProjectRepository.create_project_file(session, project_file)
        await ProjectRepository.create_project(session, project)


        """ !!! split the file from repository for more clean code"""
        # await UserRepository.create_user(session, user)
        # await ProjectRepository.create_project_file(session, project_file)
        # await ProjectRepository.create_project(session, project)

        #print(project)

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
            "thumbnail_path": str(thumbnail_path),
            "saved_as": safe_name,
            "fields-th": fields1,
            "fields-en": fields2
        }