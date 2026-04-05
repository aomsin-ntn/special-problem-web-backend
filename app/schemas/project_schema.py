from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class StudentInput(BaseModel):
    student_id: str
    student_name_th: str
    student_name_en: str

class KeywordInput(BaseModel):
    keyword_text_th: str
    keyword_text_en: str

class FileInfoInput(BaseModel):
    file_path: str
    save_name: str
    thumbnail_path: str

class ProjectSubmitRequest(BaseModel):
    title_th: str
    title_en: str
    abstract_th: str
    abstract_en: str
    academic_year: str
    degree_id: UUID
    advisor_id: UUID
    students: List[StudentInput]
    keywords: List[KeywordInput]
    file_info: FileInfoInput