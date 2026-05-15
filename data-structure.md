# Data Structure Design - Multimodal Emotion State Monitor

## 1. 개요

본 문서는 프로젝트에서 사용하는 핵심 데이터 구조와 모듈 간 데이터 흐름을 정의합니다.

---

## 2. 핵심 데이터 타입

### 2.1 감정 카테고리 상수

```python
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

class Emotion(str, Enum):
    """9가지 감정 카테고리"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    STRESSED = "stressed"
    CALM = "calm"

EMOTIONS: List[str] = [e.value for e in Emotion]
```

### 2.2 얼굴 영역

```python
@dataclass
class FaceRegion:
    """감지된 얼굴 영역"""
    x: int       # 좌상단 x 좌표 (픽셀)
    y: int       # 좌상단 y 좌표 (픽셀)
    w: int       # 너비 (픽셀)
    h: int       # 높이 (픽셀)
    
    @property
    def area(self) -> int:
        """면적 계산 (가장 큰 얼굴 선택에 사용)"""
        return self.w * self.h
    
    @property
    def center(self) -> Tuple[int, int]:
        """중심 좌표"""
        return (self.x + self.w // 2, self.y + self.h // 2)
```

### 2.3 감정 점수

```python
@dataclass
class EmotionScores:
    """9가지 감정별 점수 (모든 분석 결과의 기본 단위)"""
    scores: Dict[str, float]     # {emotion: score}, 각 값은 0.0~1.0, 합계 ≈ 1.0
    dominant: str                # 최고 점수 감정 레이블
    confidence: float            # dominant 감정의 점수 (0.0~1.0)
    source: str = "unknown"      # "face", "voice", "integrated", "average", "predicted"
    timestamp: datetime = field(default_factory=datetime.now)
    
    @staticmethod
    def empty() -> "EmotionScores":
        """빈 결과 생성"""
        scores = {e: 0.0 for e in EMOTIONS}
        scores["neutral"] = 1.0
        return EmotionScores(
            scores=scores, dominant="neutral", 
            confidence=1.0, source="empty"
        )
    
    def to_array(self) -> List[float]:
        """EMOTIONS 순서대로 배열 변환 (LSTM 입력용)"""
        return [self.scores.get(e, 0.0) for e in EMOTIONS]
```

### 2.4 분석 주기 결과

```python
@dataclass
class AnalysisCycleResult:
    """한 분석 주기(5~20초)의 종합 결과"""
    cycle_id: int                              # 주기 번호
    cycle_seconds: int                         # 주기 길이 (초)
    cycle_start: datetime                      # 주기 시작 시각
    cycle_end: datetime                        # 주기 종료 시각
    
    # 분석 결과
    face_emotions: List[EmotionScores]         # 주기 내 표정 분석 결과들
    voice_emotion: Optional[EmotionScores]     # 음성 분석 결과 (주기 당 1개)
    integrated_emotions: List[EmotionScores]   # 통합 분석 결과들
    
    # 계산 결과
    average_emotion: Optional[EmotionScores]   # 주기 평균
    predicted_emotion: Optional[EmotionScores] # LSTM 예측
    comparison_label: Optional[str]            # 비교 결과 레이블
    comparison_magnitude: Optional[float]      # 변화 크기
    
    # 메타데이터
    analysis_mode: str = "integrated"          # face_only / voice_only / integrated
    face_detected: bool = True                 # 얼굴 감지 여부
    voice_detected: bool = True                # 음성 감지 여부
```

### 2.5 LSTM 예측 결과

```python
@dataclass
class PredictionResult:
    """LSTM 예측 상세 결과"""
    predicted_scores: EmotionScores            # 예측 감정 점수
    comparison_label: str                      # 변화 방향 레이블
    comparison_magnitude: float                # 변화 크기 (0.0~1.0)
    data_points_used: int                      # 예측에 사용된 데이터 수
    model_confidence: float                    # 모델 자체 신뢰도
    timestamp: datetime = field(default_factory=datetime.now)
```

### 2.6 UI 상태

```python
@dataclass
class AppState:
    """애플리케이션 전체 상태"""
    # 설정
    cycle_seconds: int = 10
    volume: int = 70
    analysis_mode: str = "integrated"  # face_only / voice_only / integrated
    voice_feedback_enabled: bool = True
    
    # 실행 상태
    is_running: bool = False
    camera_active: bool = False
    microphone_active: bool = False
    
    # 현재 결과
    current_face_emotion: Optional[EmotionScores] = None
    current_voice_emotion: Optional[EmotionScores] = None
    current_integrated_emotion: Optional[EmotionScores] = None
    average_emotion: Optional[EmotionScores] = None
    predicted_emotion: Optional[EmotionScores] = None
    comparison_label: Optional[str] = None
    comparison_magnitude: float = 0.0
    
    # 상태 메시지
    face_status: str = "대기 중"       # "사용 중", "얼굴 미감지", "비활성"
    voice_status: str = "대기 중"      # "사용 중", "음성 미감지", "비활성"
    lstm_status: str = "데이터 수집 중" # "예측 중", "데이터 수집 중", "비활성"
    
    # 로그
    log_messages: List[str] = field(default_factory=list)
    max_log_size: int = 50
```

