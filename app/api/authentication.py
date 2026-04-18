from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi import APIRouter, Request, Response, Depends
from app.database import get_db
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError 
from typing import Annotated
from app.models.user import User, Role
from app.models.session import Session
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from uuid import UUID
from app.services.project_services import ProjectServices
from app.repository.user_repository import UserRepository
from app.config import settings

router = APIRouter(prefix="/auth")
oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/login")
async def login(request: Request):
    try:
        redirect_url = "http://127.0.0.1:8000/auth/callback"
        return await oauth.google.authorize_redirect(request, redirect_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login Error: {str(e)}")

@router.get("/callback")
async def callback(db: Annotated[AsyncSession, Depends(get_db)], request: Request, response: Response):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        print("User Info:", user_info)
        user_email = user_info.get("email")
        
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(
                user_id=uuid4(),
                student_id=user_email.split("@")[0],  # ใช้ส่วนก่อน @ เป็น student_id ชั่วคราว
                role=Role.STUDENT,
                email=user_email,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        session = Session(
            session_id=uuid4(),
            user_id=user.user_id,
            expires_at=datetime.utcnow() + timedelta(days=7)  # กำหนดเวลาหมดอายุของ session
        )
        db.add(session)
        db.commit()

        frontend_url = "http://localhost:5173/" 
        response = RedirectResponse(url=frontend_url)
        response.set_cookie(
            key="session_id",
            value=str(session.session_id),
            httponly=True,
            samesite="none",
            secure=True,  # ควรตั้งเป็น True ใน production
            max_age=60 * 60 * 24 * 7,  # 7 วัน
            path="/"
        )
        return response
    except SQLAlchemyError as db_error:
        db.rollback()  # คืนค่ากรณีมี error
        raise HTTPException(status_code=500, detail="Database error occurred during callback")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Callback Error: {str(e)}")

async def get_current_user(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> User | None:
    try:
        print(request.cookies)
        session_id = request.cookies.get("session_id")
        if not session_id:
            print("ล็อกอินไม่สำเร็จ")
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if not session or session.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        user = db.query(User).filter(User.user_id == session.user_id).first()
        return user
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database connection error")

@router.get("/protected")
async def protected(user=Depends(get_current_user)):
    return {
        "message": "You are logged in",
        "user": user
    }

@router.post("/logout")
async def logout(request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        session_id = request.cookies.get("session_id")
        if session_id:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
                
        response.delete_cookie(key="session_id")
        return {"message": "Logged out successfully"}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred during logout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout Error: {str(e)}")

@router.get("/me")
async def get_profile(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)   
    ):
    try:
        result = UserRepository.get_user_profile(db=db, user_id=current_user.user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลผู้ใช้งาน")

        user, degree, department, faculty = result

        return {
            "studentId": user.student_id,
            "studentName": user.user_name_th or user.user_name_en,
            "degree": degree.degree_name_th if degree else "-",
            "department": department.department_name_th if department else "-",
            "faculty": faculty.faculty_name_th if faculty else "-",
            "email": user.email
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error occurred while fetching profile")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")