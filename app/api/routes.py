"""
All API Routes
"""
from fastapi import APIRouter, Depends, UploadFile, File
from app.models import RootResponse, ItemResponse, ItemRequest
from fastapi.responses import JSONResponse
from app.services import upload_handler

router = APIRouter()


@router.get("/", response_model=RootResponse)
def read_root():
    return {"message": "World"}

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    service: upload_handler = Depends()
):
    return await service.save_file(file)