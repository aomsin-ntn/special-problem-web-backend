from sqlmodel import SQLModel,Field

class Advisor(SQLModel, table=True):
    advisor_id: str | None = Field(default=None, primary_key=True, max_length=10)
    advisor_name_th: str = Field(max_length=255)
    advisor_name_en: str = Field(max_length=255)
    __tablename__ = "advisors"