"""
All API Routes
"""
from fastapi import APIRouter, Depends, UploadFile, File, Query
from app.schemas.root_schema import RootResponse, ItemResponse, ItemRequest
from fastapi.responses import JSONResponse
from app.services.upload_services import UploadServices
from typing import Annotated
from sqlmodel import Session
from app.database import get_db
from app.services.project_services import ProjectServices
from app.schemas.root_schema import GetProjectRequestParams
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(prefix="/project")

@router.post("/upload")
async def upload(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    service: UploadServices = Depends(),
    page: list[int] = Query([1], description="Page numbers for pagination")
):
    return await service.save_file(file, page=page, session=db)

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
async def get_most_downloaded_projects(db: Annotated[Session, Depends(get_db)]):
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

@router.get("/master")
async def get_master_data(
    db: Annotated[Session, Depends(get_db)]
):
    master_data = await ProjectServices.get_master_data(db)
    return master_data