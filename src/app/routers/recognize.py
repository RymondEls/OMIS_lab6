from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from src.app.services.recognizer import Recognizer
from src.app.services.interpret import InterpretService
import asyncio

router = APIRouter()


class LandmarksPayload(BaseModel):
    landmarks: Dict[str, Dict[str, Any]]


class RecognitionResult(BaseModel):
    label: str
    confidence: float


@router.post("/recognize")
def recognize(payload: LandmarksPayload):
    label, conf = Recognizer.simple_rule_recognize(payload.landmarks)
    # execute interpretation asynchronously but wait for result
    interpreter = InterpretService()
    # run async execute in event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)

    result = loop.run_until_complete(interpreter.execute(label))
    return {"label": label, "confidence": conf, "action": result}
