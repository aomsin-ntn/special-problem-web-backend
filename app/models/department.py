from sqlmodel import SQLModel,Field

class Department(SQLModel, table=True):
    department_id: str | None = Field(default=None, primary_key=True, max_length=2)
    department_name_th: str = Field(max_length=255)
    department_name_en: str = Field(max_length=255)
    faculty_id: str = Field(foreign_key="faculties.faculty_id", max_length=2)
    __tablename__ = "departments"