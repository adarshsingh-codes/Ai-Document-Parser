"""
App entry point. Run with:
    uvicorn backend.main:app --reload

from the AI-Document-Parser/ root (so the `backend` package resolves).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.upload import router as upload_router
from backend.api.analysis import router as analysis_router
from backend.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="AI Document Parser", version="0.1.0")

# Wide-open CORS for local dev only — tighten this before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(analysis_router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "AI Document Parser"}
