from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, Response, Depends
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError 
from typing import Annotated, List, Union
from app.models.user import User, Role
from app.models.session import Session
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from urllib.parse import quote
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.config import settings
from app.services.user_services import UserServices
from app.schemas.auth_schema import FirstLoginCreateUserRequest

# --- 1. CONFIG & OAUTH REGISTRATION ---
router = APIRouter(prefix="/auth")
oauth = OAuth()
signup_serializer = URLSafeTimedSerializer(settings.google_client_secret)
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


SIGNUP_TOKEN_SALT = "first-login-signup"
SIGNUP_TOKEN_MAX_AGE_SECONDS = 60 * 30


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
    
def require_role(allowed_roles: Union[Role, List[Role]]):
    # ตรวจสอบว่าถ้าส่งมาเป็น Role เดียว ให้เปลี่ยนเป็น List เพื่อใช้เช็ค 'in' ได้
    if isinstance(allowed_roles, Role):
        allowed_roles = [allowed_roles]

    def role_verifier(current_user: User = Depends(get_current_user)):
        # เช็คว่า Role ของ user อยู่ในกลุ่มที่อนุญาตหรือไม่
        if current_user.role not in allowed_roles:
            role_names = [r.value for r in allowed_roles]
            raise HTTPException(
                status_code=403,
                detail=f"เฉพาะกลุ่มผู้ใช้ {role_names} เท่านั้นที่สามารถเข้าถึงได้"
            )
        return current_user
    
    return role_verifier

# --- 2. GOOGLE OAUTH FLOW ---
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
        user_email = user_info.get("email")
        
        user = db.query(User).filter(User.email == user_email).first()
        frontend_url = "http://localhost:5173/"

        local_part = user_email.split('@')[0]

        if not user or user.last_login_at is None:
            signup_token = signup_serializer.dumps({"email": user_email}, salt=SIGNUP_TOKEN_SALT)

            if local_part.isdigit():
                target_url = f"{frontend_url}first-login/student?token={signup_token}"
            else:
                target_url = f"{frontend_url}first-login/staff?token={signup_token}"
                
            return RedirectResponse(url=target_url)

        
        session = Session(
            session_id=uuid4(),
            user_id=user.user_id,
            expires_at=datetime.utcnow() + timedelta(days=7)  # กำหนดเวลาหมดอายุของ session
        )
        user.last_login_at = datetime.utcnow() # อัปเดตเวลาล่าสุดที่ผู้ใช้ล็อกอิน
        db.add(user)  # บันทึกการอัปเดตเวลาล็อกอิน
        db.add(session)
        db.commit()

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


# --- 3. FIRST LOGIN / ONBOARDING ---
@router.post("/first-login/complete")
async def complete_first_login(
    payload: FirstLoginCreateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        token_data = signup_serializer.loads(
            payload.token,
            salt=SIGNUP_TOKEN_SALT,
            max_age=SIGNUP_TOKEN_MAX_AGE_SECONDS,
        )
        email = token_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid signup token")

        user = db.query(User).filter(User.email == email).first()

        if payload.student_id:
            duplicate_id = db.query(User).filter(User.student_id == payload.student_id).first()
            if duplicate_id:
                raise HTTPException(status_code=409, detail="Student ID already exists")

        local_part = email.split('@')[0]
        if local_part.isdigit():
            user_role = Role.STUDENT
        else:            
            user_role = Role.STAFF

        if not user:
            user = User(
                user_id=uuid4(),
                email=email,
                role=user_role
            )
            db.add(user)

        user.student_id = payload.student_id or user.student_id
        user.user_name_th = payload.user_name_th
        user.user_name_en = payload.user_name_en
        user.degree_id = payload.degree_id or user.degree_id
        user.last_login_at = datetime.utcnow()

        db.flush()

        new_session = Session(
            session_id=uuid4(),
            user_id=user.user_id,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(new_session)
        db.commit()

        response_obj = JSONResponse(content={"message": "First login completed successfully"})
        response_obj.set_cookie(
            key="session_id",
            value=str(new_session.session_id),
            httponly=True,
            samesite="none",
            secure=True,
            max_age=60 * 60 * 24 * 7,
            path="/",
        )
        return response_obj
    
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=400, detail="Signup token expired or invalid")
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred while creating user")
    
@router.get("/first-login/me")
async def get_initial_data(
    token: str, # รับ Token จาก URL parameter
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. แกะ Token ดูว่าเป็นใคร
        token_data = signup_serializer.loads(token, salt=SIGNUP_TOKEN_SALT, max_age=SIGNUP_TOKEN_MAX_AGE_SECONDS)
        email = token_data.get("email")

        # 2. ไปดูใน DB ว่ามีข้อมูลเดิมที่ Admin ใส่ไว้ไหม
        user = db.query(User).filter(User.email == email).first()

        # 3. ส่งข้อมูลกลับไปให้ Frontend (ถ้าไม่มีก็ส่งค่าว่าง)
        return {
            "email": email,
            "user_name_th": user.user_name_th if user else "",
            "user_name_en": user.user_name_en if user else "",
            "student_id": user.student_id if user else "",
            "role": user.role if user else "STUDENT" # หรือใช้ logic @ ที่เราคุยกัน
        }
    except:
        raise HTTPException(status_code=400, detail="Token invalid")


# --- 4. SESSION & ACCESS CONTROL ---
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


# --- 5. USER PROFILE ---
@router.get("/me")
async def get_profile(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)   
    ):
    try:
        result = UserServices.get_user_profile(db=db, user_id=current_user.user_id)

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
    
