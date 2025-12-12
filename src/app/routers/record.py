from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from pathlib import Path
import json
import time

router = APIRouter(prefix="/record")


class RecordPayload(BaseModel):
    label: str
    landmarks: Dict[str, Dict[str, Any]]
    timestamp: float | None = None


@router.post("/sample")
def save_sample(payload: RecordPayload):
    t = payload.timestamp or time.time()
    base = Path("data/raw") / payload.label
    base.mkdir(parents=True, exist_ok=True)
    filename = base / f"sample_{int(t*1000)}.json"
    try:
        with filename.open("w", encoding="utf-8") as f:
            json.dump({"label": payload.label, "timestamp": t, "landmarks": payload.landmarks}, f, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "saved", "path": str(filename)}
