"""
utils/data_types.py - 핵심 데이터 구조 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMOTIONS


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
    """9가지 감정별 점수"""
    scores: Dict[str, float]
    dominant: str
    confidence: float
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)

    @staticmethod
    def empty() -> "EmotionScores":
        scores = {e: 0.0 for e in EMOTIONS}
        scores["neutral"] = 1.0
        return EmotionScores(scores=scores, dominant="neutral", confidence=1.0, source="empty")

    def to_array(self) -> List[float]:
        return [self.scores.get(e, 0.0) for e in EMOTIONS]


@dataclass
class AppState:
    """UI 상태 관리"""
    # 설정
    run_mode: str = "minimal"
    cycle_seconds: int = 10
    volume: int = 70
    analysis_mode: str = "integrated"
    voice_feedback_enabled: bool = False  # 기본 OFF

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

    # 음성 파이프라인 상태 (새)
    voice_pipeline_state: Optional[object] = None  # VoicePipelineState

    # 로그
    log_messages: List[str] = field(default_factory=list)

    def add_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_messages.append(f"[{timestamp}] {message}")
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
