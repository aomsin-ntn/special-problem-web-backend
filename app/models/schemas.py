"""
Request and Response Schemas
"""
from pydantic import BaseModel


class RootResponse(BaseModel):
    """Root endpoint response"""
    message: str


class ItemRequest(BaseModel):
    """Item request model"""
    name: str
    description: str | None = None
    price: float | None = None


class ItemResponse(BaseModel):
    """Item response model"""
    item_id: int
    q: str | None = None
