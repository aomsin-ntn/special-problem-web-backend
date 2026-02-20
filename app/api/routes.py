"""
All API Routes
"""
from fastapi import APIRouter
from app.models import RootResponse, ItemResponse, ItemRequest

router = APIRouter()


@router.get("/", response_model=RootResponse)
def read_root():
    return {"message": "World"}


@router.get("/items/{item_id}", response_model=ItemResponse)
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


@router.post("/items/", response_model=ItemResponse)
def create_item(item: ItemRequest):
    """Create a new item"""
    return {"item_id": 1, "q": item.name}
