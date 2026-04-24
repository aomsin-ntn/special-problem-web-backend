from uuid import UUID
from app.models.session import Session
from app.repository.user_repository import UserRepository

class UserServices:
    @staticmethod
    async def create_user_no_commit(db: Session, user_data):
        new_user = await UserRepository.create_user_no_commit(db, user_data)
        return new_user
    
    @staticmethod
    def get_user_profile(db: Session, user_id: str):
        user_profile = UserRepository.get_user_profile(db, user_id)
        return user_profile

    