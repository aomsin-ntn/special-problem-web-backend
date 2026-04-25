from uuid import UUID, uuid4
from app.models.session import Session
from app.models.user import User
from app.repository.user_repository import UserRepository

class UserServices:
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
        return await UserRepository.create_user_no_commit(
            db=db,
            student_id=student_id,
            user_name_th=user_name_th,
            user_name_en=user_name_en,
            degree_id=degree_id,
            role=role,
            email=email
        )
    
    @staticmethod
    def get_user_profile(db: Session, user_id: str):
        user_profile = UserRepository.get_user_profile(db, user_id)
        return user_profile

    