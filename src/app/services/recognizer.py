from typing import Dict, Tuple


class Recognizer:
    """Expanded rule-based recognizer.

    Heuristics implemented from pose landmarks (mediapipe pose):
    - raise_right_hand / raise_left_hand
    - both_hands_up
    - hands_close (possible clap)
    - wave (heuristic: wrist moves left-right rapidly — not implemented as temporal here)
    - point_left / point_right (wrist far from shoulder horizontally)

    Accepts landmarks dict and returns (label, confidence).
    """

    @staticmethod
    def _distance(a, b):
        return ((a['x'] - b['x']) ** 2 + (a['y'] - b['y']) ** 2) ** 0.5

    @staticmethod
    def simple_rule_recognize(landmarks: Dict[str, Dict[str, float]]) -> Tuple[str, float]:
        if not landmarks:
            return ("none", 0.0)

        nose = landmarks.get('0')
        l_sh = landmarks.get('11')
        r_sh = landmarks.get('12')
        l_wr = landmarks.get('15')
        r_wr = landmarks.get('16')

        # basic checks
        left_up = l_wr and nose and l_wr['y'] < nose['y']
        right_up = r_wr and nose and r_wr['y'] < nose['y']

        # both hands up
        if left_up and right_up:
            return ("both_hands_up", 0.95)

        # single hand raise
        if right_up:
            return ("raise_right_hand", 0.9)
        if left_up:
            return ("raise_left_hand", 0.9)

        # hands close together (possible clap)
        if l_wr and r_wr:
            d = Recognizer._distance(l_wr, r_wr)
            # normalize by shoulder width if available
            if l_sh and r_sh:
                shoulder = Recognizer._distance(l_sh, r_sh)
                if shoulder > 0:
                    norm = d / shoulder
                else:
                    norm = d
            else:
                norm = d
            if norm < 0.15:
                return ("hands_close", 0.8)

        # pointing heuristics: wrist significantly to left/right of shoulder
        if l_wr and l_sh:
            if l_wr['x'] < l_sh['x'] - 0.15:
                return ("point_left", 0.7)
        if r_wr and r_sh:
            if r_wr['x'] > r_sh['x'] + 0.15:
                return ("point_right", 0.7)

        return ("none", 0.1)
