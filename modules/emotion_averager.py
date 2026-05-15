"""
modules/emotion_averager.py - 감정 평균 계산 모듈
주기 내 수집된 감정 결과를 시간 가중 평균으로 계산합니다.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional
from datetime import datetime
from config import EMOTIONS
from utils.data_types import EmotionScores


class EmotionAverager:
    """주기별 감정 평균 계산"""

    def __init__(self):
        self._results: List[EmotionScores] = []

    def add_result(self, result: EmotionScores):
        """분석 결과 추가"""
        self._results.append(result)

    def calculate_average(self) -> Optional[EmotionScores]:
        """
        현재 누적된 결과의 시간 가중 평균을 계산합니다.

        최근 결과에 더 높은 가중치를 부여합니다.

        Returns:
            평균 EmotionScores 또는 데이터 없으면 None
        """
        if not self._results:
            return None

        emotion_sums = {e: 0.0 for e in EMOTIONS}
        total_weight = 0.0

        for i, result in enumerate(self._results):
            # 시간 가중: 최근 결과에 더 높은 가중치
            weight = 1.0 + (i / len(self._results)) * 0.5

            for emotion in EMOTIONS:
                score = result.scores.get(emotion, 0.0)
                emotion_sums[emotion] += score * weight

            total_weight += weight

        # 평균 계산
        avg_scores = {e: s / total_weight for e, s in emotion_sums.items()}

        # 정규화
        total = sum(avg_scores.values())
        if total > 0:
            avg_scores = {e: s / total for e, s in avg_scores.items()}

        dominant = max(avg_scores, key=avg_scores.get)

        return EmotionScores(
            scores=avg_scores,
            dominant=dominant,
            confidence=avg_scores[dominant],
            source="average",
        )

    def reset(self):
        """누적 데이터 초기화 (주기 종료 또는 설정 변경 시)"""
        self._results.clear()

    @property
    def count(self) -> int:
        """누적된 결과 수"""
        return len(self._results)

    @property
    def has_data(self) -> bool:
        return len(self._results) > 0
