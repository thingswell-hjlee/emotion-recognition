# Architecture - Multimodal Emotion State Monitor

## 1. Architecture Overview

본 문서는 `multimodal-emotion-state-monitor` 프로젝트의 시스템 아키텍처를 정의합니다.
이 프로그램은 노트북의 웹캠과 마이크를 통해 사용자의 얼굴 표정과 음성을 분석하고,
감정 상태를 주기적으로 계산하여 음성 안내와 LSTM 기반 예측을 제공합니다.

### 설계 원칙

| 원칙 | 설명 |
|------|------|
| 로컬 우선 | 모든 처리는 로컬 PC에서만 수행, 외부 서버 전송 없음 |
| 모듈 분리 | 각 기능을 독립 모듈로 분리하여 유지보수성 및 확장성 확보 |
| 프라이버시 중심 | 영상/음성 원본 저장 금지, 메모리 내 처리 후 즉시 폐기 |
| 비동기 처리 | UI 응답성 확보를 위한 분석 파이프라인 비동기 실행 |
| 점진적 확장 | 초기 MVP 로컬 실행 → 향후 AWS 연동 가능한 구조 |

---

## 2. System Goals

### 핵심 목표

1. **실시간 멀티모달 감정 인식**: 표정 + 음성 기반 감정 상태 분류 (9가지)
2. **주기적 감정 평균 계산**: 5~20초 주기(기본 10초)로 감정 추세 파악
3. **LSTM 기반 감정 예측**: 시계열 데이터 기반 다음 감정 상태 예측
4. **감정 변화 방향 판단**: 평균값과 예측값 비교를 통한 변화 추세 제공
5. **음성 안내**: 감정 상태를 짧은 문장으로 음성 출력
6. **사용자 제어 UI**: 설정 조정, 시작/정지, 실시간 결과 표시

### 품질 목표

| 목표 | 기준 |
|------|------|
| 성능 | 영상 10 FPS 이상, 분석은 주기 내 완료 |
| 메모리 | 2GB 이하 (모델 포함) |
| CPU 호환 | GPU 없이 동작 |
| 프라이버시 | 영상/음성 저장 없음, 네트워크 전송 없음 |

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Local PC (오프라인 실행)                           │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         UI Layer (Streamlit/PyQt)                  │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │  │
│  │  │ Settings│ │ Controls │ │ Current  │ │ Average  │ │  LSTM  │ │  │
│  │  │  Panel  │ │Start/Stop│ │ Emotion  │ │ Emotion  │ │Predict │ │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Core Controller (Orchestrator)                │  │
│  │                  - 주기 타이머 관리                                  │  │
│  │                  - 모듈 간 데이터 흐름 조율                           │  │
│  │                  - 시작/정지 상태 관리                                │  │
│  └──────────┬──────────────┬──────────────┬──────────────┬───────────┘  │
│             │              │              │              │               │
│             ▼              ▼              ▼              ▼               │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────────────┐  │
│  │  Webcam      │ │  Microphone  │ │  Emotion  │ │  Voice Feedback  │  │
│  │  Module      │ │  Module      │ │  Analyzer │ │  Module          │  │
│  │  - 캡처      │ │  - 수집      │ │  - 통합   │ │  - TTS 출력      │  │
│  │  - 얼굴감지  │ │  - 버퍼관리  │ │  - 평균   │ │  - 볼륨 제어     │  │
│  └──────┬───────┘ └──────┬───────┘ │  - 비교   │ └──────────────────┘  │
│         │                │         └─────┬─────┘                        │
│         ▼                ▼               │                              │
│  ┌──────────────┐ ┌──────────────┐       │                              │
│  │  Face        │ │  Voice       │       ▼                              │
│  │  Expression  │ │  Emotion     │ ┌───────────┐                        │
│  │  Classifier  │ │  Classifier  │ │  LSTM     │                        │
│  │  (DeepFace)  │ │  (librosa)   │ │  Predictor│                        │
│  └──────────────┘ └──────────────┘ └───────────┘                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Module Design

### 4.1 모듈 구성 및 파일 구조

