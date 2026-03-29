from sqlmodel import SQLModel,Field

class ProjectKeyword(SQLModel, table=True):
    project_id: str | None = Field(default=None, primary_key=True, max_length=10, foreign_key="projects.project_id")
    keyword_id: str = Field(primary_key=True, max_length=10, foreign_key="keywords.keyword_id")
    keyword_order: int = Field(default=0)
    __tablename__ = "project_keywords"