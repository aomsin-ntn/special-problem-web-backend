from sqlmodel import SQLModel,Field
from app.models.correction_dictionary import CorrectionDictionary

class IncorrectWord(SQLModel, table=True):
    word_id: str | None = Field(default=None, primary_key=True, max_length=10)
    word_dic_id: str = Field(max_length=10, foreign_key="correction_dictionary.word_dic_id")
    correct_word: str = Field(max_length=50)
    count: int = Field(default=0)
    __tablename__ = "incorrect_words"