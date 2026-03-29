from sqlmodel import SQLModel, Field

class Degree(SQLModel, table=True):
    degree_id: str | None = Field(default=None, primary_key=True, max_length=6)
    degree_name_th: str = Field(max_length=500)
    degree_name_en: str = Field(max_length=500)
    __tablename__ = "degrees"