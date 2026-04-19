from app.models import department
from app.repository.project_repository import ProjectRepository
from sqlmodel import Session
from fastapi import HTTPException
from app.schemas.root_schema import GetProjectRequestParams
from uuid import UUID
from app.repository.user_repository import UserRepository
import difflib
import re

class ProjectServices:
    @staticmethod
    async def get_projects(db: Session, request: GetProjectRequestParams):
        projects = await ProjectRepository.get_projects(db, request)
        return projects
    
    @staticmethod
    async def get_error_dict(db: Session):
        error_dict = await ProjectRepository.get_error_dict(db)
        return error_dict
    
    @staticmethod
    async def get_custom_dict(db: Session):
        custom_dict = await ProjectRepository.get_custom_dict(db)
        return custom_dict

    @staticmethod
    async def delete_project(db: Session, project_id: int, user_id: UUID):
        has_permission = await ProjectServices.check_edit_permission(db, project_id, user_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="คุณไม่มีสิทธิ์ลบข้อมูลนี้")
        return await ProjectRepository.delete_project(db, project_id)

    @staticmethod
    async def create_project(db: Session, project_data):
        new_project = await ProjectRepository.create_project(db, project_data)
        return new_project

    @staticmethod
    async def download_projectfile(db:Session,project_id):
        projectfile = await ProjectRepository.download_projectfile(db,project_id)
        if not projectfile:
            raise HTTPException(status_code=404, detail="Project not found")
        return projectfile

    @staticmethod
    async def get_faculty(db: Session):
        faculty = await ProjectRepository.get_faculty(db)
        return faculty

    @staticmethod
    async def get_master_faculties(db:Session):
        faculty = await ProjectRepository.get_master_faculties(db)
        return faculty

    @staticmethod
    async def get_master_departments(db:Session):
        departments = await ProjectRepository.get_master_departments(db)
        return departments

    @staticmethod
    async def get_master_advisors(db:Session):
        advisors = await ProjectRepository.get_master_advisors(db)
        return advisors

    @staticmethod
    async def get_master_degrees(db:Session):
        degrees = await ProjectRepository.get_master_degrees(db)
        return degrees

    @staticmethod
    async def get_user_by_student_id(db:Session, student_id:str):
        user = await UserRepository.get_user_by_student_id(db,student_id)
        return user
    
    @staticmethod
    async def create_project_keyword(db: Session, project_keyword_data):
        new_project_keyword = await ProjectRepository.create_project_keyword(db, project_keyword_data)
        return new_project_keyword
    
    @staticmethod
    async def create_keyword(db: Session, keyword_data):
        new_keyword = await ProjectRepository.create_keyword(db, keyword_data)
        return new_keyword
    
    @staticmethod
    async def create_project_advisor(db: Session, project_advisor_data):
        new_project_advisor = await ProjectRepository.create_project_advisor(db, project_advisor_data)
        return new_project_advisor
    
    @staticmethod
    async def get_keywords(db: Session):
        keywords = await ProjectRepository.get_keywords(db)
        return keywords
    
    @staticmethod
    async def create_project_author(db: Session, project_author_data):
        new_project_author = await ProjectRepository.create_project_author(db, project_author_data)
        return new_project_author
    
    @staticmethod
    async def create_project_file(db: Session, project_file_data):
        new_project_file = await ProjectRepository.create_project_file(db, project_file_data)
        return new_project_file

    @staticmethod
    async def get_project_details(db: Session, project_id: int):
        details = await ProjectRepository.get_project_details(db, project_id)
        result = {}
        for project, user, keyword, faculty, degree, department, project_file, advisor in details:
            pid = project.project_id

            if pid not in result:
                project_dict = project.dict()
                project_dict["authors"] = []
                project_dict["keywords"] = []
                project_dict["faculty"] = faculty.dict()
                project_dict["degree"] = degree.dict()
                project_dict["department"] = department.dict()
                project_dict["project_file"] = project_file.dict()
                project_dict["advisors"] = []
                result[pid] = project_dict

            if user.user_id not in [u["user_id"] for u in result[pid]["authors"]]:
                result[pid]["authors"].append(user.model_dump())

            if advisor.advisor_id not in [a["advisor_id"] for a in result[pid]["advisors"]]:
                result[pid]["advisors"].append(advisor.model_dump())

            if keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())

        final_result = list(result.values())
        return final_result

    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        projects = await ProjectRepository.get_most_downloaded_projects(db)
        result = {}
        for project, keyword, department in projects:
            pid = project.project_id

            if pid not in result:
                project_dict = project.dict()
                project_dict["keywords"] = []
                project_dict["departments"] = []
                result[pid] = project_dict

            if department.department_id not in [d["department_id"] for d in result[pid]["departments"]]:
                result[pid]["departments"].append(department.model_dump())

            if keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())
            

        final_result = list(result.values())
        return final_result

    def find_match(target_th, target_en, items, th_attr, en_attr):
        def normalize(text):
            if not text:
                return ""

            text = text.lower()

            # 🔥 OCR fix
            text = text.replace("0", "o")
            text = text.replace("1", "l")
            text = text.replace("5", "s")

            text = re.sub(r'\s+', '', text)
            return text

        target = normalize(target_th) or normalize(target_en)

        if not target:
            return None

        mapping = {}

        for item in items:
            th_val = normalize(getattr(item, th_attr, ""))
            en_val = normalize(getattr(item, en_attr, ""))

            if th_val:
                mapping[th_val] = item
            if en_val:
                mapping[en_val] = item

        candidates = list(mapping.keys())

        for key in candidates:
            if target in key or key in target:
                return mapping[key]

        match = difflib.get_close_matches(target, candidates, n=1, cutoff=0.5)

        if match:
            return mapping[match[0]]

        return None
    
    @staticmethod
    async def check_edit_permission(db: Session, project_id: UUID, user_id: UUID) -> bool:
        is_owner = await ProjectRepository.is_project_owner(db, project_id, user_id)
        return is_owner

    @staticmethod
    async def get_project_details_check_permission(db: Session, project_id: int, user_id: UUID):
        has_permission = await ProjectServices.check_edit_permission(db, project_id, user_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="คุณไม่มีสิทธิ์เข้าถึงข้อมูลนี้")
        return await ProjectServices.get_project_details(db, project_id)