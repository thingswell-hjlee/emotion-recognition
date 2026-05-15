# LSTM Prediction Design - Multimodal Emotion State Monitor

## 1. 개요

본 문서는 LSTM 기반 감정 예측 모듈의 상세 설계를 정의합니다.
최근 감정 시계열 데이터를 입력으로 받아 다음 주기의 감정 상태를 예측하고,
현재 평균값과 비교하여 감정 변화 방향을 판단합니다.

---

## 2. 모듈 구성

```
modules/
├── lstm_predictor.py        # LSTM 모델 추론
└── emotion_comparator.py    # 평균 vs 예측 비교

models/
├── lstm_model.h5            # 학습된 LSTM 모델
└── model_utils.py           # 모델 유틸리티
```

---

## 3. LSTM 모델 설계

### 3.1 모델 아키텍처

```
입력: (batch_size, sequence_length, features)
      sequence_length = 10 (최근 10개 주기)
      features = 9 (감정 카테고리 수)

Layer 구성:
┌──────────────────────────────────────────┐
│ Input: (None, 10, 9)                     │
├──────────────────────────────────────────┤
│ LSTM(64, return_sequences=True)          │
│ - activation: tanh                       │
│ - recurrent_activation: sigmoid          │
├──────────────────────────────────────────┤
│ Dropout(0.2)                             │
├──────────────────────────────────────────┤
│ LSTM(32, return_sequences=False)         │
├──────────────────────────────────────────┤
│ Dropout(0.2)                             │
├──────────────────────────────────────────┤
│ Dense(16, activation='relu')             │
├──────────────────────────────────────────┤
│ Dense(9, activation='softmax')           │
└──────────────────────────────────────────┘

출력: (batch_size, 9) → 다음 주기 감정 확률 분포
총 파라미터: ~25,000 (경량 모델)
```

### 3.2 TensorFlow/Keras 구현

```python
import tensorflow as tf
from tensorflow.keras import layers, Model

def build_lstm_model(sequence_length=10, n_features=9) -> Model:
    """LSTM 감정 예측 모델 생성"""
    
    inputs = layers.Input(shape=(sequence_length, n_features))
    
    x = layers.LSTM(64, return_sequences=True)(inputs)
    x = layers.Dropout(0.2)(x)
    
    x = layers.LSTM(32, return_sequences=False)(x)
    x = layers.Dropout(0.2)(x)
    
    x = layers.Dense(16, activation='relu')(x)
    outputs = layers.Dense(n_features, activation='softmax')(x)
    
    model = Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model
```

---

## 4. 시계열 데이터 관리

### 4.1 TimeSeriesBuffer 클래스

```python
class TimeSeriesBuffer:
    """LSTM 입력을 위한 시계열 데이터 관리"""
    
    SEQUENCE_LENGTH = 10   # 입력 시퀀스 길이
    MIN_DATA_POINTS = 5    # 예측 시작 최소 데이터
    MAX_BUFFER_SIZE = 100  # 최대 보존 데이터 수
    
    def __init__(self):
        self.buffer: List[Dict[str, float]] = []
        self.timestamps: List[datetime] = []
    
    def add(self, emotion_scores: Dict[str, float], timestamp: datetime):
        """새 주기의 감정 평균 점수를 추가"""
        self.buffer.append(emotion_scores)
        self.timestamps.append(timestamp)
        
        # 최대 크기 제한
        if len(self.buffer) > self.MAX_BUFFER_SIZE:
            self.buffer = self.buffer[-self.MAX_BUFFER_SIZE:]
            self.timestamps = self.timestamps[-self.MAX_BUFFER_SIZE:]
    
    def is_ready(self) -> bool:
        """예측 가능 여부"""
        return len(self.buffer) >= self.MIN_DATA_POINTS
    
    def get_input_sequence(self) -> np.ndarray:
        """
        LSTM 입력 형태로 변환
        
        Returns:
            shape: (1, sequence_length, 9)
        """
        recent = self.buffer[-self.SEQUENCE_LENGTH:]
        
        # 패딩: 데이터가 부족한 경우 첫 데이터로 채움
        while len(recent) < self.SEQUENCE_LENGTH:
            recent.insert(0, recent[0])
        
        # numpy 배열로 변환
        EMOTIONS = ["neutral", "happy", "sad", "angry", "surprised",
                    "fearful", "disgusted", "stressed", "calm"]
        
        sequence = np.array([
            [scores.get(e, 0.0) for e in EMOTIONS]
            for scores in recent
        ], dtype=np.float32)
        
        return sequence.reshape(1, self.SEQUENCE_LENGTH, len(EMOTIONS))
    
    def reset(self):
        """주기 변경 시 버퍼 초기화"""
        self.buffer.clear()
        self.timestamps.clear()
```

