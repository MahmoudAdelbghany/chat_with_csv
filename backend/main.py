from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.endpoints import router as api_router
from core.config import settings

app = FastAPI(title="Chat with CSV API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # TODO: Lock this down to specific domains once authentication is implemented
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.core.database import init_db

@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Chat with CSV API is running"}
