from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi import APIRouter, Request, Response, Depends
from app.database import get_db
from dotenv import load_dotenv
import os
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.models.user import User, Role
from app.models.session import Session
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.responses import RedirectResponse



router = APIRouter(prefix="/auth")
config = Config(".env")
oauth =OAuth(config)

load_dotenv()
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

oauth.register(
    name="google",
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/login")
async def login(request:Request):
    redirect_uri = "http://127.0.0.1:8000/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def callback( db: Annotated[AsyncSession, Depends(get_db)], request:Request,response:Response):
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

    response = RedirectResponse(url="/auth/protected")
    response.set_cookie(
        key="session_id",
        value=str(session.session_id),
        httponly=True,
        samesite="lax",
        secure=False,  # ควรตั้งเป็น True ใน production
        max_age=60 * 60 * 24 * 7  # 7 วัน
    )
    return {"user_info": user_info}

def get_current_user(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> User | None:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.user_id == session.user_id).first()
    return user

    
@router.get("/protected")
async def protected(user=Depends(get_current_user)):
    return{
        "message": "You are logged in",
        "user": user
    }