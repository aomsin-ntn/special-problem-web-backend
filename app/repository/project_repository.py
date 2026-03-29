from sqlmodel import Session
from app.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession

class ProjectRepository:
    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        result = db.query(Project).order_by(Project.download_count.desc()).limit(5).all()
        return result

    @staticmethod
    async def create_project(db: AsyncSession, project_data: Project):
        db.add(project_data)
        await db.commit()
        await db.refresh(project_data)
        return project_data