```
multimodal-emotion-state-monitor/
├── main.py                      # 엔트리포인트
├── config.py                    # 전역 설정 상수
├── controller.py                # Core Controller (오케스트레이터)
├── modules/
│   ├── __init__.py
│   ├── webcam.py                # 웹캠 캡처 및 얼굴 감지
│   ├── face_expression.py       # 표정 감정 분류
│   ├── microphone.py            # 마이크 오디오 수집
│   ├── voice_emotion.py         # 음성 감정 분류
│   ├── emotion_integrator.py    # 멀티모달 감정 통합
│   ├── emotion_averager.py      # 주기별 평균 계산
│   ├── lstm_predictor.py        # LSTM 기반 감정 예측
│   ├── emotion_comparator.py    # 평균 vs 예측 비교
│   └── voice_feedback.py        # 음성 안내 출력
├── ui/
│   ├── __init__.py
│   └── app.py                   # Streamlit/PyQt UI
├── models/
│   ├── lstm_model.h5            # LSTM 모델 파일 (초기: 더미)
│   └── model_utils.py           # 모델 로드/추론 유틸리티
├── utils/
│   ├── __init__.py
│   ├── logger.py                # 로그 관리
│   ├── timer.py                 # 주기 타이머
│   └── data_types.py            # 공통 데이터 구조 정의
├── requirements.txt
├── requirements.md
├── architecture.md
└── README.md
```

### 4.2 모듈별 역할, 입출력, 라이브러리, 연결 관계

| 모듈 | 역할 | 입력값 | 출력값 | 주요 라이브러리 | 연결 모듈 |
|------|------|--------|--------|-----------------|-----------|
| `webcam.py` | 웹캠 프레임 캡처, 얼굴 영역 감지 | 카메라 장치 ID | BGR 프레임, 얼굴 좌표 리스트 | OpenCV, MediaPipe | → face_expression |
| `face_expression.py` | 얼굴 이미지로 감정 분류 | 얼굴 이미지 (numpy) | 감정 레이블, 9개 감정 점수 딕셔너리 | DeepFace / MediaPipe | → emotion_integrator |
| `microphone.py` | 마이크 오디오 캡처, 버퍼 관리 | 마이크 장치 ID, 주기 설정 | 오디오 버퍼 (numpy, 16kHz) | PyAudio / sounddevice | → voice_emotion |
| `voice_emotion.py` | 음성 특징 추출 및 감정 분류 | 오디오 버퍼 (numpy) | 감정 레이블, 9개 감정 점수 딕셔너리 | librosa, scikit-learn | → emotion_integrator |
| `emotion_integrator.py` | 표정+음성 감정 가중 통합 | 표정 점수, 음성 점수, 분석 모드 | 통합 감정 레이블, 통합 점수 딕셔너리 | NumPy | → emotion_averager |
| `emotion_averager.py` | 주기 내 감정 결과 평균 계산 | 감정 결과 리스트, 주기 설정값 | 평균 감정 레이블, 평균 점수 딕셔너리 | NumPy, Pandas | → lstm_predictor, voice_feedback, UI |
| `lstm_predictor.py` | 시계열 기반 다음 감정 예측 | 최근 N개 주기 감정 데이터 | 예측 감정 레이블, 예측 점수 딕셔너리 | TensorFlow/PyTorch | → emotion_comparator |
| `emotion_comparator.py` | 평균값 vs 예측값 비교, 변화 방향 판단 | 평균 점수, 예측 점수 | 변화 방향 레이블, 변화 크기 | NumPy | → UI, voice_feedback |
| `voice_feedback.py` | 감정 상태 음성 안내 출력 | 평균 감정, 비교 결과, 볼륨/ON-OFF | 음성 출력 (스피커) | pyttsx3 / edge-tts | ← emotion_averager, comparator |
| `controller.py` | 전체 파이프라인 조율, 타이머, 상태 관리 | UI 설정값, 시작/정지 신호 | 각 모듈 호출 및 결과 전달 | threading, asyncio | ↔ 모든 모듈 |
| `ui/app.py` | 사용자 설정 UI, 결과 표시, 제어 | 사용자 조작 | 설정값, 시작/정지 이벤트 | Streamlit / PyQt | ↔ controller |

---

## 5. Data Flow

### 5.1 전체 데이터 흐름도

```
[사용자 시작 버튼 클릭]
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Core Controller (주기 타이머 시작)            │
│                                                         │
│   매 프레임 (연속):          매 주기 (N초마다):             │
│   ┌──────────────┐         ┌────────────────────────┐   │
│   │ Webcam 캡처  │         │ 주기 완료 트리거         │   │
│   │ → 얼굴 감지  │         │                        │   │
│   │ → 표정 분류  │─────────▶│ ① 감정 평균 계산       │   │
│   └──────────────┘         │ ② LSTM 예측            │   │
│                            │ ③ 평균 vs 예측 비교     │   │
│   ┌──────────────┐         │ ④ 음성 안내 출력       │   │
│   │ Mic 수집     │         │ ⑤ UI 업데이트          │   │
│   │ → 음성 분류  │─────────▶│                        │   │
│   └──────────────┘         └────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
         │
         ▼
[UI에 결과 표시 + 콘솔 로그]
```

### 5.2 데이터 타입 정의

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

EMOTIONS = ["neutral", "happy", "sad", "angry", "surprised",
            "fearful", "disgusted", "stressed", "calm"]

