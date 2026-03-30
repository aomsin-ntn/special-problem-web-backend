from sqlmodel import SQLModel,Field
from app.models.correction_dictionary import CorrectionDictionary
from uuid import UUID, uuid4

class IncorrectWord(SQLModel, table=True):
    word_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    word_dic_id: UUID = Field(foreign_key="correction_dictionary.word_dic_id")
    correct_word: str = Field(max_length=50)
    count: int = Field(default=0)
    __tablename__ = "incorrect_words"