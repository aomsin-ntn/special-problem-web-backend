from sqlmodel import SQLModel,Field
from app.models.degree import Degree
from enum import Enum

class Role(str,Enum):
    STUDENT = "student"
    STAFF = "staff"
    PROFESSOR = "professor"

class User(SQLModel, table=True):
    user_id: str | None = Field(default=None, primary_key=True, max_length=10)
    student_id: str = Field(max_length=8, unique=True)
    user_name_th: str = Field(max_length=150)
    user_name_en: str = Field(max_length=150)
    degree_id: str = Field(max_length=6, foreign_key="degrees.degree_id")
    role: Role = Field(sa_column=Field(default=Role.STUDENT, nullable=False))
    email: str = Field(max_length=255, unique=True)
    password_hash: str = Field(max_length=255)
    __tablename__ = "users"