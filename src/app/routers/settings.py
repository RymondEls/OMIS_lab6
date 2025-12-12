from fastapi import APIRouter, HTTPException
from typing import Any, Dict
from pathlib import Path
import yaml

router = APIRouter(prefix="/settings")


@router.get("/mappings")
def get_mappings():
    p = Path("configs/mappings.yaml")
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


@router.post("/mappings")
def save_mappings(payload: Dict[str, Any]):
    p = Path("configs/mappings.yaml")
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with p.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, allow_unicode=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}
