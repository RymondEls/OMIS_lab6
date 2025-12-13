"""
Подсистема распознавания и классификации
На основе предобработанных данных идентифицирует конкретные жесты и движения,
классифицируя их согласно загруженному словарю жестов.
"""
from typing import Dict, Optional, List, Tuple
from collections import deque
import numpy as np
import logging
from src.app.services.preprocess import LandmarkPreprocessor

logger = logging.getLogger(__name__)


class GestureRecognizer:
    """
    Распознаватель жестов на основе правил и временных паттернов.
    Поддерживает статические и динамические жесты.
    """

    def __init__(self, history_size: int = 15):
        """
        Инициализация распознавателя.
        
        Args:
            history_size: Размер истории для распознавания динамических жестов
        """
        self.history_size = history_size
        self.preprocessor = LandmarkPreprocessor()
        
        # Буферы истории для динамических жестов
        self._wrist_history: Dict[str, deque] = {
            'left': deque(maxlen=history_size),
            'right': deque(maxlen=history_size)
        }
        self._velocity_history: deque = deque(maxlen=history_size)
        
        # Пороги для распознавания
        self.thresholds = {
            'hand_raise_y_offset': 0.15,  # Минимальное смещение запястья вверх относительно носа
            'hand_clap_distance': 0.12,   # Максимальное расстояние между руками для хлопка
            'hand_clap_z_diff': 0.08,     # Максимальная разница по Z для хлопка
            'point_extension': 0.15,      # Минимальное вытягивание руки для указания (уменьшено)
            'point_extension_min': 0.10,  # Минимальное вытягивание без проверки локтя
            'wave_movement': 0.05,         # Минимальное движение для маха
            'hands_close_distance': 0.20,  # Максимальное расстояние для "руки близко" (увеличено)
            'hands_close_y_diff': 0.10,   # Максимальная разница по Y для "руки близко"
        }

    @staticmethod
    def _distance(a: Dict[str, float], b: Dict[str, float]) -> float:
        """Вычисление расстояния между двумя точками."""
        return np.sqrt(
            (a.get('x', 0) - b.get('x', 0)) ** 2 +
            (a.get('y', 0) - b.get('y', 0)) ** 2
        )

    @staticmethod
    def _is_visible(point: Optional[Dict[str, float]], threshold: float = 0.5) -> bool:
        """Проверка видимости точки."""
        return point is not None and point.get('visibility', 0.0) > threshold

    def recognize(self, landmarks: Dict[str, Dict[str, float]]) -> str:
        """
        Распознавание жеста на основе landmarks.
        
        Args:
            landmarks: Словарь landmarks
        
        Returns:
            Метка распознанного жеста или "none"
        """
        if not landmarks:
            return "none"
        
        # Предобработка
        filtered = self.preprocessor.filter_landmarks(landmarks)
        key_points = self.preprocessor.extract_key_points(landmarks)
        
        # Извлечение ключевых точек
        nose = key_points.get('nose')
        left_shoulder = key_points.get('left_shoulder')
        right_shoulder = key_points.get('right_shoulder')
        left_wrist = key_points.get('left_wrist')
        right_wrist = key_points.get('right_wrist')
        left_elbow = key_points.get('left_elbow')
        right_elbow = key_points.get('right_elbow')
        
        # Проверка видимости необходимых точек
        required_points = [nose, left_shoulder, right_shoulder]
        if not all(self._is_visible(p) for p in required_points if p):
            return "none"
        
        # Нормализация относительно ширины плеч
        shoulder_width = self._distance(left_shoulder, right_shoulder) if left_shoulder and right_shoulder else 0.3
        if shoulder_width <= 0:
            shoulder_width = 0.3
        
        # === СТАТИЧЕСКИЕ ЖЕСТЫ ===
        
        # Поднятие рук
        left_up = False
        right_up = False
        
        if self._is_visible(left_wrist) and nose:
            left_up = left_wrist['y'] < (nose['y'] - self.thresholds['hand_raise_y_offset'])
        
        if self._is_visible(right_wrist) and nose:
            right_up = right_wrist['y'] < (nose['y'] - self.thresholds['hand_raise_y_offset'])
        
        if left_up and right_up:
            return "both_hands_up"
        
        if right_up:
            return "raise_right_hand"
        
        if left_up:
            return "raise_left_hand"
        
        # Хлопок (руки близко друг к другу)
        if self._is_visible(left_wrist) and self._is_visible(right_wrist):
            dist_hands = self._distance(left_wrist, right_wrist) / shoulder_width
            z_diff = abs(left_wrist.get('z', 0) - right_wrist.get('z', 0))
            
            if dist_hands < self.thresholds['hand_clap_distance'] and z_diff < self.thresholds['hand_clap_z_diff']:
                return "clap"
        
        # Указание (вытянутая рука)
        # Проверяем указание влево
        if self._is_visible(left_wrist) and self._is_visible(left_shoulder):
            # Проверка, что рука вытянута вперед и влево
            x_extension = left_shoulder['x'] - left_wrist['x']
            
            # Базовое условие: рука вытянута влево
            if x_extension > self.thresholds['point_extension_min']:
                # Если есть данные о локте, проверяем вытянутость руки
                if left_elbow and self._is_visible(left_elbow):
                    wrist_to_shoulder = self._distance(left_wrist, left_shoulder)
                    elbow_to_shoulder = self._distance(left_elbow, left_shoulder)
                    # Рука должна быть вытянута (запястье дальше локтя) или просто достаточно вытянута влево
                    if (wrist_to_shoulder > elbow_to_shoulder * 1.15) or (x_extension > self.thresholds['point_extension']):
                        # Дополнительная проверка: рука не должна быть поднята слишком высоко
                        if not left_up:  # Не поднята вверх
                            return "point_left"
                # Если локтя нет, но рука достаточно вытянута влево
                elif x_extension > self.thresholds['point_extension']:
                    if not left_up:
                        return "point_left"
        
        # Проверяем указание вправо
        if self._is_visible(right_wrist) and self._is_visible(right_shoulder):
            x_extension = right_wrist['x'] - right_shoulder['x']
            
            if x_extension > self.thresholds['point_extension_min']:
                if right_elbow and self._is_visible(right_elbow):
                    wrist_to_shoulder = self._distance(right_wrist, right_shoulder)
                    elbow_to_shoulder = self._distance(right_elbow, right_shoulder)
                    if (wrist_to_shoulder > elbow_to_shoulder * 1.15) or (x_extension > self.thresholds['point_extension']):
                        if not right_up:  # Не поднята вверх
                            return "point_right"
                elif x_extension > self.thresholds['point_extension']:
                    if not right_up:
                        return "point_right"
        
        # Руки близко (но не хлопок и не подняты вверх)
        if self._is_visible(left_wrist) and self._is_visible(right_wrist):
            dist_hands = self._distance(left_wrist, right_wrist) / shoulder_width
            z_diff = abs(left_wrist.get('z', 0) - right_wrist.get('z', 0))
            y_diff = abs(left_wrist.get('y', 0) - right_wrist.get('y', 0))
            
            # Руки должны быть близко, но не слишком (не хлопок)
            # И не слишком далеко по Z (не на разной глубине)
            # И не слишком далеко по Y (на примерно одной высоте)
            if (self.thresholds['hand_clap_distance'] < dist_hands < 
                self.thresholds['hands_close_distance'] and
                z_diff < 0.15 and  # Руки на примерно одной глубине
                y_diff < self.thresholds['hands_close_y_diff'] and  # Руки на примерно одной высоте
                not left_up and not right_up):  # Руки не подняты вверх
                return "hands_close"
        
        # === ДИНАМИЧЕСКИЕ ЖЕСТЫ ===
        
        # Мах рукой (wave)
        if self._is_visible(right_wrist):
            self._wrist_history['right'].append(right_wrist['x'])
            if len(self._wrist_history['right']) == self.history_size and right_up:
                movement = np.std(list(self._wrist_history['right']))
                if movement > self.thresholds['wave_movement']:
                    return "wave_right"
        
        if self._is_visible(left_wrist):
            self._wrist_history['left'].append(left_wrist['x'])
            if len(self._wrist_history['left']) == self.history_size and left_up:
                movement = np.std(list(self._wrist_history['left']))
                if movement > self.thresholds['wave_movement']:
                    return "wave_left"
        
        # Круговое движение рукой
        if self._is_visible(right_wrist) and len(self._wrist_history['right']) >= 10:
            positions = list(self._wrist_history['right'])
            if len(positions) >= 10:
                # Упрощенная проверка: большая вариация по X
                x_variation = np.std(positions[-10:])
                # Проверка движения по Y (нужно сохранять историю Y)
                if right_wrist:
                    # Для упрощения проверяем только вариацию по X
                    # Полноценная проверка кругового движения требует истории по обеим осям
                    if x_variation > 0.08 and right_up:
                        # Дополнительная проверка: движение должно быть периодическим
                        return "circle_right"
        
        return "none"

    def recognize_sequence(
        self, 
        landmark_sequence: List[Dict[str, Dict[str, float]]]
    ) -> List[Tuple[str, float]]:
        """
        Распознавание последовательности жестов (для анализа движений).
        
        Args:
            landmark_sequence: Последовательность landmarks
        
        Returns:
            Список кортежей (жест, timestamp)
        """
        results = []
        for i, landmarks in enumerate(landmark_sequence):
            gesture = self.recognize(landmarks)
            if gesture != "none":
                results.append((gesture, float(i)))
        return results

    def reset_history(self):
        """Сброс истории для нового сеанса распознавания."""
        self._wrist_history['left'].clear()
        self._wrist_history['right'].clear()
        self._velocity_history.clear()
