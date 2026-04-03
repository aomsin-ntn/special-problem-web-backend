"""
All API Routes
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query
from app.schemas.root_schema import RootResponse, ItemResponse, ItemRequest
from fastapi.responses import JSONResponse,  FileResponse
from app.services.upload_services import UploadServices
from typing import Annotated
from sqlmodel import Session
from app.database import get_db
from app.services.project_services import ProjectServices
from app.schemas.root_schema import GetProjectRequestParams
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.api.authentication import get_current_user

router = APIRouter(prefix="/project")

@router.post("/upload")
async def handle_upload(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    service: UploadServices = Depends(),
    pages: list[int] = Query([1], description="Page numbers for OCR",)
):
    return await service.handle_upload(file, pages=pages, db=db)

@router.get("/download/{project_id}")
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

@router.get("/download/{project_id}")
async def download_project(
    db: Annotated[Session, Depends(get_db)],
    project_id: UUID
):  
    project = await ProjectServices.download_project(db, project_id)
    return project