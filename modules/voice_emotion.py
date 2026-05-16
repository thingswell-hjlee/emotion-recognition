"""
modules/voice_emotion.py - 음성 감정 분류 모듈 (재설계)

인터페이스 패턴:
- BaseVoiceEmotionClassifier (추상 인터페이스)
- HeuristicVoiceEmotionClassifier (현재 기본, 규칙 기반)
- TrainedVoiceEmotionClassifier (향후 학습 모델 교체용)
- DummyVoiceEmotionClassifier (테스트용)

MVP 정책:
- happy, fearful, surprised는 학습 모델 없이는 기본 억제
- 출력 제한: neutral, calm, stressed, angry_low_confidence, sad_low_confidence
- 무음/데이터 부족 시 결과 생성 금지
- 랜덤 결과 사용 금지
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMOTIONS, Config, DEFAULT_CONFIG
from utils.data_types import EmotionScores
from modules.voice_features import VoiceFeatures


# === 분류 결과 상태 ===
VOICE_RESULT_OK = "EMOTION_CLASSIFIED"
VOICE_RESULT_LOW_CONFIDENCE = "LOW_CONFIDENCE"
VOICE_RESULT_SILENCE = "SILENCE_DETECTED"
VOICE_RESULT_INSUFFICIENT = "INSUFFICIENT_VOICE_DATA"
VOICE_RESULT_ERROR = "CLASSIFICATION_ERROR"
VOICE_RESULT_DISABLED = "MODULE_DISABLED"


@dataclass
class VoiceEmotionResult:
    """음성 감정 분류 결과 (상세)"""
    emotion: Optional[EmotionScores]
    status: str                    # EMOTION_CLASSIFIED / LOW_CONFIDENCE / etc.
    confidence_tier: str = "low"   # strong / usable / low / discard
    classifier_mode: str = "heuristic"
    reason: str = ""               # 판단 근거 설명


# === Base Interface ===

class BaseVoiceEmotionClassifier(ABC):
    """음성 감정 분류기 추상 인터페이스"""

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def classify(self, features: VoiceFeatures) -> VoiceEmotionResult:
        """VoiceFeatures를 입력받아 감정을 분류합니다."""
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        pass


# === Heuristic Classifier (MVP 기본) ===

class HeuristicVoiceEmotionClassifier(BaseVoiceEmotionClassifier):
    """
    규칙 기반 음성 감정 분류기.

    출력 제한 (학습 모델 없이 신뢰할 수 있는 것만):
    - neutral: 중간 에너지 + 안정적 피치
    - calm: 낮은 에너지 + 안정적 피치
    - stressed: 높은 에너지 + 큰 피치 변동 + 높은 ZCR
    - angry_low_confidence: 높은 에너지 + 낮은 피치
    - sad_low_confidence: 낮은 에너지 + 느린 리듬

    happy, fearful, surprised는 학습 모델 없이 억제.
    """

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._initialized = False

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def classify(self, features: VoiceFeatures) -> VoiceEmotionResult:
        """규칙 기반 분류"""
        if not features.is_valid:
            return VoiceEmotionResult(
                emotion=None,
                status=VOICE_RESULT_ERROR,
                reason=features.error or "Invalid features",
            )

        # 규칙 기반 판단
        emotion_label, confidence, reason = self._apply_rules(features)

        # confidence tier 결정
        tier = self._get_confidence_tier(confidence)

        # EmotionScores 생성
        scores = self._build_scores(emotion_label, confidence)

        return VoiceEmotionResult(
            emotion=EmotionScores(
                scores=scores,
                dominant=emotion_label,
                confidence=confidence,
                source="voice_heuristic",
            ),
            status=VOICE_RESULT_OK if tier != "discard" else VOICE_RESULT_LOW_CONFIDENCE,
            confidence_tier=tier,
            classifier_mode="heuristic",
            reason=reason,
        )

    @property
    def mode_name(self) -> str:
        return "heuristic baseline"

    def _apply_rules(self, f: VoiceFeatures) -> tuple:
        """
        규칙 기반 감정 판단.
        Returns: (emotion_label, confidence, reason)
        """
        rms = f.rms_mean
        pitch = f.pitch_mean
        pitch_std = f.pitch_std
        zcr = f.zcr
        energy_var = f.energy_variation

        # Rule 1: 높은 에너지 + 큰 피치 변동 + 높은 ZCR → stressed
        if rms > 0.04 and pitch_std > 40 and zcr > 0.08:
            confidence = min(0.75, 0.50 + rms * 2 + pitch_std * 0.005)
            return "stressed", confidence, f"high_energy({rms:.3f})+pitch_var({pitch_std:.1f})+zcr({zcr:.3f})"

        # Rule 2: 높은 에너지 + 낮은 피치 → angry (low confidence)
        if rms > 0.05 and pitch < 150 and energy_var > 0.5:
            confidence = min(0.60, 0.40 + rms * 2)
            return "angry", confidence, f"high_energy({rms:.3f})+low_pitch({pitch:.0f})+energy_var({energy_var:.2f})"

        # Rule 3: 낮은 에너지 + 느린 리듬 → sad (low confidence)
        if rms < 0.015 and pitch_std < 15 and energy_var < 0.3:
            confidence = min(0.55, 0.35 + (0.02 - rms) * 10)
            return "sad", confidence, f"low_energy({rms:.3f})+stable_pitch({pitch_std:.1f})"

        # Rule 4: 낮은 에너지 + 안정적 피치 → calm
        if rms < 0.025 and pitch_std < 25:
            confidence = 0.65
            return "calm", confidence, f"low_energy({rms:.3f})+stable({pitch_std:.1f})"

        # Rule 5: 중간 에너지 + 안정적 피치 → neutral (기본)
        confidence = 0.60
        return "neutral", confidence, f"default: rms={rms:.3f} pitch={pitch:.0f} std={pitch_std:.1f}"

    def _get_confidence_tier(self, confidence: float) -> str:
        """confidence 기준으로 tier 결정"""
        if confidence >= self.config.voice_confidence_strong:
            return "strong"
        elif confidence >= self.config.voice_confidence_usable:
            return "usable"
        elif confidence >= self.config.voice_confidence_low:
            return "low"
        else:
            return "discard"

    def _build_scores(self, dominant: str, confidence: float) -> Dict[str, float]:
        """감정 점수 분포 생성 (dominant 중심, 나머지는 낮게)"""
        scores = {e: 0.02 for e in EMOTIONS}
        scores[dominant] = confidence

        # 관련 감정에 약간의 점수 배분
        related = {
            "neutral": ["calm"],
            "calm": ["neutral"],
            "stressed": ["angry", "fearful"],
            "angry": ["stressed", "disgusted"],
            "sad": ["neutral", "calm"],
        }
        for rel in related.get(dominant, []):
            if rel in scores:
                scores[rel] = max(scores[rel], (1.0 - confidence) * 0.3)

        # 정규화
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores


# === Dummy Classifier (테스트용) ===

class DummyVoiceEmotionClassifier(BaseVoiceEmotionClassifier):
    """테스트용 더미 분류기 (항상 neutral 반환, 랜덤 없음)"""

    def initialize(self) -> bool:
        return True

    def classify(self, features: VoiceFeatures) -> VoiceEmotionResult:
        scores = {e: 0.05 for e in EMOTIONS}
        scores["neutral"] = 0.60
        total = sum(scores.values())
        scores = {k: v / total for k, v in scores.items()}

        return VoiceEmotionResult(
            emotion=EmotionScores(
                scores=scores,
                dominant="neutral",
                confidence=0.60,
                source="voice_dummy",
            ),
            status=VOICE_RESULT_OK,
            confidence_tier="usable",
            classifier_mode="dummy",
            reason="dummy_test_mode",
        )

    @property
    def mode_name(self) -> str:
        return "dummy test"


# === Factory ===

def create_voice_classifier(config: Config = DEFAULT_CONFIG) -> BaseVoiceEmotionClassifier:
    """설정에 따라 적절한 분류기 인스턴스 생성"""
    mode = config.voice_classifier_mode

    if mode == "heuristic":
        classifier = HeuristicVoiceEmotionClassifier(config)
    elif mode == "dummy":
        classifier = DummyVoiceEmotionClassifier()
    else:
        # trained model은 향후 구현
        classifier = HeuristicVoiceEmotionClassifier(config)

    classifier.initialize()
    return classifier