@dataclass
class EmotionScores:
    """9가지 감정별 점수"""
    scores: Dict[str, float]  # {emotion: score} 각 값은 0.0~1.0
    dominant: str             # 최고 점수 감정
    confidence: float         # dominant 감정의 신뢰도
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AnalysisCycleResult:
    """한 주기의 분석 결과"""
    face_emotion: Optional[EmotionScores]    # 표정 분석 결과
    voice_emotion: Optional[EmotionScores]   # 음성 분석 결과
    integrated_emotion: Optional[EmotionScores]  # 통합 결과
    cycle_start: datetime
    cycle_end: datetime

@dataclass
class PredictionResult:
    """LSTM 예측 결과"""
    predicted_emotion: EmotionScores
    comparison_label: str      # 안정적, 긍정 변화, 부정 변화, ...
    change_magnitude: float    # 변화 크기 (0.0~1.0)
```



---

## 6. Emotion Analysis Flow

### 6.1 표정 분석 파이프라인

```
[웹캠 프레임 캡처]
       │
       ▼
[전처리: 그레이스케일 변환, 리사이즈]
       │
       ▼
[얼굴 감지: MediaPipe / Haar Cascade]
       │
       ├── 얼굴 미감지 → "얼굴 미감지" 상태 반환
       │
       ▼ (얼굴 감지됨)
[얼굴 영역 크롭 + 정규화]
       │
       ▼
[DeepFace / MediaPipe 감정 분류]
       │
       ▼
[EmotionScores 생성 (9가지 감정 점수)]
       │
       ▼
[emotion_integrator로 전달]
```

### 6.2 표정 분석 세부 사항

| 단계 | 처리 내용 | 소요 시간 목표 |
|------|-----------|---------------|
| 프레임 캡처 | 카메라에서 BGR 프레임 읽기 | < 33ms (30 FPS) |
| 전처리 | 그레이스케일 변환, 히스토그램 정규화 | < 5ms |
| 얼굴 감지 | 바운딩 박스 좌표 추출 | < 50ms |
| 표정 분류 | CNN 기반 감정 분류 | < 200ms |
| 총 파이프라인 | 캡처 → 결과 | < 300ms |

### 6.3 지원 감정 매핑 (DeepFace → 내부 체계)

```python
DEEPFACE_TO_INTERNAL = {
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
    "surprise": "surprised",
    "neutral": "neutral",
    "fear": "fearful",
    "disgust": "disgusted",
}
# stressed, calm은 표정만으로 구분 어려움 → 음성 분석 보완 필요
```

---

## 7. Voice Analysis Flow

### 7.1 음성 분석 파이프라인

```
[마이크 오디오 스트림 캡처]
       │
       ▼
[오디오 버퍼 축적 (주기만큼)]
       │
       ├── 무음 감지 → "음성 미감지" 상태 반환
       │
       ▼ (유효한 음성)
[전처리: 노이즈 제거, 정규화]
       │
       ▼
[특징 추출]
│   ├── MFCC (13~40 계수)
│   ├── Mel Spectrogram
│   ├── 피치 (F0)
│   ├── 에너지 (RMS)
│   ├── Zero-Crossing Rate
│   └── Spectral Centroid
       │
       ▼
[감정 분류 모델 추론]
       │
       ▼
[EmotionScores 생성 (9가지 감정 점수)]
       │
       ▼
[emotion_integrator로 전달]
```

### 7.2 음성 특징 상세

| 특징 | 라이브러리 | 감정 관련성 |
|------|-----------|------------|
| MFCC (13계수) | librosa | 음색, 발화 패턴 |
| Mel Spectrogram | librosa | 전체 주파수 분포 |
| Pitch (F0) | librosa | 흥분도, 긴장도 (높을수록 흥분/긴장) |
| Energy (RMS) | librosa | 감정 강도 (높을수록 강한 감정) |
| Zero-Crossing Rate | librosa | 노이즈, 발화 특성 |
| Spectral Centroid | librosa | 밝은/어두운 톤 구분 |

### 7.3 음성 기반 감정 분류 접근법

- **초기 MVP**: scikit-learn 기반 SVM 또는 Random Forest 분류기
- **학습 데이터**: RAVDESS, TESS 등 공개 감정 음성 데이터셋 활용
- **향후 확장**: CNN 또는 Transformer 기반 모델로 교체 가능

### 7.4 오디오 버퍼 관리

```python
class AudioBufferManager:
    """주기에 맞춰 오디오 버퍼를 관리"""
    
    def __init__(self, sample_rate=16000, cycle_seconds=10):
        self.sample_rate = sample_rate
        self.cycle_seconds = cycle_seconds
        self.buffer_size = sample_rate * cycle_seconds
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
    
    def is_silence(self, threshold=0.01) -> bool:
        """무음 여부 판단"""
        return np.max(np.abs(self.buffer)) < threshold
