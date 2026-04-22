from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from app.models.user import User

class Session(SQLModel, table=True):
    session_id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.user_id")
    created_at:datetime = Field(default_factory=datetime.utcnow)
    expires_at:datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=1))
    __tablename__ = "sessions"