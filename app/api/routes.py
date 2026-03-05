"""
All API Routes
"""
from fastapi import APIRouter, Depends, UploadFile, File
from app.schemas.root_schema import RootResponse, ItemResponse, ItemRequest
from fastapi.responses import JSONResponse
from app.services.upload_services import UploadServices

router = APIRouter()


@router.get("/", response_model=RootResponse)
def read_root():
    return {"message": "World"}

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    service: UploadServices = Depends()
):
    return await service.save_file(file)