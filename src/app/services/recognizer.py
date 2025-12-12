from typing import Dict, Tuple


class Recognizer:
    """Simple rule-based recognizer for quick prototype.

    Accepts landmarks dict and returns (label, confidence).
    """

    @staticmethod
    def simple_rule_recognize(landmarks: Dict[str, Dict[str, float]]) -> Tuple[str, float]:
        # If no landmarks, return unknown
        if not landmarks:
            return ("none", 0.0)

        # Indices: 0 - nose, 15 - left wrist, 16 - right wrist
        nose = landmarks.get('0')
        l_wr = landmarks.get('15')
        r_wr = landmarks.get('16')

        # simple rules: right hand above nose -> 'raise_right_hand'
        if r_wr and nose and r_wr['y'] < nose['y']:
            return ("raise_right_hand", 0.9)

        if l_wr and nose and l_wr['y'] < nose['y']:
            return ("raise_left_hand", 0.9)

        # default
        return ("none", 0.2)
