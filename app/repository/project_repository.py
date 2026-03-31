from sqlmodel import Session, select,or_
from app.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.project_file import ProjectFile
from app.models.keyword import Keyword
from app.models.project_keyword import ProjectKeyword
from app.models.project_author import ProjectAuthor
from app.models.degree import Degree
from app.models.department import Department
from app.models.advisor import Advisor
from app.models.project_file import ProjectFile
from app.models.project_advisor import ProjectAdvisor
from app.models.degree_department import DegreeDepartment
from app.models.faculty import Faculty
from uuid import UUID
from app.schemas.root_schema import GetProjectRequestParams

class ProjectRepository:
    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        # result = db.query(Project,Keywords).order_by(Project.downloaded_count.desc()).limit(5).all()
        result = db.exec(
            select(Project, Keyword)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id)
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id)
            .order_by(Project.downloaded_count.desc())
            .limit(5)
        ).all()
        return result

    @staticmethod
    async def get_project_details(db: Session, project_id: UUID):
        result = db.exec(
            select(Project, User, Keyword, Faculty,Degree, Department, ProjectFile, Advisor, Keyword)
            .join(ProjectAuthor, Project.project_id == ProjectAuthor.project_id)
            .join(User, ProjectAuthor.user_id == User.user_id)
            .join(Degree, Project.degree_id == Degree.degree_id)
            .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id)
            .join(Department, DegreeDepartment.department_id == Department.department_id)
            .join(Faculty, Department.faculty_id == Faculty.faculty_id)
            .join(ProjectFile, Project.file_id == ProjectFile.file_id)
            .join(ProjectAdvisor, Project.project_id == ProjectAdvisor.project_id)
            .join(Advisor, ProjectAdvisor.advisor_id == Advisor.advisor_id)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id)
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id)
            .where(Project.project_id == project_id, Project.is_active == True)
        ).all()
        return result

    @staticmethod
    async def create_project(db: AsyncSession, project_data: Project):
        db.add(project_data)
        db.commit()
        db.refresh(project_data)
        return project_data

    @staticmethod
    async def create_project_file(db: AsyncSession, project_file: ProjectFile):
        db.add(project_file)
        db.commit()
        db.refresh(project_file)
        return project_file

    @staticmethod
    async def delete_project(db: Session, project_id: int):
        project = db.exec(
            select(Project).where(Project.project_id == project_id)
        ).first()
        print(f"Project query result: {project}")
        if project:
            print(f"Project found: {project.project_id}")
            project.is_active = False  # Mark the project as inactive instead of deleting it
            db.add(project)  # Add the project back to the session to mark it as dirty
            db.commit()
            db.refresh(project) 
        return project

    @staticmethod
    async def get_projects(db: Session, request: GetProjectRequestParams):
        filters = []
        if request.search:
            filters.append(
                or_ (
                    Project.title_en.ilike(f"%{request.search}%"),
                    Project.title_th.ilike(f"%{request.search}%"),
                    User.user_name_th.ilike(f"%{request.search}%"),
                    User.user_name_en.ilike(f"%{request.search}%"),
                    User.student_id.ilike(f"%{request.search}%"),
                    Advisor.advisor_name_th.ilike(f"%{request.search}%"),
                    Advisor.advisor_name_en.ilike(f"%{request.search}%"),
                    Keyword.keyword_text_th.ilike(f"%{request.search}%"),
                    Keyword.keyword_text_en.ilike(f"%{request.search}%")
                )
            )

        if request.department:
            filters.append(Department.department_name_en.in_(request.department))
        if request.year:
            filters.append(Project.academic_year.in_(request.year))
        if request.sorted_by:
            if request.sorted_by == "downloaded_count":
                if request.order == "asc":
                    order_by = Project.downloaded_count.asc()
                else:
                    order_by = Project.downloaded_count.desc()
            elif request.sorted_by == "created_at":
                if request.order == "asc":
                    order_by = Project.created_at.asc()
                else:
                    order_by = Project.created_at.desc()
        else:
            order_by = Project.created_at.desc()  # Default sorting

        projects = db.exec(
            select(Project, User, Advisor, Keyword)
            .join(ProjectAuthor, Project.project_id == ProjectAuthor.project_id)
            .join(User, ProjectAuthor.user_id == User.user_id)
            .join(ProjectAdvisor, Project.project_id == ProjectAdvisor.project_id)
            .join(Advisor, ProjectAdvisor.advisor_id == Advisor.advisor_id)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id)
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id)
            .where(*filters, Project.is_active == True)
            .order_by(order_by)
            .offset((request.page - 1) * request.limit)
            .limit(request.limit)
        ).all()

        result = {}
        for project, user, advisor, keyword in projects:
            pid = project.project_id

            if pid not in result:
                result[pid] = {
                    "project": project.model_dump(),
                    "users": [],
                    "advisors": [],
                    "keywords": []
                }

            # ✅ กันซ้ำใน list
            if user.user_id not in [u["user_id"] for u in result[pid]["users"]]:
                result[pid]["users"].append(user.model_dump())

            if advisor.advisor_id not in [a["advisor_id"] for a in result[pid]["advisors"]]:
                result[pid]["advisors"].append(advisor.model_dump())

            if keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())

        return list(result.values())