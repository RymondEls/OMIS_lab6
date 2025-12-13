"""
API роутер для подсистемы распознавания жестов.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from src.app.services.recognizer import GestureRecognizer
from src.app.services.interpret import InterpretationService
from src.app.services.preprocess import LandmarkPreprocessor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recognize", tags=["recognition"])


class LandmarksPayload(BaseModel):
    """Модель для передачи landmarks."""
    landmarks: Dict[str, Dict[str, Any]]
    timestamp: Optional[float] = None


class RecognitionResponse(BaseModel):
    """Ответ с результатом распознавания."""
    gesture: str
    confidence: Optional[float] = None
    action: Dict[str, Any]
    timestamp: Optional[float] = None


@router.post("", response_model=RecognitionResponse)
async def recognize_gesture(payload: LandmarksPayload):
    """
    Распознавание жеста на основе landmarks.
    
    Сценарий использования: Конечный пользователь выполняет движения перед камерой,
    система распознает их и возвращает результат.
    """
    try:
        # Предобработка
        preprocessor = LandmarkPreprocessor()
        smoothed_landmarks = preprocessor.smooth_landmarks(payload.landmarks)
        
        # Распознавание
        recognizer = GestureRecognizer()
        gesture = recognizer.recognize(smoothed_landmarks)
        
        # Интерпретация
        interpreter = InterpretationService()
        context = {
            "timestamp": payload.timestamp,
            "landmarks": smoothed_landmarks
        }
        action_result = await interpreter.execute(gesture, context)
        
        logger.debug(f"Распознан жест: {gesture}, действие: {action_result.get('status')}")
        
        return RecognitionResponse(
            gesture=gesture,
            action=action_result,
            timestamp=payload.timestamp
        )
    
    except Exception as e:
        logger.exception(f"Ошибка распознавания жеста: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка распознавания: {str(e)}")


@router.post("/batch")
async def recognize_batch(landmarks_list: list[LandmarksPayload]):
    """
    Пакетное распознавание последовательности жестов.
    Используется для анализа движений.
    """
    try:
        recognizer = GestureRecognizer()
        preprocessor = LandmarkPreprocessor()
        results = []
        
        for payload in landmarks_list:
            smoothed = preprocessor.smooth_landmarks(payload.landmarks)
            gesture = recognizer.recognize(smoothed)
            if gesture != "none":
                results.append({
                    "gesture": gesture,
                    "timestamp": payload.timestamp
                })
        
        return {
            "recognized_gestures": results,
            "total_frames": len(landmarks_list),
            "gestures_count": len(results)
        }
    
    except Exception as e:
        logger.exception(f"Ошибка пакетного распознавания: {e}")
        raise HTTPException(status_code=500, detail=str(e))
