from sqlmodel import SQLModel,Field
from uuid import UUID, uuid4

class Advisor(SQLModel, table=True):
    advisor_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    advisor_name_th: str = Field(max_length=255)
    advisor_name_en: str = Field(max_length=255)
    __tablename__ = "advisors"