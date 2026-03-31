from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from sqlmodel import Session, select
from uuid import UUID
from app.models.degree import Degree
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.degree_department import DegreeDepartment

class UserRepository:
    @staticmethod
    async def create_user(db: AsyncSession, user: User):
        db.add(user)
        db.commit()
        db.refresh(user)
        return user