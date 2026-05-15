"""
modules/face_expression.py - 표정 감정 분류 모듈
DeepFace를 사용하여 얼굴 이미지의 감정을 분류합니다.
"""

import numpy as np
from typing import Dict, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMOTIONS, DEEPFACE_TO_INTERNAL
from utils.data_types import EmotionScores


class FaceExpressionClassifier:
    """DeepFace 기반 표정 감정 분류"""

    def __init__(self):
        self._initialized = False
        self._deepface = None

    def initialize(self) -> bool:
        """모델 로드 (Lazy initialization)"""
        try:
            from deepface import DeepFace
            self._deepface = DeepFace
            self._initialized = True
            return True
        except ImportError:
            print("[ERROR] DeepFace가 설치되지 않았습니다: pip install deepface")
            return False
        except Exception as e:
            print(f"[ERROR] 표정 분류기 초기화 실패: {e}")
            return False

    def classify(self, face_image: np.ndarray) -> Optional[EmotionScores]:
        """
        얼굴 이미지를 입력받아 감정을 분류합니다.

        Args:
            face_image: 크롭된 얼굴 BGR 이미지 (numpy array)

        Returns:
            EmotionScores 또는 실패 시 None
        """
        if not self._initialized:
            if not self.initialize():
                return None

        try:
            result = self._deepface.analyze(
                img_path=face_image,
                actions=["emotion"],
                enforce_detection=False,
                detector_backend="skip",  # 이미 크롭된 얼굴이므로 감지 스킵
                silent=True,
            )

            if isinstance(result, list):
                result = result[0]

            raw_scores = result.get("emotion", {})
            if not raw_scores:
                return None

            # DeepFace 7개 감정 → 내부 9개 감정으로 매핑
            internal_scores = self._map_to_internal(raw_scores)

            # stressed/calm 추정
            full_scores = self._infer_stressed_calm(internal_scores)

            # 정규화
            total = sum(full_scores.values())
            if total > 0:
                full_scores = {k: v / total for k, v in full_scores.items()}

            dominant = max(full_scores, key=full_scores.get)

            return EmotionScores(
                scores=full_scores,
                dominant=dominant,
                confidence=full_scores[dominant],
                source="face",
            )

        except Exception:
            return None

    def _map_to_internal(self, raw_scores: Dict[str, float]) -> Dict[str, float]:
        """DeepFace 출력을 내부 감정 체계로 매핑"""
        internal = {}
        for deepface_key, internal_key in DEEPFACE_TO_INTERNAL.items():
            score = raw_scores.get(deepface_key, 0.0) / 100.0  # 0~100 → 0~1
            internal[internal_key] = score
        return internal

    def _infer_stressed_calm(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        stressed/calm 추정 (표정 모델에서 직접 분류하지 않는 감정)
        
        stressed: 부정 감정 조합으로 추정
        calm: neutral 높고 부정 감정 낮을 때 추정
        """
        result = {e: scores.get(e, 0.0) for e in EMOTIONS if e not in ("stressed", "calm")}

        # stressed: angry + fearful + sad 조합
        stressed_score = (
            scores.get("angry", 0) * 0.3 +
            scores.get("fearful", 0) * 0.4 +
            scores.get("sad", 0) * 0.2 +
            scores.get("disgusted", 0) * 0.1
        ) * 0.5

        # calm: neutral 높고 부정 감정 낮으면
        negative_sum = sum(scores.get(e, 0) for e in
                          ["angry", "fearful", "sad", "disgusted"])
        calm_score = max(0.0, scores.get("neutral", 0) * 0.6 - negative_sum * 0.3)

        result["stressed"] = stressed_score
        result["calm"] = calm_score

        return result

    @property
    def is_ready(self) -> bool:
        return self._initialized
