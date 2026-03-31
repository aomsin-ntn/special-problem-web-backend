from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4

class ProjectFile(SQLModel, table=True):
    file_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    file_name: str = Field(max_length=255)
    file_path: str = Field(max_length=255)
    thumbnail_path: str = Field(default=None, max_length=255)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    __tablename__ = "project_files"