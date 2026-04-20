# app/schemas/root_schema.py

from pydantic import BaseModel
from typing import Literal
from uuid import UUID


class RootResponse(BaseModel):
    message: str


class ItemRequest(BaseModel):
    name: str
    description: str | None = None
    price: float | None = None


class ItemResponse(BaseModel):
    item_id: int
    q: str | None = None

class GetProjectRequestParams(BaseModel):
    department: list[UUID] | None = None
    page: int = 1
    limit: int = 10
    search: str | None = None
    year: list[str] | None = None
    sorted_by: Literal["downloaded_count","created_at", "student_id", "user_name_th", "title_th", "academic_year"] | None = None
    order: Literal["asc", "desc"]
