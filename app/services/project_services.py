from app.repository.project_repository import ProjectRepository
from sqlmodel import Session
from app.schemas.root_schema import GetProjectRequestParams

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

    @staticmethod
    async def get_project_details(db: Session, project_id: int):
        details = await ProjectRepository.get_project_details(db, project_id)
        result = {}
        for project, user, keyword, faculty, degree, department, project_file, advisor, keyword in details:
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

            result[pid]["authors"].append(user.dict())
            result[pid]["keywords"].append(keyword.dict())

        final_result = list(result.values())
        return final_result