```

---

## 8. Emotion Averaging Logic

### 8.1 주기적 평균 계산 흐름

```
[주기 시작 (T=0)]
       │
       ▼
[분석 결과 수집 (주기 동안)]
│   ├── t=0s:   EmotionScores_1
│   ├── t=2s:   EmotionScores_2
│   ├── t=4s:   EmotionScores_3
│   ├── t=6s:   EmotionScores_4
│   └── t=8s:   EmotionScores_5
       │
       ▼ (주기 종료, T=10s)
[시간 가중 평균 계산]
       │
       ▼
[대표 감정 선정 (최고 점수)]
       │
       ├──▶ [UI 표시: "최근 평균 감정"]
       ├──▶ [LSTM 시계열 데이터에 추가]
       ├──▶ [음성 안내 트리거]
       └──▶ [다음 주기 시작]
```

### 8.2 평균 계산 알고리즘

```python
def calculate_emotion_average(results: List[EmotionScores], 
                               cycle_seconds: int) -> EmotionScores:
    """
    주기 내 감정 분석 결과의 시간 가중 평균을 계산합니다.
    
    Args:
        results: 주기 내 수집된 EmotionScores 리스트
        cycle_seconds: 주기 길이 (초)
    
    Returns:
        평균 EmotionScores
    """
    if not results:
        return None  # "데이터 부족" 상태
    
    # 각 감정별 점수 합산
    emotion_sums = {emotion: 0.0 for emotion in EMOTIONS}
    total_weight = 0.0
    
    for i, result in enumerate(results):
        # 최근 결과에 더 높은 가중치 부여 (시간 가중)
        weight = 1.0 + (i / len(results)) * 0.5
        for emotion, score in result.scores.items():
            emotion_sums[emotion] += score * weight
        total_weight += weight
    
    # 평균 계산
    avg_scores = {e: s / total_weight for e, s in emotion_sums.items()}
    
    # 정규화 (합이 1.0이 되도록)
    total = sum(avg_scores.values())
    if total > 0:
        avg_scores = {e: s / total for e, s in avg_scores.items()}
    
    dominant = max(avg_scores, key=avg_scores.get)
    
    return EmotionScores(
        scores=avg_scores,
        dominant=dominant,
        confidence=avg_scores[dominant]
    )
```

### 8.3 주기 설정과 처리 흐름 반영

사용자가 설정하는 **감정 인식 주기 (5~20초)**는 다음과 같이 시스템 전체에 반영됩니다:

| 영향받는 항목 | 반영 방식 |
|--------------|-----------|
| 오디오 버퍼 크기 | `sample_rate × cycle_seconds` 만큼 축적 |
| 감정 평균 계산 | 주기 종료 시점에 누적 결과 평균 |
| LSTM 예측 주기 | 평균 계산과 동일 주기로 예측 실행 |
| 음성 안내 간격 | 주기 종료마다 안내 (최소 간격 준수) |
| 시계열 데이터 간격 | 주기 단위로 1개 데이터 포인트 추가 |
| UI 업데이트 | 주기 종료 시 평균/예측/비교 결과 갱신 |

```
주기 = 5초:   ████▎ (빠른 업데이트, 더 민감한 반응)
주기 = 10초:  █████████▎ (기본, 균형 잡힌 업데이트)  
주기 = 20초:  ███████████████████▎ (느린 업데이트, 더 안정적)
```

**주기 변경 시 동작**:
1. 현재 누적 데이터를 초기화한다.
2. 오디오 버퍼 크기를 새 주기에 맞게 재설정한다.
3. 타이머를 새 주기로 재시작한다.
4. LSTM 입력 데이터의 시간 간격이 변경되므로 시계열 버퍼를 리셋한다.

---

## 9. LSTM Prediction Logic

### 9.1 LSTM 모델 구조

```
입력: [sequence_length, features]
      sequence_length = 10 (최근 10개 주기)
      features = 9 (감정 카테고리 수)

┌──────────────────────────────────────┐
│ Input Layer: (10, 9)                 │
├──────────────────────────────────────┤
│ LSTM Layer 1: 64 units, return_seq   │
├──────────────────────────────────────┤
│ Dropout: 0.2                         │
├──────────────────────────────────────┤
│ LSTM Layer 2: 32 units               │
├──────────────────────────────────────┤
│ Dropout: 0.2                         │
├──────────────────────────────────────┤
│ Dense Layer: 16 units, ReLU          │
├──────────────────────────────────────┤
│ Output Layer: 9 units, Softmax       │
└──────────────────────────────────────┘

