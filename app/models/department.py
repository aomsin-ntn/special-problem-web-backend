from sqlmodel import SQLModel,Field
from uuid import UUID, uuid4

class Department(SQLModel, table=True):
    department_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    department_name_th: str = Field(max_length=255)
    department_name_en: str = Field(max_length=255)
    faculty_id: UUID = Field(foreign_key="faculties.faculty_id")
    __tablename__ = "departments"