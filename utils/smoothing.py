"""
utils/smoothing.py - 결과 안정화 모듈
이동평균(moving average)과 confidence threshold 적용으로
단일 프레임 노이즈를 제거하고 안정적인 감정 결과를 제공합니다.

기능:
1. 최근 N회 결과의 이동평균 계산
2. confidence threshold 미만이면 "low confidence" 마킹
3. majority voting (dominant 감정 기준)
4. recent trend 계산 (최근 결과에서 dominant 감정의 빈도)
"""

from collections import deque
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMOTIONS
from utils.data_types import EmotionScores


class EmotionSmoother:
    """
    감정 결과 안정화.
    최근 N회 결과를 유지하면서 이동평균, majority voting, trend를 제공합니다.
    """

    def __init__(self, window_size: int = 4, confidence_threshold: float = 0.6):
        """
        Args:
            window_size: 이동평균 윈도우 크기 (3~5 권장)
            confidence_threshold: 이 값 미만이면 low confidence 표시
        """
        self.window_size = max(1, window_size)
        self.confidence_threshold = confidence_threshold
        self._history: deque = deque(maxlen=self.window_size)

    def add(self, result: EmotionScores):
        """새 분석 결과를 히스토리에 추가"""
        self._history.append(result)

    def get_smoothed(self) -> Optional[EmotionScores]:
        """
        이동평균 적용된 안정화 결과를 반환합니다.

        Returns:
            smoothed EmotionScores 또는 데이터 없으면 None
        """
        if not self._history:
            return None

        if len(self._history) == 1:
            # 데이터 1개면 그대로 반환 (source만 변경)
            single = self._history[0]
            return EmotionScores(
                scores=single.scores.copy(),
                dominant=single.dominant,
                confidence=single.confidence,
                source="smoothed",
            )

        # 이동평균 계산 (최근 결과에 더 높은 가중치)
        avg_scores = {e: 0.0 for e in EMOTIONS}
        total_weight = 0.0

        for i, result in enumerate(self._history):
            # 최근 결과에 선형적으로 더 높은 가중치
            weight = 1.0 + (i / len(self._history))
            for emotion in EMOTIONS:
                avg_scores[emotion] += result.scores.get(emotion, 0.0) * weight
            total_weight += weight

        # 평균
        avg_scores = {e: s / total_weight for e, s in avg_scores.items()}

        # 정규화
        total = sum(avg_scores.values())
        if total > 0:
            avg_scores = {e: s / total for e, s in avg_scores.items()}

        dominant = max(avg_scores, key=avg_scores.get)
        confidence = avg_scores[dominant]

        return EmotionScores(
            scores=avg_scores,
            dominant=dominant,
            confidence=confidence,
            source="smoothed",
        )

    def get_majority_vote(self) -> Optional[str]:
        """
        Majority voting: 최근 N회에서 가장 빈번한 dominant 감정 반환.

        Returns:
            감정 레이블 또는 None
        """
        if not self._history:
            return None

        counts: Dict[str, int] = {}
        for result in self._history:
            counts[result.dominant] = counts.get(result.dominant, 0) + 1

        return max(counts, key=counts.get)

    def get_trend(self) -> List[Tuple[str, float]]:
        """
        Recent trend: 최근 결과들의 dominant 감정 빈도를 비율로 반환.

        Returns:
            [(감정, 비율), ...] 빈도 내림차순
        """
        if not self._history:
            return []

        counts: Dict[str, int] = {}
        for result in self._history:
            counts[result.dominant] = counts.get(result.dominant, 0) + 1

        total = len(self._history)
        trend = [(e, c / total) for e, c in counts.items()]
        trend.sort(key=lambda x: x[1], reverse=True)
        return trend

    def is_low_confidence(self, result: Optional[EmotionScores] = None) -> bool:
        """
        confidence가 threshold 미만인지 확인.

        Args:
            result: 확인할 결과. None이면 최신 smoothed 결과를 사용.
        """
        if result is None:
            result = self.get_smoothed()
        if result is None:
            return True
        return result.confidence < self.confidence_threshold

    def update_window_size(self, new_size: int):
        """윈도우 크기 변경 (기존 데이터는 유지, 초과분만 제거)"""
        new_size = max(1, new_size)
        if new_size != self.window_size:
            self.window_size = new_size
            # deque의 maxlen 변경은 불가하므로 새로 생성
            old_data = list(self._history)
            self._history = deque(old_data[-new_size:], maxlen=new_size)

    def update_threshold(self, new_threshold: float):
        """confidence threshold 변경"""
        self.confidence_threshold = max(0.0, min(1.0, new_threshold))

    def reset(self):
        """히스토리 초기화"""
        self._history.clear()

    @property
    def count(self) -> int:
        """현재 히스토리 크기"""
        return len(self._history)

    @property
    def is_full(self) -> bool:
        """윈도우가 가득 찼는지"""
        return len(self._history) >= self.window_size
