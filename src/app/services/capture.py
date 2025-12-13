"""
Подсистема захвата данных
Осуществляет получение исходных данных о положении и движении тела пользователя
с помощью hardware-сенсоров (камеры глубины, RGB-камеры, IMU, motion capture-костюмы).
"""
import cv2
import mediapipe as mp
import asyncio
import base64
from typing import Dict, Any, Optional, List
import logging
import websockets

logger = logging.getLogger(__name__)


class CaptureService:
    """
    Сервис захвата данных с камеры и извлечения ключевых точек скелета.
    Поддерживает MediaPipe для детекции позы и рук.
    """

    def __init__(self, device: int = 0, enable_hands: bool = True):
        """
        Инициализация сервиса захвата.
        
        Args:
            device: ID камеры (обычно 0 для встроенной камеры)
            enable_hands: Включить детекцию рук для более точного распознавания жестов
        """
        self.device = device
        self.enable_hands = enable_hands
        self._cap: Optional[cv2.VideoCapture] = None
        
        # Инициализация MediaPipe Pose
        self._mp_pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            enable_segmentation=False
        )
        
        # Инициализация MediaPipe Hands (для детекции жестов рук)
        self._mp_hands = None
        if enable_hands:
            self._mp_hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_drawing_styles = mp.solutions.drawing_styles

    def initialize(self) -> bool:
        """Инициализация камеры."""
        try:
            self._cap = cv2.VideoCapture(self.device)
            if not self._cap.isOpened():
                logger.error(f"Не удалось открыть камеру {self.device}")
                return False
            # Установка разрешения
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            logger.info(f"Камера {self.device} успешно инициализирована")
            return True
        except Exception as e:
            logger.exception(f"Ошибка инициализации камеры: {e}")
            return False

    def release(self) -> None:
        """Освобождение ресурсов."""
        try:
            if self._cap:
                self._cap.release()
                self._cap = None
            if self._mp_pose:
                try:
                    self._mp_pose.close()
                except (AttributeError, Exception):
                    pass
                self._mp_pose = None
            if self._mp_hands:
                try:
                    self._mp_hands.close()
                except (AttributeError, Exception):
                    pass
                self._mp_hands = None
            logger.info("Ресурсы захвата освобождены")
        except Exception as e:
            logger.exception(f"Ошибка при освобождении ресурсов: {e}")

    @staticmethod
    def _landmarks_to_dict(landmarks, landmark_type: str = "pose") -> Dict[str, Dict[str, float]]:
        """
        Преобразование MediaPipe landmarks в словарь.
        
        Args:
            landmarks: MediaPipe landmarks объект
            landmark_type: Тип landmarks ("pose" или "hands")
        
        Returns:
            Словарь с координатами ключевых точек
        """
        out: Dict[str, Dict[str, float]] = {}
        if not landmarks:
            return out
        
        for idx, lm in enumerate(landmarks.landmark):
            key = f"{landmark_type}_{idx}"
            out[key] = {
                "x": lm.x,
                "y": lm.y,
                "z": lm.z,
                "visibility": lm.visibility if hasattr(lm, 'visibility') else 1.0
            }
        return out

    def capture_frame(self) -> Optional[Dict[str, Any]]:
        """
        Захват одного кадра и извлечение ключевых точек.
        
        Returns:
            Словарь с данными кадра и landmarks, или None при ошибке
        """
        if not self._cap or not self._cap.isOpened():
            return None
        
        ret, frame = self._cap.read()
        if not ret:
            return None
        
        # Изменение размера для производительности
        frame_resized = cv2.resize(frame, (640, 480))
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        
        # Обработка позы
        pose_results = self._mp_pose.process(frame_rgb)
        pose_landmarks = {}
        if pose_results.pose_landmarks:
            pose_landmarks = self._landmarks_to_dict(pose_results.pose_landmarks, "pose")
        
        # Обработка рук
        hands_landmarks = {}
        if self._mp_hands:
            hands_results = self._mp_hands.process(frame_rgb)
            if hands_results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(hands_results.multi_hand_landmarks):
                    hand_key = f"hand_{hand_idx}"
                    hands_landmarks[hand_key] = self._landmarks_to_dict(hand_landmarks, f"hand_{hand_idx}")
        
        # Кодирование кадра в base64
        _, jpeg = cv2.imencode('.jpg', frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(jpeg.tobytes()).decode('ascii')
        frame_b64 = f"data:image/jpeg;base64,{b64}"
        
        import time
        return {
            "frame": frame_b64,
            "landmarks": {**pose_landmarks, **hands_landmarks},
            "timestamp": time.time()
        }

    async def stream_to_websocket(self, websocket) -> None:
        """
        Потоковая передача данных через WebSocket.
        
        Args:
            websocket: WebSocket соединение
        """
        if not self.initialize():
            await websocket.close(code=1008, reason="Camera initialization failed")
            return
        
        loop = asyncio.get_event_loop()
        try:
            while True:
                # Захват кадра в executor для избежания блокировки
                frame_data = await loop.run_in_executor(None, self.capture_frame)
                
                if frame_data is None:
                    await asyncio.sleep(0.033)  # ~30 FPS
                    continue
                
                await websocket.send_json(frame_data)
                await asyncio.sleep(0.033)  # Контроль частоты кадров
                
        except (ConnectionError, Exception) as e:
            # Игнорируем нормальное закрытие соединения
            if isinstance(e, (websockets.exceptions.ConnectionClosedOK, 
                             websockets.exceptions.ConnectionClosedError)):
                logger.debug(f"WebSocket соединение закрыто: {e}")
            else:
                logger.exception(f"Ошибка в потоке WebSocket: {e}")
        finally:
            self.release()
