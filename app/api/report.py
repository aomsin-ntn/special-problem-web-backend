from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.authentication import require_role
from app.database import get_db
from app.models.session import Session
from app.models.user import Role, User
from app.schemas.root_schema import GetProjectRequestParams
from app.services.project_services import ProjectServices
from typing import Annotated

from app.services.spell_services import SpellServices

router = APIRouter(prefix="/report")

@router.get("/projects")
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

@router.get("/dictionary")
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
        result = await SpellServices.get_dictionary_report(db, table_type, page, limit, sorted_by, order)
        return result
    except Exception as e:
        db.rollback()
        print(f"Error fetching dictionary: {e}")
        raise HTTPException(status_code=500, detail="ไม่สามารถดึงข้อมูลรายงานได้")
    
@router.post("/create_custom_word")
async def create_custom_word(
    db: Annotated[Session, Depends(get_db)],
    cus_word: str,
    authorized_user: User = Depends(require_role([Role.STAFF]))
):
    try:
        custom_word = await SpellServices.save_custom_word(db, cus_word)
        return custom_word
    except Exception as e:
        db.rollback()
        print(f"Error creating custom word: {e}")
        raise HTTPException(status_code=500, detail="ไม่สามารถสร้างคำเฉพาะทางได้")