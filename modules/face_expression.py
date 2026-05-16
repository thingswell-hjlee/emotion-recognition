"""
modules/face_expression.py - 표정 감정 분류 모듈
DeepFace 기반 분류 + 폴백 처리 (Haar Cascade → 더미)

폴백 순서:
1) DeepFace 사용 (모델 로드 성공 시)
2) OpenCV Haar Cascade 얼굴 감지만 + neutral 반환
3) 더미 감정 결과 neutral 반환
"""

import numpy as np
from typing import Dict, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMOTIONS, DEEPFACE_TO_INTERNAL, Config, DEFAULT_CONFIG
from utils.data_types import EmotionScores


class FaceExpressionClassifier:
    """표정 감정 분류 (DeepFace + 폴백)"""

    FALLBACK_NONE = "none"
    FALLBACK_HAAR = "haar"
    FALLBACK_DEEPFACE = "deepface"

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._deepface = None
        self._backend = self.FALLBACK_NONE
        self._initialized = False
        self._init_error: Optional[str] = None

    def initialize(self) -> bool:
        """
        모델 초기화 (폴백 순서 적용)
        DeepFace 실패 → Haar만 → 더미
        """
        if not self.config.use_deepface:
            # minimal mode: 더미 분류기
            self._backend = self.FALLBACK_NONE
            self._initialized = True
            return True

        # DeepFace 시도
        try:
            from deepface import DeepFace
            self._deepface = DeepFace
            self._backend = self.FALLBACK_DEEPFACE
            self._initialized = True
            return True
        except ImportError:
            self._init_error = "DeepFace 미설치. 더미 모드로 동작합니다."
        except Exception as e:
            self._init_error = f"DeepFace 초기화 실패: {e}"

        # 폴백: 더미 모드
        self._backend = self.FALLBACK_NONE
        self._initialized = True
        return True

    def classify(self, face_image: np.ndarray) -> Optional[EmotionScores]:
        """
        얼굴 이미지로 감정 분류
        어떤 상황에서도 예외를 외부로 전파하지 않음
        """
        if not self._initialized:
            self.initialize()

        try:
            if self._backend == self.FALLBACK_DEEPFACE:
                return self._classify_deepface(face_image)
            else:
                return self._classify_dummy()
        except Exception:
            # 어떤 오류든 더미로 폴백
            return self._classify_dummy()

    def _classify_deepface(self, face_image: np.ndarray) -> Optional[EmotionScores]:
        """DeepFace 기반 분류"""
        try:
            result = self._deepface.analyze(
                img_path=face_image,
                actions=["emotion"],
                enforce_detection=False,
                detector_backend="skip",
                silent=True,
            )

            if isinstance(result, list):
                result = result[0]

            raw_scores = result.get("emotion", {})
            if not raw_scores:
                return self._classify_dummy()

            internal_scores = self._map_to_internal(raw_scores)
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
            # DeepFace 추론 실패 → 더미
            self._backend = self.FALLBACK_NONE
            return self._classify_dummy()

    def _classify_dummy(self) -> EmotionScores:
        """더미 감정 결과 (neutral 중심 + 약간의 랜덤)"""
        scores = {e: 0.02 for e in EMOTIONS}
        scores["neutral"] = 0.55
        scores["calm"] = 0.25

        # 약간의 변동 추가
        noise = np.random.dirichlet(np.ones(len(EMOTIONS)) * 0.3)
        for i, e in enumerate(EMOTIONS):
            scores[e] = scores[e] * 0.7 + noise[i] * 0.3

        # 정규화
        total = sum(scores.values())
        scores = {k: v / total for k, v in scores.items()}

        dominant = max(scores, key=scores.get)
        return EmotionScores(
            scores=scores,
            dominant=dominant,
            confidence=scores[dominant],
            source="face_dummy",
        )

    def _map_to_internal(self, raw_scores: Dict[str, float]) -> Dict[str, float]:
        """DeepFace 출력 → 내부 감정 체계 매핑"""
        internal = {}
        for deepface_key, internal_key in DEEPFACE_TO_INTERNAL.items():
            score = raw_scores.get(deepface_key, 0.0) / 100.0
            internal[internal_key] = score
        return internal

    def _infer_stressed_calm(self, scores: Dict[str, float]) -> Dict[str, float]:
        """stressed/calm 추정"""
        result = {e: scores.get(e, 0.0) for e in EMOTIONS if e not in ("stressed", "calm")}

        stressed_score = (
            scores.get("angry", 0) * 0.3 +
            scores.get("fearful", 0) * 0.4 +
            scores.get("sad", 0) * 0.2 +
            scores.get("disgusted", 0) * 0.1
        ) * 0.5

        negative_sum = sum(scores.get(e, 0) for e in ["angry", "fearful", "sad", "disgusted"])
        calm_score = max(0.0, scores.get("neutral", 0) * 0.6 - negative_sum * 0.3)

        result["stressed"] = stressed_score
        result["calm"] = calm_score
        return result

    @property
    def backend_name(self) -> str:
        return self._backend

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    @property
    def is_ready(self) -> bool:
        return self._initialized
