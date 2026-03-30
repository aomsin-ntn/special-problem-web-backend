from sqlmodel import SQLModel,Field
from uuid import UUID, uuid4

class Faculty(SQLModel, table=True):
    faculty_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    faculty_name_th: str = Field(max_length=255)
    faculty_name_en: str = Field(max_length=255)
    __tablename__ = "faculties"