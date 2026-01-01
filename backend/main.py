from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.endpoints import router as api_router
from core.config import settings
import os

app = FastAPI(title="Chat with CSV API")

# Configure CORS
origins = [
    "http://localhost:5173",
    "https://chat-with-csv-indol.vercel.app",
]

# Allow overriding/adding via environment variable
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Mount uploads directory to serve static files (reports, etc.)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from backend.core.database import init_db

@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Chat with CSV API is running"}
