from fastapi import APIRouter, Depends
from typing import Annotated
from sqlmodel import Session
from app.database import get_db
from app.services.project_services import ProjectServices

router = APIRouter(prefix="/master")

@router.get("/faculty")
async def get_master_faculty(
    db: Annotated[Session, Depends(get_db)]
):
    faculty = await ProjectServices.get_master_faculties(db)
    return faculty

@router.get("/department")
async def get_master_departments(
    db: Annotated[Session, Depends(get_db)]
):
    departments = await ProjectServices.get_master_departments(db)
    return departments

@router.get("/degree")
async def get_master_degrees(
    db: Annotated[Session, Depends(get_db)]
):
    degrees = await ProjectServices.get_master_degrees(db)
    return degrees

@router.get("/advisor")
async def get_master_advisors(
    db: Annotated[Session, Depends(get_db)]
):
    advisors = await ProjectServices.get_master_advisors(db)
    return advisors