### 4.2 데이터 흐름

```
[주기 N 종료]
     │
     ▼
[emotion_averager → 평균 점수]
     │
     ▼
[TimeSeriesBuffer.add(평균 점수)]
     │
     ├── buffer.length < 5 → "데이터 수집 중"
     │
     ▼ (buffer.length ≥ 5)
[TimeSeriesBuffer.get_input_sequence()]
     │
     ▼
[LSTM 모델 추론]
     │
     ▼
[예측 결과: Dict[str, float]]
     │
     ├──▶ UI 표시
     └──▶ emotion_comparator
```

---

## 5. 예측 모듈 (lstm_predictor.py)

### 5.1 클래스 설계

```python
class LSTMPredictor:
    """LSTM 기반 감정 예측"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path
        self.time_series = TimeSeriesBuffer()
        self._initialized = False
    
    def initialize(self) -> bool:
        """모델 로드"""
        if self.model_path and os.path.exists(self.model_path):
            self.model = tf.keras.models.load_model(self.model_path)
        else:
            # 모델 파일 없으면 새로 생성 (초기 MVP)
            self.model = build_lstm_model()
        self._initialized = True
        return True
    
    def add_data_point(self, avg_scores: Dict[str, float], 
                       timestamp: datetime):
        """새 평균 데이터 추가"""
        self.time_series.add(avg_scores, timestamp)
    
    def predict(self) -> Optional[EmotionScores]:
        """
        다음 주기 감정 예측
        
        Returns:
            예측 EmotionScores 또는 데이터 부족 시 None
        """
        if not self.time_series.is_ready():
            return None
        
        if not self._initialized:
            self.initialize()
        
        # 입력 준비
        input_seq = self.time_series.get_input_sequence()
        
        # 추론
        prediction = self.model.predict(input_seq, verbose=0)[0]
        
        # EmotionScores로 변환
        EMOTIONS = ["neutral", "happy", "sad", "angry", "surprised",
                    "fearful", "disgusted", "stressed", "calm"]
        
        scores = dict(zip(EMOTIONS, prediction.tolist()))
        dominant = max(scores, key=scores.get)
        
        return EmotionScores(
            scores=scores,
            dominant=dominant,
            confidence=scores[dominant]
        )
    
    def reset(self):
        """주기 변경 시 시계열 초기화"""
        self.time_series.reset()
    
    @property
    def data_count(self) -> int:
        """현재 수집된 데이터 포인트 수"""
        return len(self.time_series.buffer)
    
    @property
    def is_ready(self) -> bool:
        """예측 가능 상태"""
        return self.time_series.is_ready()
```

---

## 6. 비교 모듈 (emotion_comparator.py)

### 6.1 클래스 설계

```python
class EmotionComparator:
    """평균 감정과 예측 감정을 비교하여 변화 방향 판단"""
    
    # 감정의 긍정/부정 가치(valence) 매핑
    EMOTION_VALENCE = {
        "happy": 1.0,
        "calm": 0.7,
        "surprised": 0.2,
        "neutral": 0.0,
        "sad": -0.5,
        "disgusted": -0.6,
        "angry": -0.7,
        "fearful": -0.8,
        "stressed": -0.9,
    }
    
    # 비교 결과 레이블
    LABELS = {
        "STABLE": "안정적",
        "POSITIVE": "긍정 방향 변화",
        "NEGATIVE": "부정 방향 변화",
        "STRESS_UP": "스트레스 증가 가능성",
        "VOLATILE": "감정 변동성 증가",
    }
    
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
        
        # 판단 로직
        label = self._determine_label(average, predicted, diff, magnitude)
        
        return label, magnitude
    
    def _calc_valence(self, scores: Dict[str, float]) -> float:
        """감정 점수의 가중 valence 계산"""
        return sum(
            score * self.EMOTION_VALENCE.get(emotion, 0)
            for emotion, score in scores.items()
        )
    
    def _determine_label(self, avg, pred, diff, magnitude) -> str:
        """변화 방향 레이블 결정"""
        EMOTIONS = list(self.EMOTION_VALENCE.keys())
        
        # 변동성 체크
        changes = [pred.get(e, 0) - avg.get(e, 0) for e in EMOTIONS]
        variance = np.std(changes)
        
        if variance > 0.15:
            return self.LABELS["VOLATILE"]
        
        # 스트레스 증가 체크
        stress_change = (
            pred.get("stressed", 0) - avg.get("stressed", 0) +
            pred.get("fearful", 0) - avg.get("fearful", 0)
        )
        if stress_change > 0.1:
            return self.LABELS["STRESS_UP"]
        
        # 안정성 체크
        if magnitude < 0.05:
            return self.LABELS["STABLE"]
        
        # 방향 판단
        if diff > 0:
            return self.LABELS["POSITIVE"]
        else:
            return self.LABELS["NEGATIVE"]
```

