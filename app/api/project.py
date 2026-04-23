"""
All API Routes
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from typing import Annotated
from sqlmodel import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID, uuid4
from datetime import datetime

# Database & Auth
from app.database import get_db
from app.api.authentication import get_current_user
from app.api.authentication import require_role

# Services
from app.services.upload_services import UploadServices
from app.services.project_services import ProjectServices

# Schemas
from app.schemas.root_schema import RootResponse, ItemResponse, ItemRequest, GetProjectRequestParams
from app.schemas.project_schema import ProjectSaveRequest, ProjectSubmitRequest

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

# --- 1. Basic Fetching (Read) ---
@router.get("/search")
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


# --- 2. Create & Update Logic ---
@router.post("/upload")
async def handle_upload(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    service: UploadServices = Depends(),
    pages: list[int] = Query([1]),
    user: User = Depends(get_current_user),
):
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ PDF เท่านั้น")

        result = await service.handle_upload(file, pages=pages, db=db, current_user=user)
        # print(result)  # Debug: แสดงผลลัพธ์ที่ได้จากการประมวลผล

        # เช็คคุณภาพข้อมูลตรงนี้
        ProjectServices.validate_extracted_data(result["form_data"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"OCR/Upload Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}"
        )

@router.post("/save")
async def save_project(
    data: ProjectSaveRequest, 
    db: Annotated[Session, Depends(get_db)], 
    current_user: User = Depends(get_current_user),
    project_service: ProjectServices = Depends() # เรียกใช้ Service
):
    try:
        # โยนภาระไปให้ Service จัดการให้หมด
        result = await project_service.save_project_data(data.data, data.old_data, db, current_user)
        return result

    except SQLAlchemyError as db_error:
        db.rollback() 
        print(f"Database Error: {db_error}")
        raise HTTPException(status_code=500, detail="เกิดข้อผิดพลาดลงฐานข้อมูล")

    except Exception as e:
        db.rollback()
        print(f"Unexpected Error: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")

@router.get("/edit_project/{project_id}")
async def get_project_details_check_permission(
    db: Annotated[Session, Depends(get_db)],
    project_id: UUID,
    current_user: User = Depends(get_current_user)
):
    try:
        details = await ProjectServices.get_project_details_check_permission(db, project_id, current_user.user_id)
        
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

@router.post("/save_update_project_data/{project_id}")
async def save_update_project(
    project_id: UUID,
    data: ProjectSubmitRequest, 
    db: Annotated[Session, Depends(get_db)], 
    current_user: User = Depends(get_current_user),
    project_service: ProjectServices = Depends()
):
    try:
        result = await project_service.save_update_project_data(str(project_id), data, db, current_user)
        return result

    except SQLAlchemyError as db_error:
        db.rollback() 
        print(f"Database Error: {db_error}")
        raise HTTPException(status_code=500, detail="เกิดข้อผิดพลาดลงฐานข้อมูล")

    except Exception as e:
        db.rollback()
        print(f"Unexpected Error: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


# --- 3. Resource Management (File & Deletion) ---
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
    user: User = Depends(get_current_user),
):
    try:
        result = await ProjectServices.delete_project(db, project_id, user.user_id)
        if result:
            return {"message": "ลบโปรเจกต์สำเร็จ"}
        else:
            raise HTTPException(status_code=404, detail="ไม่พบโปรเจกต์นี้ในระบบ")
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="ข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล")
    except Exception as e:
        print(f"Delete Error: {e}")
        raise HTTPException(status_code=500, detail="เกิดข้อผิดพลาดในการลบโปรเจกต์นี้")


# --- 4. Reports & Staff Only (Admin) ---   
@router.get("/report")
async def get_projects_report(
    db: Annotated[Session, Depends(get_db)],
    request: Annotated[GetProjectRequestParams, Query()],
    authorized_user: User = Depends(require_role([Role.STAFF]))
):
    try:
        # ใช้ Logic การดึงข้อมูลเดิมจาก Repository ได้เลย
        projects = await ProjectServices.get_projects(db, request)
        return projects
    except SQLAlchemyError as e:
        print(f"DB Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="ไม่สามารถดึงข้อมูลรายงานโปรเจกต์ได้ในขณะนี้"
        )

@router.get("/report/dictionary")
async def get_dictionary_report_api(
    db: Annotated[Session, Depends(get_db)],
    table_type: str = Query(..., description="incorrect, correction, or custom"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    sorted_by: str = Query(None),
    order: str = Query("desc"),
    authorized_user: User = Depends(require_role([Role.STAFF]))
):
    try:
        result = await ProjectServices.get_dictionary_report(db, table_type, page, limit, sorted_by, order)
        return result
    except Exception as e:
        db.rollback()
        print(f"Error fetching dictionary: {e}")
        raise HTTPException(status_code=500, detail="ไม่สามารถดึงข้อมูลรายงานได้")
    