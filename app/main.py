from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.project import router as project_router
from app.api.authentication import router as auth_router
from app.database import init_db
from starlette.middleware.sessions import SessionMiddleware
from app.api.master import router as master_router
from app.api.report import router as report_router

app = FastAPI()
app.include_router(project_router,tags=["Project Management"])
app.include_router(auth_router,tags=["Authentication and User Management"])
app.include_router(master_router,tags=["Get Master Data"])
app.include_router(report_router,tags=["Report"])
app.mount("/thumbnails",StaticFiles(directory="thumbnails"), name="static")
app.mount("/uploads",StaticFiles(directory="uploads"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # พอร์ตของ Svelte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key="your_secret_key_here",  # ควรใช้คีย์ที่ปลอดภัยและไม่เปิดเผย
    same_site="lax",  # ปรับตามความต้องการ (lax, strict, none)
    https_only=False,  # ควรตั้งเป็น True ใน production
)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized and app is starting up...")
