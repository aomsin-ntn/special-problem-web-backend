from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlmodel import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db
from app.services.project_services import ProjectServices

router = APIRouter(prefix="/master")

@router.get("/faculty")
async def get_master_faculty(
    db: Annotated[Session, Depends(get_db)]
):
    try:
        faculty = await ProjectServices.get_master_faculties(db)
        return faculty
    except SQLAlchemyError as e:
        print(f"DB Error (Faculty): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="เกิดข้อผิดพลาดในการดึงข้อมูลคณะจากฐานข้อมูล"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/department")
async def get_master_departments(
    db: Annotated[Session, Depends(get_db)]
):
    try:
        departments = await ProjectServices.get_master_departments(db)
        return departments
    except SQLAlchemyError as e:
        print(f"DB Error (Department): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="เกิดข้อผิดพลาดในการดึงข้อมูลภาควิชาจากฐานข้อมูล"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/degree")
async def get_master_degrees(
    db: Annotated[Session, Depends(get_db)]
):
    try:
        degrees = await ProjectServices.get_master_degrees(db)
        return degrees
    except SQLAlchemyError as e:
        print(f"DB Error (Degree): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="เกิดข้อผิดพลาดในการดึงข้อมูลระดับปริญญาจากฐานข้อมูล"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/advisor")
async def get_master_advisors(
    db: Annotated[Session, Depends(get_db)]
):
    try:
        advisors = await ProjectServices.get_master_advisors(db)
        return advisors
    except SQLAlchemyError as e:
        print(f"DB Error (Advisor): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="เกิดข้อผิดพลาดในการดึงข้อมูลอาจารย์ที่ปรึกษาจากฐานข้อมูล"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))