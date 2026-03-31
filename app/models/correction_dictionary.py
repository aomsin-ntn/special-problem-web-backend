from sqlmodel import SQLModel,Field,Column,ARRAY,String
from typing import List
from datetime import datetime
from uuid import UUID, uuid4

class CorrectionDictionary(SQLModel, table=True):
    word_dic_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    incorrect_word: str = Field(max_length=50)
    correct_word_list: List[str] | None = Field(default=None,sa_column=Column(ARRAY(String)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    count: int = Field(default=0)
    __tablename__ = "correction_dictionary"