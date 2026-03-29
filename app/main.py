from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.project import router
from app.database import init_db


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # พอร์ตของ Svelte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized and app is starting up...")
