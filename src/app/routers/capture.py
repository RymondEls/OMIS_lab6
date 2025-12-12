from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.app.services.capture import CaptureService
from src.app.services.preprocess import LandmarkPreprocessor
from src.app.services.recognizer import Recognizer
import asyncio

router = APIRouter()


@router.websocket("/ws/capture")
async def websocket_capture(websocket: WebSocket):
    await websocket.accept()
    capture = CaptureService()
    try:
        # stream frames -> websocket; CaptureService handles camera read in executor
        await capture.stream_to_websocket(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        capture.release()
