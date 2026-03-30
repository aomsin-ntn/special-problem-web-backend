from sqlmodel import SQLModel,Field
from uuid import UUID, uuid4


class ProjectAdvisor(SQLModel, table=True):
    project_id: UUID | None = Field(default_factory=uuid4, primary_key=True, foreign_key="projects.project_id")
    advisor_id: UUID = Field(default_factory=uuid4, primary_key=True, foreign_key="advisors.advisor_id")
    advisor_order: int = Field(default=0)
    __tablename__ = "project_advisors"