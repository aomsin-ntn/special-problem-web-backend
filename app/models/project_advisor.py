from sqlmodel import ForeignKey, SQLModel,Field
from uuid import UUID, uuid4
from sqlalchemy import Column, ForeignKey


class ProjectAdvisor(SQLModel, table=True):
    project_id: UUID = Field(sa_column=Column(ForeignKey("projects.project_id", ondelete="CASCADE"),primary_key=True))
    advisor_id: UUID = Field(default_factory=uuid4, primary_key=True, foreign_key="advisors.advisor_id")
    advisor_order: int = Field(default=0)
    __tablename__ = "project_advisors"