"""
utils/data_types.py - 핵심 데이터 구조 정의
모든 모듈이 공유하는 데이터 타입을 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMOTIONS


class AnalysisMode(str, Enum):
    """분석 모드"""
    FACE_ONLY = "face_only"
    VOICE_ONLY = "voice_only"
    INTEGRATED = "integrated"


class ComparisonLabel(str, Enum):
    """감정 변화 방향 레이블"""
    STABLE = "안정적"
    POSITIVE = "긍정 방향 변화"
    NEGATIVE = "부정 방향 변화"
    STRESS_UP = "스트레스 증가 가능성"
    VOLATILE = "감정 변동성 증가"


@dataclass
class FaceRegion:
    """감지된 얼굴 영역"""
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


@dataclass
class EmotionScores:
    """9가지 감정별 점수 (모든 분석 결과의 기본 단위)"""
    scores: Dict[str, float]
    dominant: str
    confidence: float
    source: str = "unknown"  # face, voice, integrated, average, predicted
    timestamp: datetime = field(default_factory=datetime.now)

    @staticmethod
    def empty() -> "EmotionScores":
        """빈 결과 생성 (기본 neutral)"""
        scores = {e: 0.0 for e in EMOTIONS}
        scores["neutral"] = 1.0
        return EmotionScores(
            scores=scores,
            dominant="neutral",
            confidence=1.0,
            source="empty"
        )

    def to_array(self) -> List[float]:
        """EMOTIONS 순서대로 배열 변환 (LSTM 입력용)"""
        return [self.scores.get(e, 0.0) for e in EMOTIONS]

    def to_dict(self) -> Dict:
        """직렬화용 딕셔너리 변환"""
        return {
            "scores": self.scores,
            "dominant": self.dominant,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PredictionResult:
    """LSTM 예측 결과"""
    predicted_scores: EmotionScores
    comparison_label: str
    comparison_magnitude: float
    data_points_used: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CycleResult:
    """한 분석 주기의 종합 결과"""
    cycle_id: int
    cycle_seconds: int
    cycle_start: datetime
    cycle_end: datetime

    # 개별 결과
    face_emotions: List[EmotionScores] = field(default_factory=list)
    voice_emotion: Optional[EmotionScores] = None
    integrated_emotions: List[EmotionScores] = field(default_factory=list)

    # 계산 결과
    average_emotion: Optional[EmotionScores] = None
    predicted_emotion: Optional[EmotionScores] = None
    comparison_label: Optional[str] = None
    comparison_magnitude: float = 0.0

    # 메타
    analysis_mode: str = "integrated"
    face_detected: bool = False
    voice_detected: bool = False


@dataclass
class AppState:
    """UI 상태 관리"""
    # 설정
    cycle_seconds: int = 10
    volume: int = 70
    analysis_mode: str = "integrated"
    voice_feedback_enabled: bool = True

    # 실행 상태
    is_running: bool = False
    camera_active: bool = False
    microphone_active: bool = False

    # 현재 결과
    current_emotion: Optional[EmotionScores] = None
    average_emotion: Optional[EmotionScores] = None
    predicted_emotion: Optional[EmotionScores] = None
    comparison_label: Optional[str] = None
    comparison_magnitude: float = 0.0

    # 상태 메시지
    face_status: str = "대기 중"
    voice_status: str = "대기 중"
    lstm_status: str = "데이터 수집 중"

    # 로그
    log_messages: List[str] = field(default_factory=list)

    def add_log(self, message: str):
        """로그 메시지 추가 (최대 50개)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_messages.append(f"[{timestamp}] {message}")
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
