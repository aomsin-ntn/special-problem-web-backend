from sqlmodel import SQLModel, Field
from datetime import datetime

class ProjectFile(SQLModel, table=True):
    file_id: str | None = Field(default=None, primary_key=True, max_length=10)
    file_name: str = Field(max_length=255)
    file_path: str = Field(max_length=255)
    thumbnail_path: str = Field(default=None, max_length=255)
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    __tablename__ = "project_files"