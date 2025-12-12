import cv2
import mediapipe as mp
import asyncio
import base64
from typing import Dict, Any


class CaptureService:
    """Service to capture frames and extract pose landmarks using MediaPipe."""

    def __init__(self, device: int = 0):
        self.device = device
        self._mp_holistic = mp.solutions.holistic.Holistic(static_image_mode=False)

    def release(self) -> None:
        try:
            self._mp_holistic.close()
        except Exception:
            pass

    @staticmethod
    def _landmarks_to_dict(landmarks) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for idx, lm in enumerate(landmarks.landmark):
            out[str(idx)] = {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": getattr(lm, 'visibility', 0.0)}
        return out

    async def stream_to_websocket(self, websocket) -> None:
        """Open camera and stream landmark data to a FastAPI WebSocket.

        This method is written to be used inside an async WebSocket endpoint.
        """
        loop = asyncio.get_event_loop()
        cap = cv2.VideoCapture(self.device)
        try:
            while True:
                # Read frame in threadpool to avoid blocking event loop
                ret, frame = await loop.run_in_executor(None, cap.read)
                if not ret:
                    await asyncio.sleep(0.05)
                    continue

                # Resize to reasonable size for network transfer
                frame_small = await loop.run_in_executor(None, cv2.resize, frame, (640, 480))

                # Convert color and process with MediaPipe in threadpool
                frame_rgb = await loop.run_in_executor(None, cv2.cvtColor, frame_small, cv2.COLOR_BGR2RGB)
                results = await loop.run_in_executor(None, self._mp_holistic.process, frame_rgb)

                landmarks = {}
                if getattr(results, 'pose_landmarks', None):
                    landmarks = self._landmarks_to_dict(results.pose_landmarks)

                # encode frame as JPEG base64 for client display
                try:
                    _, jpeg = await loop.run_in_executor(None, cv2.imencode, '.jpg', frame_small)
                    b64 = base64.b64encode(jpeg.tobytes()).decode('ascii')
                    frame_b64 = f"data:image/jpeg;base64,{b64}"
                except Exception:
                    frame_b64 = None

                payload: Dict[str, Any] = {"landmarks": landmarks, "frame": frame_b64}
                await websocket.send_json(payload)

        finally:
            cap.release()
            self.release()
