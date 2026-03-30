from sqlmodel import Session, select
from app.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.project_file import ProjectFile
from app.models.keyword import Keyword
from app.models.project_keyword import ProjectKeyword

class ProjectRepository:
    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        # result = db.query(Project,Keywords).order_by(Project.download_count.desc()).limit(5).all()
        result = db.exec(
            select(Project, Keyword)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id)
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id)
            .order_by(Project.download_count.desc())
            .limit(5)
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