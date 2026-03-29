# app/schemas/root_schema.py

from pydantic import BaseModel
from typing import Literal


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
    department: list[str] | None = None
    page: int = 1
    limit: int = 10
    search: str | None = None
    year: list[str] | None = None
    sorted_by: Literal["downloaded","recent"]
    order: Literal["asc", "desc"]

