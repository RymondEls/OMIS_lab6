"""
Подсистема предобработки данных
Выполняет фильтрацию raw-данных (устранение шумов, сглаживание траекторий),
сегментацию пользователя на фоне, а также идентификацию и трекинг ключевых точек
(скелета, суставов, кистей рук) в пространстве.
"""
from typing import Dict, List, Optional, Tuple
import math
from collections import deque
import numpy as np
import logging

logger = logging.getLogger(__name__)


class LandmarkPreprocessor:
    """
    Сервис предобработки landmarks: фильтрация, сглаживание, извлечение признаков.
    """

    def __init__(self, smoothing_window: int = 5, visibility_threshold: float = 0.5):
        """
        Инициализация препроцессора.
        
        Args:
            smoothing_window: Размер окна для сглаживания (moving average)
            visibility_threshold: Порог видимости точки для фильтрации
        """
        self.smoothing_window = smoothing_window
        self.visibility_threshold = visibility_threshold
        
        # Буферы для сглаживания координат каждой точки
        self._smoothing_buffers: Dict[str, deque] = {}
        
    def _get_or_create_buffer(self, point_key: str) -> deque:
        """Получить или создать буфер сглаживания для точки."""
        if point_key not in self._smoothing_buffers:
            self._smoothing_buffers[point_key] = deque(maxlen=self.smoothing_window)
        return self._smoothing_buffers[point_key]

    @staticmethod
    def _distance(a: Dict[str, float], b: Dict[str, float]) -> float:
        """Вычисление евклидова расстояния между двумя точками."""
        return math.sqrt(
            (a.get('x', 0) - b.get('x', 0)) ** 2 +
            (a.get('y', 0) - b.get('y', 0)) ** 2 +
            (a.get('z', 0) - b.get('z', 0)) ** 2
        )

    def filter_landmarks(
        self, 
        landmarks: Dict[str, Dict[str, float]], 
        visibility_threshold: Optional[float] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Фильтрация точек с низкой видимостью.
        
        Args:
            landmarks: Словарь landmarks
            visibility_threshold: Порог видимости (если None, используется self.visibility_threshold)
        
        Returns:
            Отфильтрованный словарь landmarks
        """
        threshold = visibility_threshold or self.visibility_threshold
        return {
            k: v for k, v in landmarks.items() 
            if v.get('visibility', 0.0) >= threshold
        }

    def smooth_landmarks(self, landmarks: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """
        Сглаживание координат landmarks с помощью moving average.
        
        Args:
            landmarks: Словарь landmarks
        
        Returns:
            Сглаженный словарь landmarks
        """
        smoothed = {}
        
        for point_key, point_data in landmarks.items():
            # Проверка валидности данных
            if not isinstance(point_data, dict):
                smoothed[point_key] = point_data
                continue
            
            # Проверка наличия необходимых ключей
            if 'x' not in point_data or 'y' not in point_data:
                smoothed[point_key] = point_data
                continue
            
            # Добавляем текущие координаты в буфер
            buffer = self._get_or_create_buffer(point_key)
            buffer.append(point_data)
            
            # Вычисляем среднее значение только для валидных данных
            if len(buffer) > 0:
                valid_points = [p for p in buffer if isinstance(p, dict) and 'x' in p and 'y' in p]
                
                if len(valid_points) > 0:
                    avg_x = sum(p.get('x', 0) for p in valid_points) / len(valid_points)
                    avg_y = sum(p.get('y', 0) for p in valid_points) / len(valid_points)
                    avg_z = sum(p.get('z', 0) for p in valid_points) / len(valid_points)
                    avg_visibility = sum(p.get('visibility', 0) for p in valid_points) / len(valid_points)
                    
                    smoothed[point_key] = {
                        'x': avg_x,
                        'y': avg_y,
                        'z': avg_z,
                        'visibility': avg_visibility
                    }
                else:
                    # Если нет валидных точек в буфере, используем текущие данные
                    smoothed[point_key] = point_data
            else:
                smoothed[point_key] = point_data
        
        return smoothed

    def extract_key_points(self, landmarks: Dict[str, Dict[str, float]]) -> Dict[str, Optional[Dict[str, float]]]:
        """
        Извлечение ключевых точек для распознавания жестов.
        
        Args:
            landmarks: Словарь всех landmarks
        
        Returns:
            Словарь с ключевыми точками (nose, shoulders, wrists, etc.)
        """
        filtered = self.filter_landmarks(landmarks)
        
        # MediaPipe Pose индексы
        # 0 - nose, 11 - left_shoulder, 12 - right_shoulder
        # 15 - left_wrist, 16 - right_wrist
        # 13 - left_elbow, 14 - right_elbow
        # 23 - left_hip, 24 - right_hip
        
        key_points = {
            'nose': filtered.get('pose_0'),
            'left_shoulder': filtered.get('pose_11'),
            'right_shoulder': filtered.get('pose_12'),
            'left_elbow': filtered.get('pose_13'),
            'right_elbow': filtered.get('pose_14'),
            'left_wrist': filtered.get('pose_15'),
            'right_wrist': filtered.get('pose_16'),
            'left_hip': filtered.get('pose_23'),
            'right_hip': filtered.get('pose_24'),
        }
        
        # Добавляем точки рук, если доступны
        for hand_key in ['hand_0', 'hand_1']:
            if hand_key in filtered:
                # MediaPipe Hands: 0 - wrist, 4 - thumb tip, 8 - index tip, 12 - middle tip
                hand_points = {}
                for idx in [0, 4, 8, 12]:
                    point_key = f"{hand_key}_{idx}"
                    if point_key in filtered:
                        hand_points[f"finger_{idx}"] = filtered[point_key]
                if hand_points:
                    key_points[hand_key] = hand_points
        
        return key_points

    def extract_features(self, landmarks: Dict[str, Dict[str, float]]) -> List[float]:
        """
        Извлечение нормализованных признаков для классификации.
        
        Args:
            landmarks: Словарь landmarks
        
        Returns:
            Вектор признаков
        """
        filtered = self.filter_landmarks(landmarks)
        if not filtered:
            return []
        
        key_points = self.extract_key_points(landmarks)
        
        nose = key_points.get('nose')
        left_shoulder = key_points.get('left_shoulder')
        right_shoulder = key_points.get('right_shoulder')
        left_wrist = key_points.get('left_wrist')
        right_wrist = key_points.get('right_wrist')
        
        if not all([nose, left_shoulder, right_shoulder]):
            return []
        
        # Нормализация относительно ширины плеч
        shoulder_width = self._distance(left_shoulder, right_shoulder) if left_shoulder and right_shoulder else 1.0
        if shoulder_width <= 0:
            shoulder_width = 1.0
        
        features: List[float] = []
        
        def normalized_distance(a: Optional[Dict], b: Optional[Dict]) -> float:
            """Нормализованное расстояние между двумя точками."""
            if not a or not b:
                return 0.0
            return self._distance(a, b) / shoulder_width
        
        # Расстояния от запястий до плеч
        features.append(normalized_distance(left_wrist, left_shoulder))
        features.append(normalized_distance(right_wrist, right_shoulder))
        
        # Расстояния от запястий до носа
        features.append(normalized_distance(left_wrist, nose))
        features.append(normalized_distance(right_wrist, nose))
        
        # Высота запястий относительно носа
        if left_wrist:
            features.append(left_wrist['y'] - nose['y'])
        else:
            features.append(0.0)
        
        if right_wrist:
            features.append(right_wrist['y'] - nose['y'])
        else:
            features.append(0.0)
        
        # Расстояние между запястьями
        features.append(normalized_distance(left_wrist, right_wrist))
        
        # Горизонтальное положение запястий относительно плеч
        if left_wrist and left_shoulder:
            features.append(left_wrist['x'] - left_shoulder['x'])
        else:
            features.append(0.0)
        
        if right_wrist and right_shoulder:
            features.append(right_wrist['x'] - right_shoulder['x'])
        else:
            features.append(0.0)
        
        return features

    def track_movement(
        self, 
        current_landmarks: Dict[str, Dict[str, float]],
        previous_landmarks: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Dict[str, float]:
        """
        Трекинг движения ключевых точек между кадрами.
        
        Args:
            current_landmarks: Текущие landmarks
            previous_landmarks: Предыдущие landmarks
        
        Returns:
            Словарь со скоростями движения ключевых точек
        """
        if previous_landmarks is None:
            return {}
        
        velocities = {}
        key_points = ['pose_0', 'pose_11', 'pose_12', 'pose_15', 'pose_16']
        
        for point_key in key_points:
            if point_key in current_landmarks and point_key in previous_landmarks:
                curr = current_landmarks[point_key]
                prev = previous_landmarks[point_key]
                velocity = self._distance(curr, prev)
                velocities[point_key] = velocity
        
        return velocities
