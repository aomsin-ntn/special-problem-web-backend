from sqlmodel import SQLModel,Field


class ProjectAdvisor(SQLModel, table=True):
    project_id: str | None = Field(default=None, primary_key=True, max_length=10, foreign_key="projects.project_id")
    advisor_id: str = Field(primary_key=True, max_length=10, foreign_key="advisors.advisor_id")
    advisor_order: int = Field(default=0)
    __tablename__ = "project_advisors"