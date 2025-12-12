from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from src.app.services.recognizer import Recognizer
from src.app.services.interpret import InterpretService
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class LandmarksPayload(BaseModel):
    landmarks: Dict[str, Dict[str, Any]]


class RecognitionResult(BaseModel):
    label: str
    confidence: float


@router.post("/recognize")
def recognize(payload: LandmarksPayload):
    try:
        label, conf = Recognizer.simple_rule_recognize(payload.landmarks)
        logger.debug(f"Recognized: {label} ({conf})")
        
        interpreter = InterpretService()
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            import asyncio as _asyncio

            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)

        result = loop.run_until_complete(interpreter.execute(label))
        logger.debug(f"Interpretation result: {result}")
        return {"label": label, "confidence": conf, "action": result}
    except Exception as e:
        logger.exception("Error in recognize endpoint")
        return {"label": "error", "confidence": 0.0, "error": str(e)}
