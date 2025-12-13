"""
API роутер для настройки системы и управления жестами.
Сценарий: Разработчик приложения создает профиль, назначает жесты на команды.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from src.app.services.interpret import InterpretationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class GestureMappingRequest(BaseModel):
    """Запрос на создание/обновление маппинга жеста."""
    gesture: str
    action_type: str  # "log", "callback", "keyboard", "mouse"
    message: Optional[str] = None
    url: Optional[str] = None
    key: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None


class GestureMappingResponse(BaseModel):
    """Ответ с информацией о маппинге."""
    gesture: str
    mapping: Dict[str, Any]
    status: str


@router.get("/info")
async def get_system_info():
    """Получение информации о системе."""
    return {
        "system": "Gesture Recognition System",
        "version": "1.0.0",
        "modes": ["user", "developer", "specialist"],
        "subsystems": [
            "capture",
            "preprocessing",
            "recognition",
            "interpretation",
            "interface"
        ]
    }


@router.get("/gestures")
async def get_all_gesture_mappings():
    """
    Получение всех настроенных маппингов жестов.
    Сценарий: Разработчик просматривает список доступных жестов и их назначений.
    """
    try:
        interpreter = InterpretationService()
        mappings = interpreter.get_all_mappings()
        return {
            "mappings": mappings,
            "count": len(mappings)
        }
    except Exception as e:
        logger.exception(f"Ошибка получения маппингов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gestures/{gesture}")
async def get_gesture_mapping(gesture: str):
    """Получение маппинга для конкретного жеста."""
    try:
        interpreter = InterpretationService()
        mapping = interpreter.get_mapping(gesture)
        if not mapping:
            raise HTTPException(status_code=404, detail=f"Жест '{gesture}' не найден")
        return {
            "gesture": gesture,
            "mapping": mapping
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка получения маппинга: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gestures", response_model=GestureMappingResponse)
async def create_gesture_mapping(request: GestureMappingRequest):
    """
    Создание нового маппинга жеста на действие.
    Сценарий: Разработчик назначает жест "смахнуть рукой" на команду "следующая страница".
    """
    try:
        interpreter = InterpretationService()
        
        # Подготовка параметров маппинга
        mapping_params = {
            "type": request.action_type,
        }
        
        if request.message:
            mapping_params["message"] = request.message
        if request.url:
            mapping_params["url"] = request.url
        if request.key:
            mapping_params["key"] = request.key
        if request.action:
            mapping_params["action"] = request.action
        if request.description:
            mapping_params["description"] = request.description
        
        success = interpreter.add_mapping(request.gesture, request.action_type, **mapping_params)
        
        if not success:
            raise HTTPException(status_code=500, detail="Не удалось создать маппинг")
        
        mapping = interpreter.get_mapping(request.gesture)
        return GestureMappingResponse(
            gesture=request.gesture,
            mapping=mapping,
            status="created"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка создания маппинга: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/gestures/{gesture}", response_model=GestureMappingResponse)
async def update_gesture_mapping(gesture: str, request: GestureMappingRequest):
    """Обновление существующего маппинга жеста."""
    try:
        interpreter = InterpretationService()
        
        # Удаляем старый маппинг
        interpreter.remove_mapping(gesture)
        
        # Создаем новый
        mapping_params = {"type": request.action_type}
        if request.message:
            mapping_params["message"] = request.message
        if request.url:
            mapping_params["url"] = request.url
        if request.key:
            mapping_params["key"] = request.key
        if request.action:
            mapping_params["action"] = request.action
        if request.description:
            mapping_params["description"] = request.description
        
        success = interpreter.add_mapping(gesture, request.action_type, **mapping_params)
        
        if not success:
            raise HTTPException(status_code=500, detail="Не удалось обновить маппинг")
        
        mapping = interpreter.get_mapping(gesture)
        return GestureMappingResponse(
            gesture=gesture,
            mapping=mapping,
            status="updated"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка обновления маппинга: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/gestures/{gesture}")
async def delete_gesture_mapping(gesture: str):
    """Удаление маппинга жеста."""
    try:
        interpreter = InterpretationService()
        success = interpreter.remove_mapping(gesture)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Жест '{gesture}' не найден")
        
        return {
            "status": "deleted",
            "gesture": gesture
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка удаления маппинга: {e}")
        raise HTTPException(status_code=500, detail=str(e))
