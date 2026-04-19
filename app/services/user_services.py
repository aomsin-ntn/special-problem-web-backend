from uuid import UUID
from app.models.session import Session
from app.repository.user_repository import UserRepository
import difflib
import re

class UserServices:
    @staticmethod
    async def create_user(db: Session, user_data):
        new_user = await UserRepository.create_user(db, user_data)
        return new_user