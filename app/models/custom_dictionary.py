from sqlmodel import SQLModel,Field,Column,ARRAY,String
from typing import List
from datetime import datetime
from uuid import UUID, uuid4

class CustomDictionary(SQLModel, table=True):
    cus_word_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    cus_word: str = Field(max_length=50)
    __tablename__ = "custom_dictionary"