### 2.7 설정값

```python
@dataclass
class Config:
    """전역 설정"""
    # 카메라
    camera_device_id: int = 0
    frame_width: int = 640
    frame_height: int = 480
    analysis_skip_frames: int = 3
    
    # 마이크
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_chunk_size: int = 1024
    silence_threshold: float = 0.01
    
    # 분석
    cycle_seconds: int = 10
    face_weight: float = 0.6     # 통합 시 표정 가중치
    voice_weight: float = 0.4    # 통합 시 음성 가중치
    
    # LSTM
    lstm_sequence_length: int = 10
    lstm_min_data_points: int = 5
    lstm_model_path: str = "models/lstm_model.h5"
    
    # TTS
    tts_enabled: bool = True
    tts_volume: int = 70
    tts_min_interval: int = 10   # 동일 메시지 최소 간격 (초)
    tts_max_repeat: int = 3      # 동일 메시지 최대 연속 횟수
    
    # UI
    window_title: str = "Multimodal Emotion State Monitor"
    log_max_size: int = 50
```

---

## 3. 모듈 간 데이터 흐름

### 3.1 데이터 흐름 다이어그램

```
webcam.py
│ → FaceRegion
│ → np.ndarray (frame)
▼
face_expression.py
│ → EmotionScores (source="face")
▼
emotion_integrator.py ◀── voice_emotion.py
│                          │ → EmotionScores (source="voice")
│                          │
│ → EmotionScores (source="integrated")
▼
emotion_averager.py
│ → EmotionScores (source="average")
│
├──▶ lstm_predictor.py
│    │ → EmotionScores (source="predicted")
│    ▼
│    emotion_comparator.py
│    │ → (label: str, magnitude: float)
│    ▼
│    voice_feedback.py
│    │ → 음성 출력
│
└──▶ UI (app.py)
     │ → 화면 표시
```

### 3.2 큐 기반 통신

```python
# 스레드 간 데이터 전달
from queue import Queue
from dataclasses import dataclass
from typing import Any

@dataclass
class QueueMessage:
    """큐 메시지 형식"""
    type: str              # "face_result", "voice_result", "average", "prediction", "log"
    data: Any              # EmotionScores, str, etc.
    timestamp: datetime = field(default_factory=datetime.now)

# 큐 정의
face_result_queue: Queue[QueueMessage]      # webcam → controller
voice_result_queue: Queue[QueueMessage]     # microphone → controller
ui_update_queue: Queue[QueueMessage]        # controller → UI
tts_queue: Queue[QueueMessage]              # controller → voice_feedback
log_queue: Queue[QueueMessage]              # all → UI log
```

---

## 4. 저장 데이터 형식

### 4.1 로그 파일 (JSON Lines)

```json
{"timestamp": "2026-05-15T14:30:10", "type": "analysis", "cycle_id": 1, "mode": "integrated", "result": {"dominant": "happy", "confidence": 0.85, "scores": {"neutral": 0.05, "happy": 0.85, "sad": 0.02, ...}}}
{"timestamp": "2026-05-15T14:30:10", "type": "average", "cycle_id": 1, "result": {"dominant": "calm", "confidence": 0.72, "scores": {...}}}
{"timestamp": "2026-05-15T14:30:10", "type": "prediction", "cycle_id": 1, "result": {"dominant": "neutral", "confidence": 0.65}, "comparison": {"label": "안정적", "magnitude": 0.03}}
{"timestamp": "2026-05-15T14:30:10", "type": "voice_feedback", "message": "현재 상태는 안정적으로 보입니다."}
```

### 4.2 설정 파일 (JSON)

```json
{
  "cycle_seconds": 10,
  "volume": 70,
  "analysis_mode": "integrated",
  "voice_feedback_enabled": true,
  "camera_device_id": 0,
  "face_weight": 0.6,
  "voice_weight": 0.4
}
```

---

## 5. 데이터 생명주기

| 데이터 유형 | 생성 시점 | 소멸 시점 | 최대 보존 |
|------------|-----------|-----------|-----------|
| 웹캠 프레임 | 매 프레임 | 분석 후 즉시 | 1개 (현재 프레임) |
| 얼굴 크롭 이미지 | 분석 시 | 분류 후 즉시 | 1개 |
| 오디오 버퍼 | 연속 축적 | 주기 종료 시 | 1주기분 |
| EmotionScores (개별) | 분석 완료 시 | 주기 종료 시 | 주기 내 결과 수 |
| EmotionScores (평균) | 주기 종료 시 | 다음 주기 종료 시 | 1개 (현재) |
| 시계열 버퍼 | 주기마다 추가 | 100개 초과 시 | 100개 |
| 로그 메시지 | 이벤트 발생 시 | UI 표시 후 | 50개 (UI), 무제한 (파일) |
