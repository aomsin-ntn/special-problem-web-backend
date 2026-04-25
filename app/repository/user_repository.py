from sqlalchemy.ext.asyncio import AsyncSession
from app.models import user
from app.models.user import User
from sqlmodel import Session, select
from uuid import UUID, uuid4
from app.models.degree import Degree
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.degree_department import DegreeDepartment

class UserRepository:
    @staticmethod
    async def create_user_no_commit(
        db: Session, 
        student_id: str,
        user_name_th: str,
        user_name_en: str,
        degree_id: UUID,
        role: str,
        email: str
    ):  
        user = User(
            user_id=uuid4(),
            student_id=student_id,
            user_name_th=user_name_th,
            user_name_en=user_name_en,
            degree_id=degree_id,
            role=role,
            email=email,
            last_login_at=None
        )
        db.add(user)
        db.flush()
        return user
    
    @staticmethod
    def get_user_profile(db: Session, user_id: str):
        result = db.exec(
            select(User, Degree, Department, Faculty)
            .where(User.user_id == user_id)
            .join(Degree, User.degree_id == Degree.degree_id, isouter=True)
            .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id, isouter=True)
            .join(Department, DegreeDepartment.department_id == Department.department_id, isouter=True)
            .join(Faculty, Department.faculty_id == Faculty.faculty_id, isouter=True)
        ).first()
        
        return result

    @staticmethod
    async def get_user_by_student_id(db: Session, student_id: str):
        result = db.exec(
            select(User)
            .where(User.student_id == student_id)
        ).first()

        return result