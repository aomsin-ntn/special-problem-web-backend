from sqlmodel import SQLModel,Field,Column,ARRAY,String
from typing import List
from datetime import datetime

class CorrectionDictionary(SQLModel, table=True):
    word_dic_id: str | None = Field(default=None, primary_key=True, max_length=10)
    incorrect_word: str = Field(max_length=50)
    correct_word_list: List[str] | None = Field(default=None,sa_column=Column(ARRAY(String)))
    create_date: datetime = Field(default_factory=datetime.utcnow)
    update_date: datetime = Field(default_factory=datetime.utcnow)
    count: int = Field(default=0)
    __tablename__ = "correction_dictionary"