---

## 7. 초기 MVP 학습 전략

### 7.1 더미 데이터 생성

초기 MVP에서는 LSTM 모델을 간단한 합성 데이터로 학습합니다:

```python
def generate_dummy_training_data(n_samples=1000, seq_length=10, n_emotions=9):
    """
    학습용 더미 시계열 데이터 생성
    
    전략: 감정 전이 확률 기반 시퀀스 생성
    - 같은 감정이 연속될 확률: 60%
    - 유사 감정으로 전이: 25%
    - 무작위 전이: 15%
    """
    # 감정 전이 행렬 (simplified)
    transition_matrix = np.array([
        # neu  hap  sad  ang  sur  fea  dis  str  cal
        [0.5, 0.1, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.1],  # neutral
        [0.1, 0.5, 0.05, 0.05, 0.1, 0.02, 0.02, 0.06, 0.1],   # happy
        [0.1, 0.05, 0.5, 0.1, 0.02, 0.1, 0.05, 0.08, 0.0],    # sad
        [0.1, 0.02, 0.1, 0.5, 0.05, 0.1, 0.05, 0.08, 0.0],    # angry
        [0.15, 0.1, 0.05, 0.05, 0.4, 0.1, 0.05, 0.05, 0.05],  # surprised
        [0.1, 0.02, 0.1, 0.1, 0.05, 0.4, 0.05, 0.15, 0.03],   # fearful
        [0.1, 0.02, 0.1, 0.15, 0.05, 0.05, 0.4, 0.1, 0.03],   # disgusted
        [0.05, 0.02, 0.1, 0.15, 0.03, 0.15, 0.1, 0.35, 0.05], # stressed
        [0.15, 0.2, 0.02, 0.02, 0.05, 0.02, 0.02, 0.02, 0.5], # calm
    ])
    
    X, y = [], []
    
    for _ in range(n_samples):
        # 시퀀스 생성
        sequence = []
        state = np.random.randint(0, n_emotions)
        
        for _ in range(seq_length + 1):
            # one-hot에 노이즈 추가 (실제 감정 분포 모방)
            scores = np.random.dirichlet(np.ones(n_emotions) * 0.5)
            scores[state] += 0.5
            scores /= scores.sum()
            sequence.append(scores)
            
            # 전이
            state = np.random.choice(n_emotions, p=transition_matrix[state])
        
        X.append(sequence[:-1])  # 입력: 처음 10개
        y.append(sequence[-1])   # 출력: 마지막 1개
    
    return np.array(X), np.array(y)
```

### 7.2 학습 스크립트

```python
def train_initial_model():
    """초기 LSTM 모델 학습"""
    
    # 더미 데이터 생성
    X_train, y_train = generate_dummy_training_data(n_samples=5000)
    X_val, y_val = generate_dummy_training_data(n_samples=1000)
    
    # 모델 생성
    model = build_lstm_model(sequence_length=10, n_features=9)
    
    # 학습
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=32,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(patience=5),
            tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3),
        ]
    )
    
    # 저장
    model.save("models/lstm_model.h5")
    print("[INFO] LSTM 모델 학습 완료")
```

---

## 8. 향후 확장 계획

| 단계 | 내용 | 데이터 소스 |
|------|------|------------|
| MVP | 더미 데이터 기반 학습 | 합성 전이 데이터 |
| v1.1 | 사용자 실시간 데이터 축적 | 로컬 로그 (동의 시) |
| v1.2 | 축적 데이터로 재학습 | 로컬 Fine-tuning |
| v2.0 | 사전학습 모델 적용 | 공개 감정 데이터셋 |
| v3.0 | AWS SageMaker 학습 | 대규모 데이터 |

---

## 9. 성능 요구사항

| 항목 | 목표 |
|------|------|
| 추론 시간 | < 100ms (CPU) |
| 모델 크기 | < 5MB |
| 메모리 사용 | < 100MB (모델 로드 시) |
| 최소 데이터 | 5개 주기 후 예측 시작 |
| 예측 정확도 (MVP) | 감정 전이 방향 일치 ≥ 40% |
