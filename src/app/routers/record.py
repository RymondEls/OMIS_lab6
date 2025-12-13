"""
API роутер для записи и анализа движений.
Сценарий: Специалист записывает движение пользователя и получает анализ техники.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import time
import logging
from src.app.services.preprocess import LandmarkPreprocessor
from src.app.services.recognizer import GestureRecognizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/record", tags=["recording"])


class RecordSequenceRequest(BaseModel):
    """Запрос на запись последовательности движений."""
    label: str  # Название упражнения/движения
    sequence: List[Dict[str, Dict[str, Any]]]  # Последовательность landmarks
    timestamp: Optional[float] = None
    reference_sequence: Optional[List[Dict[str, Dict[str, Any]]]] = None  # Эталонная последовательность


class AnalysisReport(BaseModel):
    """Отчет об анализе движения."""
    avg_deviation: float
    max_deviation: float
    min_deviation: float
    progress_note: str
    details: List[float]
    recognized_gestures: List[Dict[str, Any]]
    recommendations: List[str]


class RecordResponse(BaseModel):
    """Ответ на запрос записи."""
    status: str
    path: Optional[str] = None
    report: AnalysisReport


@router.post("/sequence", response_model=RecordResponse)
async def save_and_analyze_sequence(request: RecordSequenceRequest):
    """
    Сохранение последовательности движений и анализ техники.
    Сценарий: Специалист запускает режим анализа, пользователь выполняет упражнение,
    система сравнивает с эталоном и выдает отчет.
    """
    try:
        timestamp = request.timestamp or time.time()
        base_dir = Path("data/sequences") / request.label
        base_dir.mkdir(parents=True, exist_ok=True)
        filename = base_dir / f"sequence_{int(timestamp * 1000)}.json"
        
        # Предобработка последовательности
        preprocessor = LandmarkPreprocessor()
        features_list = []
        
        for frame in request.sequence:
            filtered = preprocessor.filter_landmarks(frame)
            if filtered:
                features = preprocessor.extract_features(frame)
                features_list.append(features)
        
        if not features_list:
            raise HTTPException(status_code=400, detail="Не удалось извлечь признаки из последовательности")
        
        # Распознавание жестов в последовательности
        recognizer = GestureRecognizer()
        recognized_gestures = recognizer.recognize_sequence(request.sequence)
        
        # Анализ отклонений от эталона
        deviations = []
        reference_features = None
        
        if request.reference_sequence:
            # Извлечение признаков эталонной последовательности
            ref_features_list = []
            for frame in request.reference_sequence:
                filtered = preprocessor.filter_landmarks(frame)
                if filtered:
                    features = preprocessor.extract_features(frame)
                    ref_features_list.append(features)
            
            if ref_features_list:
                # Усреднение эталонных признаков
                import numpy as np
                reference_features = np.mean(ref_features_list, axis=0).tolist()
        
        # Вычисление отклонений
        if reference_features:
            for features in features_list:
                if len(features) == len(reference_features):
                    dev = sum(abs(f - e) for f, e in zip(features, reference_features)) / len(features)
                    deviations.append(dev)
        else:
            # Если эталона нет, используем вариативность внутри последовательности
            import numpy as np
            if len(features_list) > 1:
                mean_features = np.mean(features_list, axis=0)
                for features in features_list:
                    if len(features) == len(mean_features):
                        dev = sum(abs(f - m) for f, m in zip(features, mean_features)) / len(features)
                        deviations.append(dev)
        
        # Формирование отчета
        avg_deviation = sum(deviations) / len(deviations) if deviations else 0.0
        max_deviation = max(deviations) if deviations else 0.0
        min_deviation = min(deviations) if deviations else 0.0
        
        # Оценка техники
        if avg_deviation < 0.15:
            progress_note = "Отличная техника выполнения"
            recommendations = ["Продолжайте в том же духе"]
        elif avg_deviation < 0.25:
            progress_note = "Хорошая техника, есть небольшие отклонения"
            recommendations = [
                "Обратите внимание на симметрию движений",
                "Старайтесь поддерживать плавность"
            ]
        else:
            progress_note = "Требуется улучшение техники"
            recommendations = [
                "Попробуйте выполнить движение медленнее",
                "Сосредоточьтесь на правильной форме",
                "Повторите упражнение несколько раз"
            ]
        
        report = AnalysisReport(
            avg_deviation=round(avg_deviation, 4),
            max_deviation=round(max_deviation, 4),
            min_deviation=round(min_deviation, 4),
            progress_note=progress_note,
            details=[round(d, 4) for d in deviations],
            recognized_gestures=[
                {"gesture": g, "frame": int(t)} for g, t in recognized_gestures
            ],
            recommendations=recommendations
        )
        
        # Сохранение данных
        data = {
            "label": request.label,
            "timestamp": timestamp,
            "sequence": request.sequence,
            "features": features_list,
            "report": report.dict(),
            "reference_sequence": request.reference_sequence is not None
        }
        
        with filename.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Последовательность сохранена: {filename}, отклонение: {avg_deviation:.4f}")
        
        return RecordResponse(
            status="saved",
            path=str(filename),
            report=report
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка сохранения последовательности: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sequences/{label}")
async def get_sequences_by_label(label: str):
    """Получение всех записей для конкретного упражнения."""
    try:
        base_dir = Path("data/sequences") / label
        if not base_dir.exists():
            return {"sequences": [], "count": 0}
        
        sequences = []
        for file_path in base_dir.glob("sequence_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sequences.append({
                        "filename": file_path.name,
                        "timestamp": data.get("timestamp"),
                        "avg_deviation": data.get("report", {}).get("avg_deviation")
                    })
            except Exception as e:
                logger.warning(f"Ошибка чтения файла {file_path}: {e}")
        
        sequences.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return {
            "label": label,
            "sequences": sequences,
            "count": len(sequences)
        }
    
    except Exception as e:
        logger.exception(f"Ошибка получения последовательностей: {e}")
        raise HTTPException(status_code=500, detail=str(e))
