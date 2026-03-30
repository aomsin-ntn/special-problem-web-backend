from sqlmodel import SQLModel,Field
from uuid import UUID, uuid4

class ProjectKeyword(SQLModel, table=True):
    project_id: UUID | None = Field(default_factory=uuid4, primary_key=True, foreign_key="projects.project_id")
    keyword_id: UUID = Field(default_factory=uuid4, primary_key=True, foreign_key="keywords.keyword_id")
    keyword_order: int = Field(default=0)
    __tablename__ = "project_keywords"