출력: [9] → 다음 주기 감정 확률 분포
```

### 9.2 예측 흐름

```
[주기 종료: 평균 감정 계산 완료]
       │
       ▼
[시계열 버퍼에 평균 점수 추가]
       │
       ├── 데이터 < 5개 → "데이터 수집 중" 표시
       │
       ▼ (데이터 ≥ 5개)
[최근 10개 주기 데이터 추출]
       │
       ▼
[LSTM 모델 추론]
       │
       ▼
[예측 EmotionScores 생성]
       │
       ├──▶ [UI 표시: "LSTM 예측 감정"]
       └──▶ [emotion_comparator로 전달]
```

### 9.3 시계열 버퍼 관리

```python
class TimeSeriesBuffer:
    """LSTM 입력을 위한 시계열 데이터 관리"""
    
    SEQUENCE_LENGTH = 10  # 최근 10개 주기
    MIN_DATA_POINTS = 5   # 예측 시작 최소 데이터 수
    
    def __init__(self):
        self.buffer: List[Dict[str, float]] = []
    
    def add(self, emotion_scores: Dict[str, float]):
        """새 주기의 감정 점수를 추가"""
        self.buffer.append(emotion_scores)
        # 최대 크기 초과 시 가장 오래된 데이터 제거
        if len(self.buffer) > self.SEQUENCE_LENGTH * 2:
            self.buffer = self.buffer[-self.SEQUENCE_LENGTH:]
    
    def is_ready(self) -> bool:
        """예측 가능 상태인지 확인"""
        return len(self.buffer) >= self.MIN_DATA_POINTS
    
    def get_input(self) -> np.ndarray:
        """LSTM 입력 형태로 변환"""
        recent = self.buffer[-self.SEQUENCE_LENGTH:]
        # 패딩 (데이터가 부족한 경우)
        while len(recent) < self.SEQUENCE_LENGTH:
            recent.insert(0, recent[0])
        return np.array([[s[e] for e in EMOTIONS] for s in recent])
```

### 9.4 평균값 vs 예측값 비교 로직

```python
# 감정의 긍정/부정 매핑
EMOTION_VALENCE = {
    "happy": 1.0,   "calm": 0.7,     "neutral": 0.0,
    "surprised": 0.2, "sad": -0.5,   "angry": -0.7,
    "fearful": -0.8, "disgusted": -0.6, "stressed": -0.9
}

def compare_emotions(average: Dict[str, float], 
                     predicted: Dict[str, float]) -> Tuple[str, float]:
    """
    평균 감정과 예측 감정을 비교하여 변화 방향을 판단합니다.
    
    Returns:
        (변화_방향_레이블, 변화_크기)
    """
    # 가중 평균 valence 계산
    avg_valence = sum(score * EMOTION_VALENCE[e] 
                      for e, score in average.items())
    pred_valence = sum(score * EMOTION_VALENCE[e] 
                       for e, score in predicted.items())
    
    diff = pred_valence - avg_valence
    magnitude = abs(diff)
    
    # 스트레스 특수 판단
    stress_increase = (predicted.get("stressed", 0) - average.get("stressed", 0) +
                       predicted.get("fearful", 0) - average.get("fearful", 0))
    
    # 변동성 판단
    variance = np.std([predicted[e] - average[e] for e in EMOTIONS])
    
    if variance > 0.15:
        return "감정 변동성 증가", magnitude
    elif stress_increase > 0.1:
        return "스트레스 증가 가능성", magnitude
    elif magnitude < 0.05:
        return "안정적", magnitude
    elif diff > 0:
        return "긍정 방향 변화", magnitude
    else:
        return "부정 방향 변화", magnitude
```



---

## 10. UI Architecture

### 10.1 UI 레이아웃 구성

```
┌─────────────────────────────────────────────────────────────┐
│  Multimodal Emotion State Monitor                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── 설정 패널 ───────────────────────────────────────┐   │
│  │  감정 인식 주기: [====●=====] 10초  (5~20초)        │   │
│  │  음성 출력 볼륨: [=======●==] 70%   (0~100%)       │   │
│  │  분석 종류:      [▼ 표정+음성 통합]                  │   │
│  │  음성 안내:      [● ON] / [○ OFF]                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─── 제어 ────────────────────────────────────────────┐   │
│  │  [ ▶ 시작 ]   [ ■ 정지 ]                           │   │
│  │  📷 카메라: 사용 중  🎤 마이크: 사용 중              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─── 결과 표시 ───────────────────────────────────────┐   │
│  │                                                      │   │
│  │  현재 감정:    😊 happy (92%)                        │   │
│  │  최근 평균:    😌 calm (78%)                         │   │
│  │  LSTM 예측:   🙂 neutral (65%)                      │   │
│  │  변화 방향:    → 안정적 (변화폭: 0.03)               │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─── 로그 ────────────────────────────────────────────┐   │
│  │  [14:30:10] 감정 분석: happy (conf: 0.92)           │   │
│  │  [14:30:10] 평균 감정: calm (주기: 10초)             │   │
│  │  [14:30:10] LSTM 예측: neutral (conf: 0.65)         │   │
│  │  [14:30:10] 비교 결과: 안정적                        │   │
│  │  [14:30:10] 음성 안내: "현재 상태는 안정적입니다"      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ⚠️ 감정 분석 결과는 참고용이며, 의학적·심리학적 진단이      │
│     아닙니다.                                               │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 UI ↔ Backend 통신 구조

