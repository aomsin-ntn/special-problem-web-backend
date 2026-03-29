from sqlmodel import Session
from app.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.project_file import ProjectFile

class ProjectRepository:
    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        result = db.query(Project).order_by(Project.download_count.desc()).limit(5).all()
        return result

    @staticmethod
    async def create_project(db: AsyncSession, project_data: Project):
        db.add(project_data)
        db.commit()
        db.refresh(project_data)
        return project_data

    @staticmethod
    async def create_user(db: AsyncSession, user: User):
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    async def create_project_file(db: AsyncSession, project_file: ProjectFile):
        db.add(project_file)
        db.commit()
        db.refresh(project_file)
        return project_file