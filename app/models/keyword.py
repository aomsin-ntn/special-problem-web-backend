from sqlmodel import SQLModel,Field
from uuid import UUID, uuid4

class Keyword(SQLModel, table=True):
    keyword_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    keyword_text_th: str = Field(max_length=100)
    keyword_text_en: str = Field(max_length=100)
    __tablename__ = "keywords"