"""
API роутер для подсистемы захвата данных.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from src.app.services.capture import CaptureService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capture", tags=["capture"])


@router.websocket("/ws")
async def websocket_capture(websocket: WebSocket):
    """
    WebSocket endpoint для потоковой передачи данных захвата.
    Отправляет кадры видео и landmarks в реальном времени.
    """
    await websocket.accept()
    logger.info("WebSocket соединение установлено для захвата")
    
    capture = CaptureService(device=0, enable_hands=True)
    
    try:
        await capture.stream_to_websocket(websocket)
    except WebSocketDisconnect:
        logger.info("WebSocket соединение закрыто клиентом")
    except Exception as e:
        logger.exception(f"Ошибка в WebSocket потоке: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        capture.release()


@router.get("/status")
async def get_capture_status():
    """Получение статуса подсистемы захвата."""
    try:
        capture = CaptureService()
        initialized = capture.initialize()
        capture.release()
        return {
            "status": "available" if initialized else "unavailable",
            "device": capture.device,
            "hands_enabled": capture.enable_hands
        }
    except Exception as e:
        logger.exception(f"Ошибка проверки статуса захвата: {e}")
        raise HTTPException(status_code=500, detail=str(e))
