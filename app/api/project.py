"""
All API Routes
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import Annotated
from sqlmodel import Session
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from datetime import datetime

# Database & Auth
from app.database import get_db
from app.api.authentication import get_current_user

# Services
from app.services.upload_services import UploadServices
from app.services.project_services import ProjectServices

# Schemas
from app.schemas.root_schema import RootResponse, ItemResponse, ItemRequest, GetProjectRequestParams
from app.schemas.project_schema import ProjectSubmitRequest

# Models
from app.models.user import User, Role
from app.models.project_file import ProjectFile
from app.models.project import Project
from app.models.project_advisor import ProjectAdvisor
from app.models.project_author import ProjectAuthor
from app.models.project_keyword import ProjectKeyword
from app.models.keyword import Keyword

# Repositories
from app.repository.project_repository import ProjectRepository
from app.repository.user_repository import UserRepository


router = APIRouter(prefix="/project")

@router.post("/upload")
async def handle_upload(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    service: UploadServices = Depends(),
    pages: list[int] = Query([1], description="Page numbers for OCR"),
    user: User = Depends(get_current_user),
):
    try:
        # เช็คก่อนว่าเป็น PDF จริงไหม
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ PDF เท่านั้น")

        result = await service.handle_upload(file, pages=pages, db=db, current_user=user)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"OCR/Upload Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}"
        )

# ----------------------------------------------------
# 🚨 แก้ไข Path ให้ไม่ซ้ำกัน (ดาวน์โหลดตัวไฟล์ PDF)
# ----------------------------------------------------
@router.get("/download/file/{project_id}")
async def download_projectfile(
    db: Annotated[Session, Depends(get_db)],
    project_id: UUID,
):
    try:
        projectfile = await ProjectServices.download_projectfile(db, project_id)
        
        # ดักจับกรณีที่ไม่มีข้อมูลใน Database
        if not projectfile:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลไฟล์นี้ในระบบ")

        return FileResponse(
            path=projectfile.file_path,
            filename=projectfile.file_name,
            media_type="application/pdf"
        )
    except HTTPException:
        raise # โยน 404 ออกไปเลย
    except SQLAlchemyError as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="ข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล")
    except Exception as e:
        print(f"File Error: {e}")
        raise HTTPException(status_code=500, detail="ไม่พบไฟล์ในเซิร์ฟเวอร์ หรือไฟล์อาจถูกลบไปแล้ว")

@router.patch("/delete")
async def delete_project(
    db: Annotated[Session, Depends(get_db)],
    project_id: UUID,
):
    try:
        result = await ProjectServices.delete_project(db, project_id)
        if not result:
            # ถ้าหาโปรเจกต์ไม่เจอ ให้ throw 404
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Project not found"
            )
        return {"message": "Project deleted successfully"}
        
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Database error occurred while deleting"
        )

@router.get("/")
async def get_projects(
    db: Annotated[Session, Depends(get_db)],
    request: Annotated[GetProjectRequestParams, Query()]
):
    try:
        projects = await ProjectServices.get_projects(db, request)
        return projects
    except SQLAlchemyError as e:
        print(f"DB Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="ไม่สามารถดึงข้อมูลโปรเจกต์ได้ในขณะนี้"
        )

@router.get("/most_downloaded")
async def get_most_downloaded_projects(
    db: Annotated[Session, Depends(get_db)]
):
    projects = await ProjectServices.get_most_downloaded_projects(db)
    print(projects)
    return projects

@router.get("/details/{project_id}")
async def get_project_details(
    db: Annotated[Session, Depends(get_db)],
    project_id: UUID
):
    try:
        details = await ProjectServices.get_project_details(db, project_id)
        
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="ไม่พบข้อมูลโปรเจกต์นี้"
            )
        return details
        
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="เกิดข้อผิดพลาดในการดึงข้อมูลจากฐานข้อมูล"
        )

@router.get("/get_faculty")
async def get_faculty(
    db: Annotated[Session, Depends(get_db)]
):
    try:
        faculty = await ProjectServices.get_faculty(db)
        return faculty
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="เกิดข้อผิดพลาดในการดึงข้อมูลคณะ")


@router.post("/save")
async def save_project(
    data: ProjectSubmitRequest, 
    db: Annotated[Session, Depends(get_db)], 
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. สร้าง ProjectFile
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name=data.file_info.save_name,
            file_path=data.file_info.file_path,
            thumbnail_path=data.file_info.thumbnail_path,
            uploaded_at=datetime.utcnow()
        )
        await ProjectRepository.create_project_file(db, project_file)

        # 2. สร้าง Project
        project = Project(
            project_id=uuid4(),
            title_th=data.title_th,
            title_en=data.title_en,
            abstract_th=data.abstract_th,
            abstract_en=data.abstract_en,
            academic_year=data.academic_year,
            degree_id=data.degree_id,
            created_by=current_user.user_id,
            is_active=True,
            file_id=project_file.file_id,
            download_count=0
        )
        await ProjectRepository.create_project(db, project)

        # 3. สร้าง Advisor
        if data.advisor_id:
            project_advisor = ProjectAdvisor(
                project_id=project.project_id,
                advisor_id=data.advisor_id,
                advisor_order=1
            )
            await ProjectRepository.create_project_advisor(db, project_advisor)

        # 4. สร้าง User และ ProjectAuthor 
        for index, student_data in enumerate(data.students, start=1):
            if not student_data.student_id:
                continue

            user = await ProjectServices.get_user_by_student_id(db, student_data.student_id)
            if user:
                # 🚨 แก้ไขชื่อตัวแปรจาก student_name_th เป็น name_th ให้ตรงกับ Schema ของคุณ
                user.user_name_th = student_data.name_th
                user.user_name_en = student_data.name_en
                user.degree_id = data.degree_id
            else:
                user = User(
                    user_id=uuid4(),
                    student_id=student_data.student_id,
                    user_name_th=student_data.name_th,
                    user_name_en=student_data.name_en,
                    degree_id=data.degree_id,
                    role=Role.STUDENT,
                    email=student_data.student_id + "@kmitl.ac.th",
                    password_hash=None
                )
                await UserRepository.create_user(db, user)

            # ผูก Author ลงใน Project
            author = ProjectAuthor(
                project_id=project.project_id,
                user_id=user.user_id,
                author_order=index
            )
            await ProjectRepository.create_project_author(db, author)

        # 5. จัดการ Keywords
        db_keywords = await ProjectRepository.get_keywords(db)
        final_project_keywords = []

        for kw in data.keywords:
            match = ProjectServices.find_match(
                kw.th, kw.en, db_keywords, "keyword_text_th", "keyword_text_en"
            )
            
            if match:
                final_project_keywords.append(match)
            else:
                new_keyword = Keyword(
                    keyword_id=uuid4(),
                    keyword_text_th=kw.th,
                    keyword_text_en=kw.en
                )
                await ProjectRepository.create_keyword(db, new_keyword)
                final_project_keywords.append(new_keyword)

        # ผูก Keyword ลงใน Project
        for order, kw in enumerate(final_project_keywords, start=1):
            project_keyword = ProjectKeyword(
                project_id=project.project_id,
                keyword_id=kw.keyword_id,
                keyword_order=order
            )
            await ProjectRepository.create_project_keyword(db, project_keyword)

        return {"status": "success", "message": "บันทึกข้อมูลโปรเจกต์สำเร็จ", "project_id": project.project_id}

    except SQLAlchemyError as db_error:
        # เกิด Error เกี่ยวกับ Database (เช่น ข้อมูลซ้ำ, ID ไม่มีจริง)
        await db.rollback() # ยกเลิกการเปลี่ยนแปลงทั้งหมดที่ทำมาใน Transaction นี้
        print(f"Database Error: {db_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="เกิดข้อผิดพลาดในการบันทึกข้อมูลลงฐานข้อมูล โปรดตรวจสอบข้อมูลอีกครั้ง"
        )
        
    except Exception as e:
        # เกิด Error อื่นๆ ที่ไม่คาดคิด (เช่น ตัวแปรพัง, Network หลุด)
        await db.rollback()
        print(f"Unexpected Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดภายในเซิร์ฟเวอร์: {str(e)}"
        )