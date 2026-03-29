from sqlmodel import SQLModel,Field,Column,Text
from app.models.degree import Degree
from app.models.user import User
from datetime import datetime
from app.models.project_file import ProjectFile


class Project(SQLModel, table=True):
    project_id: str | None = Field(default=None, primary_key=True, max_length=10)
    title_th: str = Field(max_length=500)
    title_en: str = Field(max_length=500)
    abstract_th: str = Field(sa_column=Column(Text))
    abstract_en: str = Field(sa_column=Column(Text))
    academic_year: str = Field(max_length=4)
    degree_id: str = Field(max_length=6, foreign_key="degrees.degree_id")
    create_by: str = Field(max_length=10, foreign_key="users.user_id")
    create_date: datetime = Field(default_factory=datetime.utcnow)
    update_by: str = Field(max_length=10, foreign_key="users.user_id")
    update_time: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    file_id: str = Field(max_length=10, foreign_key="project_files.file_id")
    download_count: int = Field(default=0)
    __tablename__ = "projects"