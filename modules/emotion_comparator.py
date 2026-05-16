"""
modules/emotion_comparator.py - 평균값 vs 예측값 비교 모듈
현재 평균 감정과 LSTM 예측 감정을 비교하여 변화 방향을 판단합니다.
"""

import numpy as np
from typing import Dict, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMOTIONS, EMOTION_VALENCE, Config, DEFAULT_CONFIG


class EmotionComparator:
    """평균 감정과 예측 감정 비교"""

    LABELS = {
        "STABLE": "안정적",
        "POSITIVE": "긍정 방향 변화",
        "NEGATIVE": "부정 방향 변화",
        "STRESS_UP": "스트레스 증가 가능성",
        "VOLATILE": "감정 변동성 증가",
    }

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config

    def compare(self, average: Dict[str, float],
                predicted: Dict[str, float]) -> Tuple[str, float]:
        """
        평균값과 예측값을 비교합니다.

        Args:
            average: 현재 주기 평균 감정 점수
            predicted: LSTM 예측 감정 점수

        Returns:
            (변화_방향_레이블, 변화_크기)
        """
        # Valence 계산
        avg_valence = self._calc_valence(average)
        pred_valence = self._calc_valence(predicted)

        diff = pred_valence - avg_valence
        magnitude = abs(diff)

        # 변동성 판단
        changes = [predicted.get(e, 0) - average.get(e, 0) for e in EMOTIONS]
        variance = float(np.std(changes))

        if variance > self.config.comparison_volatile_threshold:
            return self.LABELS["VOLATILE"], magnitude

        # 스트레스 증가 판단
        stress_change = (
            predicted.get("stressed", 0) - average.get("stressed", 0) +
            predicted.get("fearful", 0) - average.get("fearful", 0)
        )
        if stress_change > self.config.comparison_stress_threshold:
            return self.LABELS["STRESS_UP"], magnitude

        # 안정성 판단
        if magnitude < self.config.comparison_stable_threshold:
            return self.LABELS["STABLE"], magnitude

        # 방향 판단
        if diff > 0:
            return self.LABELS["POSITIVE"], magnitude
        else:
            return self.LABELS["NEGATIVE"], magnitude

    def _calc_valence(self, scores: Dict[str, float]) -> float:
        """감정 점수의 가중 valence 계산"""
        return sum(
            score * EMOTION_VALENCE.get(emotion, 0.0)
            for emotion, score in scores.items()
        )
