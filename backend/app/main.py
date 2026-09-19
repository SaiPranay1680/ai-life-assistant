from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .db import get_db
from .modules.auth.router import router as auth_router
from .modules.documents.router import router as documents_router
from .modules.actions.router import router as actions_router
from .security.scanner import get_scanner

app = FastAPI(title="AI Life Assistant - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(actions_router)


@app.get("/health")
async def health(db=Depends(get_db)):
    return {"status": "ok"}


@app.get("/health/ready")
async def ready(db=Depends(get_db)):
    scanner_available = await get_scanner().health_check()
    body = {
        "status": "ok",
        "storage_backend": settings.storage_backend,
        "scanner_required": settings.clamav_required,
        "scanner_available": scanner_available,
    }
    if settings.clamav_required and not scanner_available:
        return JSONResponse(status_code=503, content={**body, "status": "scanner_unavailable"})
    return body
