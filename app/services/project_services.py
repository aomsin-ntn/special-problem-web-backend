from app.repository.project_repository import ProjectRepository
from sqlmodel import Session

class ProjectServices:
    @staticmethod
    async def get_projects(db: Session, request):
        # Implement logic to retrieve projects based on request parameters
        # For example, you can filter projects by faculty, department, degree, etc.
        # This is just a placeholder implementation
        projects = db.query(Project).all()
        return projects

    @staticmethod
    async def delete_project(db: Session, project_id: int):
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.is_active = False  # Mark the project as inactive instead of deleting it
            db.commit()
            return True
        return False

    async def create_project(db: Session, project_data):
        repository = ProjectRepository()
        new_project = await repository.create_project(db, project_data)
        return new_project