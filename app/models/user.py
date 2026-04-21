from datetime import datetime

from sqlmodel import SQLModel,Field
from app.models.degree import Degree
from enum import Enum
from uuid import UUID, uuid4

class Role(str,Enum):
    STUDENT = "student"
    STAFF = "staff"

class User(SQLModel, table=True):
    user_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    student_id: str | None = Field(max_length=8, unique=True)
    user_name_th: str | None = Field(max_length=150)
    user_name_en: str | None = Field(max_length=150)
    degree_id: UUID | None = Field(foreign_key="degrees.degree_id")
    role: Role = Field(sa_column=Field(default=Role.STUDENT, nullable=False))
    email: str = Field(max_length=255, unique=True)
    last_login_at: datetime | None = Field(default=datetime.utcnow)
    __tablename__ = "users"