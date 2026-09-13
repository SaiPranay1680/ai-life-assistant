from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .db import get_db
from .modules.auth.router import router as auth_router

app = FastAPI(title="AI Life Assistant - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)


@app.get("/health")
async def health(db=Depends(get_db)):
    return {"status": "ok"}
