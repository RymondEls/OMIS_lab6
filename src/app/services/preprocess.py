from typing import Dict, List
import math


class LandmarkPreprocessor:
    """Simple preprocessing utilities for pose landmarks.

    Expect landmarks as a dict: {index: {x,y,z,visibility}} where coordinates are normalized [0,1].
    """

    @staticmethod
    def _distance(a: Dict[str, float], b: Dict[str, float]) -> float:
        return math.sqrt((a['x'] - b['x']) ** 2 + (a['y'] - b['y']) ** 2)

    @staticmethod
    def extract_features(landmarks: Dict[str, Dict[str, float]]) -> List[float]:
        """Extract a small fixed-size feature vector from pose landmarks.

        Features: normalized distances from wrists to shoulders and to nose if available.
        """
        if not landmarks:
            return []

        # Mediapipe pose indices: 0 - nose, 11 - left shoulder, 12 - right shoulder, 15 - left wrist, 16 - right wrist
        nose = landmarks.get('0')
        l_sh = landmarks.get('11')
        r_sh = landmarks.get('12')
        l_wr = landmarks.get('15')
        r_wr = landmarks.get('16')

        features: List[float] = []

        # shoulder width for normalization
        if l_sh and r_sh:
            shoulder_width = LandmarkPreprocessor._distance(l_sh, r_sh)
            if shoulder_width <= 0:
                shoulder_width = 1.0
        else:
            shoulder_width = 1.0

        def norm_dist(a, b):
            if not a or not b:
                return 0.0
            return LandmarkPreprocessor._distance(a, b) / shoulder_width

        features.append(norm_dist(l_wr, l_sh))
        features.append(norm_dist(r_wr, r_sh))
        features.append(norm_dist(l_wr, nose) if nose else 0.0)
        features.append(norm_dist(r_wr, nose) if nose else 0.0)

        return features
