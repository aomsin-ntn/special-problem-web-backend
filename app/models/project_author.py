from sqlmodel import SQLModel,Field
from app.models.user import User
from app.models.project import Project

class ProjectAuthor(SQLModel, table=True):
    project_id: str | None = Field(default=None, primary_key=True, max_length=10, foreign_key="projects.project_id")
    user_id: str = Field(primary_key=True, max_length=10, foreign_key="users.user_id")
    author_order: int = Field(default=0)
    __tablename__ = "project_authors"