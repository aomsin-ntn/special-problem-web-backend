# app/schemas/root_schema.py

from pydantic import BaseModel


class RootResponse(BaseModel):
    message: str


class ItemRequest(BaseModel):
    name: str
    description: str | None = None
    price: float | None = None


class ItemResponse(BaseModel):
    item_id: int
    q: str | None = None