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
from app.schemas.project_schema import ProjectSubmitRequest  # <--- อย่าลืมนำเข้า Schema ที่สร้างไว้

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
    pages: list[int] = Query([1], description="Page numbers for OCR",),
    user: User = Depends(get_current_user),
):
    return await service.handle_upload(file, pages=pages, db=db, current_user=user)

# ----------------------------------------------------
# 🚨 แก้ไข Path ให้ไม่ซ้ำกัน (ดาวน์โหลดตัวไฟล์ PDF)
# ----------------------------------------------------
@router.get("/download/file/{project_id}")
async def download_projectfile(
    db: Annotated[Session, Depends(get_db)],
    project_id: UUID,
):
    projectfile = await ProjectServices.download_projectfile(db, project_id)

    return FileResponse(
        path=projectfile.file_path,
        filename=projectfile.file_name,
        media_type="application/pdf"
    )

@router.patch("/delete")
async def delete_project(
    db: Annotated[Session, Depends(get_db)],
    project_id: UUID,
):
    result = await ProjectServices.delete_project(db, project_id)
    if result:
        return JSONResponse(content={"message": "Project deleted successfully"})
    else:
        return JSONResponse(content={"message": "Project not found"}, status_code=404)

@router.get("/")
async def get_projects(
    db: Annotated[Session, Depends(get_db)],
    request: Annotated[GetProjectRequestParams, Query()]
):
    projects = await ProjectServices.get_projects(db, request)
    return projects

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
    details = await ProjectServices.get_project_details(db, project_id)
    return details

@router.get("/get_faculty")
async def get_faculty(
    db: Annotated[Session, Depends(get_db)]
):
    faculty = await ProjectServices.get_faculty(db)
    return faculty


@router.post("/save")
async def save_project(
    data: ProjectSubmitRequest, 
    db: Annotated[Session, Depends(get_db)], 
    current_user: User = Depends(get_current_user)
):
    # 1. สร้าง ProjectFile จาก data.file_info ที่หน้าบ้านส่งกลับมา
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
        # เช็คข้ามถ้าหน้าบ้านไม่ได้ส่งรหัสนักศึกษามา
        if not student_data.student_id:
            continue

        user = await ProjectServices.get_user_by_student_id(db, student_data.student_id)
        if user:
            user.user_name_th = student_data.student_name_th
            user.user_name_en = student_data.student_name_en
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

    # 5. จัดการ Keywords (โค้ดดึงเทียบคำเดิม / สร้างคำใหม่)
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