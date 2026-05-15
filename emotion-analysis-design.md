# Emotion Analysis Design - Multimodal Emotion State Monitor

## 1. 개요

본 문서는 얼굴 표정 기반 감정 분석 모듈의 상세 설계를 정의합니다.
웹캠에서 캡처한 프레임으로부터 얼굴을 감지하고, 9가지 감정 중 하나로 분류합니다.

---

## 2. 모듈 구성

```
modules/
├── webcam.py              # 웹캠 캡처 + 얼굴 감지
└── face_expression.py     # 표정 감정 분류
```

---

## 3. 웹캠 모듈 (webcam.py)

### 3.1 클래스 설계

```python
class WebcamCapture:
    """웹캠 프레임 캡처 및 얼굴 감지"""
    
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.cap = None
        self.face_detector = None  # MediaPipe or Haar Cascade
    
    def open(self) -> bool:
        """카메라를 열고 초기화"""
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """한 프레임 캡처"""
    
    def detect_faces(self, frame: np.ndarray) -> List[FaceRegion]:
        """프레임에서 얼굴 영역 감지"""
    
    def get_largest_face(self, faces: List[FaceRegion]) -> Optional[FaceRegion]:
        """여러 얼굴 중 가장 큰(가까운) 얼굴 반환"""
    
    def release(self):
        """카메라 리소스 해제"""
    
    @property
    def is_opened(self) -> bool:
        """카메라 열림 상태 확인"""
```

### 3.2 얼굴 감지 방식

| 방식 | 장점 | 단점 | 선택 기준 |
|------|------|------|-----------|
| MediaPipe Face Detection | 높은 정확도, 랜드마크 제공 | 약간 무거움 | 기본 선택 |
| OpenCV Haar Cascade | 가벼움, 추가 설치 불필요 | 정확도 낮음 | 폴백 |
| OpenCV DNN (Caffe/TF) | 중간 정확도 | 모델 파일 필요 | 대안 |

### 3.3 프레임 캡처 설정

```python
WEBCAM_CONFIG = {
    "device_id": 0,
    "frame_width": 640,
    "frame_height": 480,
    "fps_target": 30,
    "analysis_skip_frames": 3,  # 3프레임마다 1회 분석
}
```

---

## 4. 표정 분류 모듈 (face_expression.py)

### 4.1 클래스 설계

```python
class FaceExpressionClassifier:
    """얼굴 이미지를 입력받아 감정을 분류"""
    
    EMOTIONS = ["neutral", "happy", "sad", "angry", 
                "surprised", "fearful", "disgusted", "stressed", "calm"]
    
    def __init__(self, backend: str = "deepface"):
        self.backend = backend
        self.model = None
    
    def initialize(self) -> bool:
        """모델 로드 (Lazy initialization)"""
    
    def classify(self, face_image: np.ndarray) -> Optional[EmotionScores]:
        """
        얼굴 이미지로 감정 분류
        
        Args:
            face_image: 크롭된 얼굴 이미지 (BGR, numpy)
        
        Returns:
            EmotionScores 또는 분류 실패 시 None
        """
    
    def _map_to_internal(self, raw_scores: Dict) -> Dict[str, float]:
        """외부 모델 출력을 내부 감정 체계로 매핑"""
    
    def _infer_stressed_calm(self, base_scores: Dict) -> Dict[str, float]:
        """stressed/calm 추정 (표정만으로 직접 분류 어려운 감정)"""
```

### 4.2 감정 매핑 로직

DeepFace는 7개 감정만 출력하므로, `stressed`와 `calm`은 추정합니다:

```python
def _infer_stressed_calm(self, base_scores: Dict[str, float]) -> Dict[str, float]:
    """
    stressed: angry + fearful + sad의 조합으로 추정
    calm: neutral의 높은 점수 + 부정 감정 낮음으로 추정
    """
    scores = base_scores.copy()
    
    # stressed 추정: 부정 감정들의 가중 조합
    stressed_score = (
        scores.get("angry", 0) * 0.3 +
        scores.get("fearful", 0) * 0.4 +
        scores.get("sad", 0) * 0.2 +
        scores.get("disgusted", 0) * 0.1
    ) * 0.5  # 보수적 추정
    
    # calm 추정: neutral이 높고 부정 감정이 낮을 때
    negative_sum = sum(scores.get(e, 0) for e in 
                       ["angry", "fearful", "sad", "disgusted"])
    calm_score = max(0, scores.get("neutral", 0) * 0.6 - negative_sum * 0.3)
    
    scores["stressed"] = stressed_score
    scores["calm"] = calm_score
    
    # 정규화
    total = sum(scores.values())
    if total > 0:
        scores = {k: v / total for k, v in scores.items()}
    
    return scores
```

### 4.3 전처리 파이프라인

```python
def preprocess_face(self, frame: np.ndarray, region: FaceRegion) -> np.ndarray:
    """
    분석을 위한 얼굴 이미지 전처리
    
    1. 얼굴 영역 크롭 (여유 공간 20% 포함)
    2. 이미지 크기 정규화 (224x224 또는 48x48)
    3. 밝기/대비 정규화
    """
    padding_ratio = 0.2
    h, w = frame.shape[:2]
    
    # 패딩 적용
    pad_x = int(region.w * padding_ratio)
    pad_y = int(region.h * padding_ratio)
    
    x1 = max(0, region.x - pad_x)
    y1 = max(0, region.y - pad_y)
    x2 = min(w, region.x + region.w + pad_x)
    y2 = min(h, region.y + region.h + pad_y)
    
    face_img = frame[y1:y2, x1:x2]
    
    # 크기 정규화
    face_img = cv2.resize(face_img, (224, 224))
    
    return face_img
```

---

## 5. 분석 주기와 프레임 스킵 전략

### 5.1 연속 분석 vs 주기 분석

```
시간 ─────────────────────────────────────────▶

프레임:  │F1│F2│F3│F4│F5│F6│F7│F8│F9│...
표시:    │✓ │✓ │✓ │✓ │✓ │✓ │✓ │✓ │✓ │...  (매 프레임 표시)
분석:    │✓ │  │  │✓ │  │  │✓ │  │  │...  (3프레임마다 분석)
                                    
주기 끝: ─────────────────────────────│
         ← 10초 (설정 주기) →         │
                                      ▼
                              [평균 계산 트리거]
```

### 5.2 분석 결과 축적

- 주기 동안 분석된 모든 `EmotionScores`를 리스트에 축적
- 주기 종료 시 `emotion_averager`로 전달
- 축적 후 리스트 초기화

---

## 6. 성능 고려사항

| 항목 | 목표 | 전략 |
|------|------|------|
| 프레임 표시 FPS | ≥ 10 | UI 표시와 분석 분리 (별도 스레드) |
| 분석 레이턴시 | < 500ms | 프레임 스킵, 경량 모델 사용 |
| 메모리 | < 800MB | 모델 1개만 로드, 프레임 즉시 해제 |
| CPU 사용률 | < 60% | 분석 주기 내에서만 추론 수행 |

---

## 7. 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| 카메라 열기 실패 | UI에 경고, 표정 분석 비활성화 |
| 프레임 읽기 실패 (연속 3회) | 카메라 재초기화 시도 |
| 얼굴 미감지 | 해당 프레임 건너뜀, UI에 상태 표시 |
| 모델 추론 실패 | None 반환, 다음 프레임에서 재시도 |
| 이미지 품질 불량 (너무 어둡거나 흐림) | 감지 스킵, 로그 기록 |
