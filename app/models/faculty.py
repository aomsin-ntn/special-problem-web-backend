from sqlmodel import SQLModel,Field

class Faculty(SQLModel, table=True):
    faculty_id: str | None = Field(default=None, primary_key=True, max_length=2)
    faculty_name_th: str = Field(max_length=255)
    faculty_name_en: str = Field(max_length=255)
    __tablename__ = "faculties"