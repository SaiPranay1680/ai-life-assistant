import os
from fastapi import FastAPI, Depends
from .db import get_db

app = FastAPI(title="AI Life Assistant - Backend")


@app.get("/health")
async def health(db=Depends(get_db)):
    return {"status": "ok"}