```
┌──────────┐     설정값/이벤트      ┌──────────────┐
│          │ ──────────────────────▶ │              │
│    UI    │                         │  Controller  │
│  (Main   │ ◀────────────────────── │  (Backend)   │
│  Thread) │   결과/상태 업데이트      │              │
└──────────┘                         └──────────────┘
```

**통신 방식**:
- **Streamlit**: Session State + st.rerun() 기반 폴링
- **PyQt**: Signal/Slot 메커니즘 + QThread

### 10.3 UI 상태 모델

```python
@dataclass
class UIState:
    """UI 상태를 관리하는 데이터 클래스"""
    # 설정
    cycle_seconds: int = 10            # 분석 주기 (5~20)
    volume: int = 70                   # 음성 볼륨 (0~100)
    analysis_mode: str = "integrated"  # face_only / voice_only / integrated
    voice_feedback_enabled: bool = True
    
    # 제어 상태
    is_running: bool = False
    camera_active: bool = False
    microphone_active: bool = False
    
    # 결과
    current_emotion: Optional[EmotionScores] = None
    average_emotion: Optional[EmotionScores] = None
    predicted_emotion: Optional[EmotionScores] = None
    comparison_result: Optional[str] = None
    
    # 로그
    log_messages: List[str] = field(default_factory=list)
```

---

## 11. Privacy and Security Design

### 11.1 개인정보 보호 원칙

| 원칙 | 구현 방식 |
|------|-----------|
| **얼굴 이미지 저장 금지** | 프레임은 메모리에서만 처리, 분석 후 즉시 참조 해제 (GC 대상) |
| **원본 음성 저장 금지** | 오디오 버퍼는 메모리에서만 유지, 주기 종료 후 폐기 |
| **외부 서버 전송 금지** | 네트워크 소켓을 열지 않음, HTTP/HTTPS 요청 없음 |
| **로컬 처리 우선** | 모든 모델 추론은 로컬 CPU/GPU에서 수행 |

### 11.2 데이터 생명주기

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  수집 단계   │     │  처리 단계   │     │  폐기 단계   │
│             │     │             │     │             │
│ 웹캠 프레임  │────▶│ 감정 분류   │────▶│ 프레임 삭제  │
│ 오디오 버퍼  │────▶│ 특징 추출   │────▶│ 버퍼 초기화  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  결과만 보존  │
                    │ (점수, 레이블)│
                    │  → 로그 기록  │
                    └─────────────┘
```

### 11.3 보안 설계 체크리스트

- [x] 네트워크 인터페이스 바인딩 없음
- [x] 파일 시스템 쓰기: 로그 파일만 허용 (설정으로 비활성화 가능)
- [x] 사용자 명시적 동의 후에만 캡처 시작 (시작 버튼)
- [x] 카메라/마이크 사용 상태 UI에 상시 표시
- [x] 프로그램 종료 시 모든 미디어 리소스 즉시 해제
- [x] 의료/심리 진단 면책 안내문 상시 표시

### 11.4 저장 허용 데이터 범위

| 데이터 유형 | 저장 여부 | 저장 형태 |
|------------|-----------|-----------|
| 웹캠 영상 프레임 | ❌ 금지 | - |
| 얼굴 이미지 크롭 | ❌ 금지 | - |
| 원본 오디오 데이터 | ❌ 금지 | - |
| 감정 점수 결과 | ✅ 허용 (선택) | 로컬 로그 파일 (JSON/CSV) |
| 평균/예측 결과 | ✅ 허용 (선택) | 로컬 로그 파일 |
| 설정값 | ✅ 허용 | 로컬 설정 파일 |

---

## 12. Local Runtime Environment

### 12.1 실행 환경 요구사항

| 항목 | 최소 사양 | 권장 사양 |
|------|-----------|-----------|
| OS | Windows 10, macOS 12, Ubuntu 20.04 | Windows 11, macOS 14, Ubuntu 22.04 |
| Python | 3.9 | 3.10~3.11 |
| CPU | Intel i5 / AMD Ryzen 5 | Intel i7 / AMD Ryzen 7 |
| RAM | 4GB | 8GB 이상 |
| 디스크 | 3GB (모델 포함) | 5GB |
| 카메라 | 내장 웹캠 또는 USB 웹캠 | HD 해상도 이상 |
| 마이크 | 내장 마이크 또는 외부 마이크 | 노이즈 캔슬링 마이크 |
| GPU | 불필요 (CPU 전용) | 있으면 가속 활용 |

### 12.2 프로세스 구조

```
[main.py]
    │
    ├── Main Thread: UI 렌더링 + 이벤트 처리
    │
    ├── Worker Thread 1: 웹캠 캡처 + 얼굴 감지 + 표정 분류
    │
    ├── Worker Thread 2: 마이크 캡처 + 음성 분석
    │
    ├── Worker Thread 3: LSTM 예측 + 비교
    │
    └── Worker Thread 4: 음성 안내 출력 (TTS)
