from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class StudentInput(BaseModel):
    student_id: str
    student_name_th: str
    student_name_en: str

class KeywordInput(BaseModel):
    keyword_id: Optional[UUID] = None
    keyword_text_th: str
    keyword_text_en: str

class FileInfoInput(BaseModel):
    file_path: str
    save_name: str
    thumbnail_path: str

class DegreeInput(BaseModel):
    degree_id: Optional[UUID] = None
    degree_name_th: str
    degree_name_en: str

class DepartmentInput(BaseModel):
    department_id: Optional[UUID] = None
    department_name_th: str
    department_name_en: str

class FacultyInput(BaseModel):
    faculty_id: Optional[UUID] = None
    faculty_name_th: str
    faculty_name_en: str

class AdvisorInput(BaseModel):
    advisor_id: Optional[UUID] = None
    advisor_name_th: str
    advisor_name_en: str

class ProjectSubmitRequest(BaseModel):
    title_th: Optional[str] = None
    title_en: str
    abstract_th: Optional[str] = None
    abstract_en: str
    academic_year_be: Optional[str] = None
    academic_year_ce: str
    
    degree: DegreeInput
    department: DepartmentInput
    faculty: FacultyInput
    advisors: List[AdvisorInput]
    students: List[StudentInput]
    keywords: List[KeywordInput]
    file_info: FileInfoInput

class ProjectSaveRequest(BaseModel): # สร้าง Schema ใหม่คลุมอีกชั้น
    data: ProjectSubmitRequest
    old_data: Optional[ProjectSubmitRequest] = None