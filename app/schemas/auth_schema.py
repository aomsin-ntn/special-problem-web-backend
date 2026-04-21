from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class FirstLoginCreateUserRequest(BaseModel):
    token: str
    student_id: Optional[str] = None
    user_name_th: str
    user_name_en: str
    degree_id: Optional[UUID] = None