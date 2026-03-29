from sqlmodel import SQLModel,Field

class Keyword(SQLModel, table=True):
    keyword_id: str | None = Field(default=None, primary_key=True, max_length=10)
    keyword_text_th: str = Field(max_length=100)
    keyword_text_en: str = Field(max_length=100)
    __tablename__ = "keywords"