```

### 12.3 스레드 간 통신

```python
import queue
import threading

# 스레드 간 데이터 전달을 위한 큐
face_result_queue = queue.Queue(maxsize=100)
voice_result_queue = queue.Queue(maxsize=100)
ui_update_queue = queue.Queue(maxsize=50)
tts_queue = queue.Queue(maxsize=10)
```

### 12.4 리소스 관리

```python
class ResourceManager:
    """시스템 리소스 초기화 및 해제 관리"""
    
    def __init__(self):
        self.camera = None
        self.microphone = None
        self.tts_engine = None
    
    def initialize(self, config: UIState):
        """설정에 따라 필요한 리소스만 초기화"""
        if config.analysis_mode in ("face_only", "integrated"):
            self.camera = self._init_camera()
        if config.analysis_mode in ("voice_only", "integrated"):
            self.microphone = self._init_microphone()
        if config.voice_feedback_enabled:
            self.tts_engine = self._init_tts()
    
    def cleanup(self):
        """모든 리소스를 안전하게 해제"""
        if self.camera: self.camera.release()
        if self.microphone: self.microphone.close()
        if self.tts_engine: self.tts_engine.stop()
```

---

## 13. Future AWS Extension Plan

### 13.1 확장 개요

초기 MVP는 로컬 전용이지만, 향후 AWS 리소스 연동을 통해 다음 기능을 확장할 수 있습니다:

```
┌─────────────────┐          ┌──────────────────────────────────┐
│  Local PC       │          │  AWS Cloud                        │
│                 │          │                                  │
│  ┌───────────┐  │  HTTPS   │  ┌────────────────────────────┐  │
│  │ Emotion   │──┼─────────▶│  │ Amazon SageMaker           │  │
│  │ Monitor   │  │          │  │ - 고성능 LSTM 모델 학습     │  │
│  │ (로컬)    │◀─┼──────────│  │ - 모델 배포 (Endpoint)     │  │
│  └───────────┘  │          │  └────────────────────────────┘  │
│                 │          │                                  │
│                 │          │  ┌────────────────────────────┐  │
│                 │─────────▶│  │ Amazon DynamoDB / S3       │  │
│                 │          │  │ - 감정 통계 저장            │  │
│                 │          │  │ - 모델 버전 관리            │  │
│                 │          │  └────────────────────────────┘  │
│                 │          │                                  │
│                 │          │  ┌────────────────────────────┐  │
│                 │─────────▶│  │ Amazon Polly               │  │
│                 │          │  │ - 고품질 음성 합성           │  │
│                 │          │  └────────────────────────────┘  │
│                 │          │                                  │
│                 │          │  ┌────────────────────────────┐  │
│                 │─────────▶│  │ AWS IoT Greengrass         │  │
│                 │          │  │ - 엣지 추론 최적화          │  │
│                 │          │  └────────────────────────────┘  │
└─────────────────┘          └──────────────────────────────────┘
```

### 13.2 AWS 확장 로드맵

| Phase | 기능 | AWS 서비스 | 설명 |
|-------|------|-----------|------|
| Phase A | 모델 학습 | SageMaker | 실제 사용자 데이터 기반 LSTM 재학습 |
| Phase B | 모델 배포 | SageMaker Endpoint | 클라우드 추론 또는 모델 다운로드 |
| Phase C | 데이터 저장 | DynamoDB / S3 | 장기 감정 추세 데이터 저장/분석 |
| Phase D | 음성 품질 향상 | Amazon Polly | 자연스러운 한국어 음성 안내 |
| Phase E | 엣지 최적화 | IoT Greengrass | 로컬 디바이스 추론 최적화 |
| Phase F | 대시보드 | QuickSight / CloudWatch | 감정 추세 시각화 대시보드 |

### 13.3 확장 시 설계 고려사항

- **모듈 인터페이스**: 각 모듈은 추상 인터페이스를 통해 호출 → 로컬/클라우드 구현 교체 가능
- **네트워크 연동 시 프라이버시**: 영상/음성 원본은 전송하지 않고, 추출된 특징 벡터 또는 분석 결과만 전송
- **오프라인 폴백**: AWS 연결 실패 시 자동으로 로컬 모델로 폴백
- **설정 기반 전환**: `config.py`에서 `USE_AWS=True/False` 플래그로 전환

```python
# config.py 확장 예시
USE_AWS = False  # MVP: False → 향후: True

