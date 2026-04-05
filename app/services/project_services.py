from app.repository.project_repository import ProjectRepository
from sqlmodel import Session
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
    async def delete_project(db: Session, project_id: int):
        project = await ProjectRepository.delete_project(db, project_id)
        if project:
            return True
        return False

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
                project_dict["advisor"] = advisor.dict()
                result[pid] = project_dict

            if user.user_id not in [u["user_id"] for u in result[pid]["authors"]]:
                result[pid]["authors"].append(user.model_dump())

            if keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())

        final_result = list(result.values())
        return final_result

    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        projects = await ProjectRepository.get_most_downloaded_projects(db)
        result = {}
        for project, keyword in projects:
            pid = project.project_id

            if pid not in result:
                project_dict = project.dict()
                project_dict["keywords"] = []
                result[pid] = project_dict

            result[pid]["keywords"].append(keyword.dict())

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
