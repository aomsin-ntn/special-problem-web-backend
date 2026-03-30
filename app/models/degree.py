from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class Degree(SQLModel, table=True):
    degree_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    degree_name_th: str = Field(max_length=500)
    degree_name_en: str = Field(max_length=500)
    __tablename__ = "degrees"