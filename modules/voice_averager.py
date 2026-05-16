"""
modules/voice_averager.py - 음성 감정 평균 계산 (confidence 가중)

분리된 평균 계산:
- face_average: 표정 분석 결과 평균
- voice_average: 음성 분석 결과 평균 (confidence 가중)
- integrated_average: face + voice 통합 (동적 가중치)
- final_average: 최종 결과

Confidence 가중치 정책:
- strong (>=0.75): weight 1.0
- usable (>=0.60): weight 0.7
- low (>=0.40): weight 0.2
- discard (<0.40): 평균에서 제외

Full mode 통합 가중치:
- 기본: face 0.7, voice 0.3
- voice heuristic + low confidence: voice 0.05~0.15
- voice_not_detected: voice 0.0
- insufficient_voice_data: voice 0.0
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMOTIONS, Config, DEFAULT_CONFIG
from utils.data_types import EmotionScores
from modules.voice_emotion import VoiceEmotionResult


@dataclass
class AverageResult:
    """평균 계산 결과"""
    emotion: Optional[EmotionScores]
    sample_count: int = 0
    total_weight: float = 0.0
    is_valid: bool = False


@dataclass
class IntegratedAverages:
    """분리된 평균들"""
    face_average: Optional[EmotionScores] = None
    voice_average: Optional[EmotionScores] = None
    integrated_average: Optional[EmotionScores] = None
    final_average: Optional[EmotionScores] = None

    # 적용된 가중치
    applied_face_weight: float = 1.0
    applied_voice_weight: float = 0.0
    voice_sample_count: int = 0
    face_sample_count: int = 0

    # 상태
    voice_status: str = "no_data"  # no_data / insufficient / valid
    reason: str = ""


class VoiceAverager:
    """
    음성 감정 결과를 confidence 가중으로 평균 계산.
    무음/low confidence 결과는 자동으로 제외 또는 낮은 가중치 적용.
    """

    # Confidence tier → 가중치 매핑
    TIER_WEIGHTS = {
        "strong": 1.0,
        "usable": 0.7,
        "low": 0.2,
        "discard": 0.0,
    }

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._voice_results: List[Tuple[EmotionScores, float]] = []  # (result, weight)
        self._face_results: List[EmotionScores] = []

    def add_voice_result(self, result: VoiceEmotionResult):
        """
        음성 분류 결과 추가.
        confidence tier에 따라 가중치가 자동으로 결정됩니다.
        discard tier는 추가되지 않습니다.
        """
        if result.emotion is None:
            return
        if result.confidence_tier == "discard":
            return

        weight = self.TIER_WEIGHTS.get(result.confidence_tier, 0.0)
        if weight > 0:
            self._voice_results.append((result.emotion, weight))

    def add_face_result(self, result: EmotionScores):
        """표정 분석 결과 추가"""
        self._face_results.append(result)

    def calculate_averages(self) -> IntegratedAverages:
        """
        face, voice, integrated, final 평균을 모두 계산합니다.
        """
        result = IntegratedAverages()

        # Face average
        if self._face_results:
            result.face_average = self._calculate_simple_average(self._face_results)
            result.face_sample_count = len(self._face_results)

        # Voice average (confidence weighted)
        if self._voice_results:
            result.voice_average = self._calculate_weighted_average(self._voice_results)
            result.voice_sample_count = len(self._voice_results)
            result.voice_status = "valid"
        else:
            result.voice_status = "no_data"

        # Integrated average (Full mode)
        result.integrated_average, result.applied_face_weight, result.applied_voice_weight = \
            self._calculate_integrated(result)

        # Final average (모드에 따라)
        if result.integrated_average:
            result.final_average = result.integrated_average
        elif result.face_average:
            result.final_average = result.face_average
            result.reason = "voice 무효, face only"
        elif result.voice_average:
            result.final_average = result.voice_average
            result.reason = "face 무효, voice only"

        return result

    def reset(self):
        """주기 종료 시 초기화"""
        self._voice_results.clear()
        self._face_results.clear()

    @property
    def voice_count(self) -> int:
        return len(self._voice_results)

    @property
    def face_count(self) -> int:
        return len(self._face_results)

    def _calculate_simple_average(self, results: List[EmotionScores]) -> Optional[EmotionScores]:
        """단순 시간 가중 평균 (face용)"""
        if not results:
            return None

        avg_scores = {e: 0.0 for e in EMOTIONS}
        total_weight = 0.0

        for i, r in enumerate(results):
            weight = 1.0 + (i / len(results)) * 0.5  # 최근 결과에 더 높은 가중치
            for e in EMOTIONS:
                avg_scores[e] += r.scores.get(e, 0.0) * weight
            total_weight += weight

        avg_scores = {e: s / total_weight for e, s in avg_scores.items()}
        total = sum(avg_scores.values())
        if total > 0:
            avg_scores = {e: s / total for e, s in avg_scores.items()}

        dominant = max(avg_scores, key=avg_scores.get)
        return EmotionScores(
            scores=avg_scores,
            dominant=dominant,
            confidence=avg_scores[dominant],
            source="face_average",
        )

    def _calculate_weighted_average(self, results: List[Tuple[EmotionScores, float]]) -> Optional[EmotionScores]:
        """confidence 가중 평균 (voice용)"""
        if not results:
            return None

        avg_scores = {e: 0.0 for e in EMOTIONS}
        total_weight = 0.0

        for emotion, weight in results:
            for e in EMOTIONS:
                avg_scores[e] += emotion.scores.get(e, 0.0) * weight
            total_weight += weight

        if total_weight == 0:
            return None

        avg_scores = {e: s / total_weight for e, s in avg_scores.items()}
        total = sum(avg_scores.values())
        if total > 0:
            avg_scores = {e: s / total for e, s in avg_scores.items()}

        dominant = max(avg_scores, key=avg_scores.get)
        return EmotionScores(
            scores=avg_scores,
            dominant=dominant,
            confidence=avg_scores[dominant],
            source="voice_average",
        )

    def _calculate_integrated(self, avgs: IntegratedAverages) -> Tuple[Optional[EmotionScores], float, float]:
        """
        face + voice 통합 평균 (동적 가중치).
        voice가 무효이면 face만 사용.
        """
        face = avgs.face_average
        voice = avgs.voice_average

        # 둘 다 없으면
        if face is None and voice is None:
            return None, 0.0, 0.0

        # voice만 있으면
        if face is None and voice is not None:
            return voice, 0.0, 1.0

        # face만 있으면
        if face is not None and voice is None:
            return EmotionScores(
                scores=face.scores.copy(),
                dominant=face.dominant,
                confidence=face.confidence,
                source="integrated_face_only",
            ), 1.0, 0.0

        # 둘 다 있으면: 동적 가중치 적용
        # voice confidence에 따라 voice_weight 결정
        voice_conf = voice.confidence if voice else 0.0
        if voice_conf >= self.config.voice_confidence_strong:
            voice_w = self.config.voice_weight_strong
        elif voice_conf >= self.config.voice_confidence_usable:
            voice_w = self.config.voice_weight_usable
        elif voice_conf >= self.config.voice_confidence_low:
            voice_w = self.config.voice_weight_low
        else:
            voice_w = 0.0

        face_w = 1.0 - voice_w

        # 가중 평균 계산
        integrated_scores = {}
        for e in EMOTIONS:
            f_score = face.scores.get(e, 0.0) if face else 0.0
            v_score = voice.scores.get(e, 0.0) if voice else 0.0
            integrated_scores[e] = f_score * face_w + v_score * voice_w

        # 정규화
        total = sum(integrated_scores.values())
        if total > 0:
            integrated_scores = {k: v / total for k, v in integrated_scores.items()}

        dominant = max(integrated_scores, key=integrated_scores.get)

        return EmotionScores(
            scores=integrated_scores,
            dominant=dominant,
            confidence=integrated_scores[dominant],
            source="integrated",
        ), face_w, voice_w