AWS_CONFIG = {
    "region": "ap-northeast-2",
    "sagemaker_endpoint": "emotion-lstm-endpoint",
    "polly_voice_id": "Seoyeon",
    "s3_bucket": "emotion-data-bucket",
}
```

---

## 14. Technical Risks and Mitigation

### 14.1 리스크 매트릭스

| 리스크 | 영향도 | 발생 확률 | 완화 전략 |
|--------|--------|-----------|-----------|
| 표정 분석 모델 정확도 부족 | 높음 | 중간 | 다중 모델 앙상블, 신뢰도 임계값 적용 |
| 음성 감정 분석 정확도 부족 | 높음 | 높음 | 공개 데이터셋 활용 학습, 특징 조합 최적화 |
| CPU 환경에서 실시간 처리 불가 | 높음 | 중간 | 프레임 스킵, 모델 경량화, 분석 주기 조절 |
| LSTM 예측 정확도 부족 (MVP) | 중간 | 높음 | 초기엔 트렌드 방향 제시에 집중, 점진적 개선 |
| 카메라/마이크 호환성 문제 | 중간 | 중간 | 다중 백엔드 지원, 장치 ID 설정 가능 |
| TTS 음성 안내와 마이크 간섭 | 중간 | 높음 | 음성 안내 중 마이크 일시 정지, 에코 제거 |
| 메모리 누수 (장시간 실행) | 높음 | 중간 | 주기적 버퍼 정리, 메모리 모니터링, GC 호출 |
| DeepFace/TensorFlow 버전 충돌 | 중간 | 중간 | 가상환경 격리, 의존성 버전 고정 |

### 14.2 성능 최적화 전략

| 전략 | 설명 | 적용 대상 |
|------|------|-----------|
| 프레임 스킵 | 영상은 매 프레임 표시하되, 분석은 N프레임마다 | 표정 분석 |
| 모델 경량화 | MobileNet 기반 경량 모델 사용 | 표정 분류 |
| 비동기 분석 | 분석을 별도 스레드에서 수행 | 전체 파이프라인 |
| 버퍼 크기 제한 | 시계열/오디오 버퍼 최대 크기 설정 | LSTM, 음성 |
| Lazy Loading | 모델을 최초 사용 시에만 로드 | 전체 모델 |
| 결과 캐싱 | 동일 프레임 재분석 방지 | 표정 분석 |

### 14.3 에러 복구 전략

```python
class ErrorRecoveryPolicy:
    """에러 발생 시 복구 정책"""
    
    POLICIES = {
        "camera_fail": {
            "action": "disable_face_analysis",
            "message": "카메라를 사용할 수 없습니다. 음성 분석만 진행합니다.",
            "retry": True,
            "max_retries": 3,
        },
        "microphone_fail": {
            "action": "disable_voice_analysis",
            "message": "마이크를 사용할 수 없습니다. 표정 분석만 진행합니다.",
            "retry": True,
            "max_retries": 3,
        },
        "model_load_fail": {
            "action": "disable_feature",
            "message": "모델을 로드할 수 없습니다. 해당 기능을 비활성화합니다.",
            "retry": False,
        },
        "lstm_inference_fail": {
            "action": "use_last_prediction",
            "message": "LSTM 추론 실패. 이전 예측 결과를 유지합니다.",
            "retry": True,
            "max_retries": 2,
        },
        "tts_fail": {
            "action": "text_only_feedback",
            "message": "음성 출력 불가. 텍스트로만 안내합니다.",
            "retry": False,
        },
    }
```

### 14.4 테스트 전략

| 테스트 유형 | 대상 | 도구 |
|------------|------|------|
| 단위 테스트 | 각 모듈의 핵심 로직 | pytest |
| 통합 테스트 | 모듈 간 데이터 흐름 | pytest + mock |
| 성능 테스트 | CPU 사용률, 메모리, FPS | cProfile, memory_profiler |
| UI 테스트 | 버튼/슬라이더 동작 | Selenium (Streamlit) / pytest-qt |
| 엣지 케이스 | 카메라 없음, 마이크 없음, 모델 없음 | 수동 테스트 |
