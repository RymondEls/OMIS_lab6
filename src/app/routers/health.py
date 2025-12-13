"""
API роутер для проверки здоровья системы.
"""
from fastapi import APIRouter
import time
import platform
import sys

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Проверка состояния системы."""
    return {
        "status": "ok",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "timestamp": time.time()
    }


@router.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "service": "Gesture Recognition System",
        "version": "1.0.0",
        "status": "running"
    }
