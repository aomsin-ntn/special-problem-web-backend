from sqlalchemy import Column, ForeignKey
from sqlmodel import SQLModel,Field
from app.models.user import User
from app.models.project import Project
from uuid import UUID, uuid4

class ProjectAuthor(SQLModel, table=True):
    project_id: UUID = Field(sa_column=Column(ForeignKey("projects.project_id", ondelete="CASCADE"),primary_key=True))
    user_id: UUID = Field(default_factory=uuid4, primary_key=True, foreign_key="users.user_id")
    author_order: int = Field(default=0)
    __tablename__ = "project_authors"