from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

class UserRepository:
    @staticmethod
    async def create_user(db: AsyncSession, user: User):
        db.add(user)
        db.commit()
        db.refresh(user)
        return user