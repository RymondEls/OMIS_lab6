from fastapi import APIRouter
from pydantic import BaseModel
import time
import platform

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    uptime: float | None = None
    python: str | None = None


_START = time.time()


@router.get("/health", response_model=HealthResponse)
def health():
    """Health endpoint with basic runtime info."""
    return {"status": "ok", "uptime": time.time() - _START, "python": platform.python_version()}
