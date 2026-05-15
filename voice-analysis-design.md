# Voice Analysis Design - Multimodal Emotion State Monitor

## 1. 개요

본 문서는 음성 기반 감정 분석 모듈의 상세 설계를 정의합니다.
마이크로부터 실시간 오디오를 수집하고, 음성 특징을 추출하여 9가지 감정 중 하나로 분류합니다.

---

## 2. 모듈 구성

```
modules/
├── microphone.py          # 마이크 오디오 캡처 + 버퍼 관리
└── voice_emotion.py       # 음성 특징 추출 + 감정 분류
```

---

## 3. 마이크 모듈 (microphone.py)

### 3.1 클래스 설계

```python
class MicrophoneCapture:
    """실시간 마이크 오디오 캡처 및 버퍼 관리"""
    
    def __init__(self, sample_rate: int = 16000, 
                 cycle_seconds: int = 10):
        self.sample_rate = sample_rate
        self.cycle_seconds = cycle_seconds
        self.stream = None
        self.buffer = AudioRingBuffer(sample_rate * cycle_seconds)
        self._is_capturing = False
    
    def open(self) -> bool:
        """마이크 스트림을 열고 캡처 시작"""
    
    def get_buffer(self) -> np.ndarray:
        """현재 버퍼의 오디오 데이터 반환 (복사본)"""
    
    def clear_buffer(self):
        """버퍼 초기화 (주기 종료 시)"""
    
    def update_cycle(self, new_cycle_seconds: int):
        """주기 변경 시 버퍼 크기 재설정"""
    
    def is_silence(self, threshold: float = 0.01) -> bool:
        """현재 버퍼가 무음인지 판단"""
    
    def close(self):
        """마이크 스트림 종료"""
    
    @property
    def is_opened(self) -> bool:
        """마이크 상태 확인"""
```

### 3.2 오디오 링 버퍼

```python
class AudioRingBuffer:
    """고정 크기 링 버퍼로 오디오 데이터 관리"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.buffer = np.zeros(max_size, dtype=np.float32)
        self.write_pos = 0
        self.is_full = False
    
    def write(self, data: np.ndarray):
        """새 오디오 데이터를 버퍼에 추가"""
        n = len(data)
        if self.write_pos + n <= self.max_size:
            self.buffer[self.write_pos:self.write_pos + n] = data
            self.write_pos += n
        else:
            # 링 버퍼: 오래된 데이터 덮어쓰기
            overflow = (self.write_pos + n) - self.max_size
            self.buffer[self.write_pos:] = data[:n - overflow]
            self.buffer[:overflow] = data[n - overflow:]
            self.write_pos = overflow
            self.is_full = True
    
    def read_all(self) -> np.ndarray:
        """버퍼 전체 데이터 반환"""
        if self.is_full:
            return np.concatenate([
                self.buffer[self.write_pos:],
                self.buffer[:self.write_pos]
            ])
        return self.buffer[:self.write_pos].copy()
    
    def clear(self):
        """버퍼 초기화"""
        self.buffer[:] = 0
        self.write_pos = 0
        self.is_full = False
```

### 3.3 오디오 캡처 설정

```python
AUDIO_CONFIG = {
    "sample_rate": 16000,       # 16kHz (음성 분석 표준)
    "channels": 1,              # 모노
    "chunk_size": 1024,         # 콜백당 프레임 수
    "format": "float32",        # 데이터 형식
    "silence_threshold": 0.01,  # 무음 판단 임계값 (RMS)
    "silence_duration": 2.0,    # 무음 지속 시간 (초) → 무음 상태 판단
}
```

### 3.4 마이크-TTS 간섭 방지

```python
class AudioMutex:
    """음성 안내 출력 중 마이크 입력 일시 중단"""
    
    def __init__(self):
        self._tts_playing = False
    
    def set_tts_playing(self, playing: bool):
        self._tts_playing = playing
    
    def should_capture(self) -> bool:
        """TTS 출력 중이면 캡처 중단"""
        return not self._tts_playing
```

---

## 4. 음성 감정 분류 모듈 (voice_emotion.py)

### 4.1 클래스 설계

```python
class VoiceEmotionClassifier:
    """음성 특징 기반 감정 분류"""
    
    EMOTIONS = ["neutral", "happy", "sad", "angry",
                "surprised", "fearful", "disgusted", "stressed", "calm"]
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.scaler = None  # 특징 정규화용
        self.model_path = model_path
    
    def initialize(self) -> bool:
        """분류 모델 로드"""
    
    def classify(self, audio_data: np.ndarray, 
                 sample_rate: int = 16000) -> Optional[EmotionScores]:
        """
        오디오 데이터로 감정 분류
        
        Args:
            audio_data: 오디오 신호 (float32, mono)
            sample_rate: 샘플레이트 (Hz)
        
        Returns:
            EmotionScores 또는 분류 실패 시 None
        """
    
    def extract_features(self, audio: np.ndarray, 
                         sr: int) -> Optional[np.ndarray]:
        """음성 특징 벡터 추출"""
    
    def _is_valid_audio(self, audio: np.ndarray) -> bool:
        """유효한 음성 데이터인지 검증 (무음, 노이즈 과다 등)"""
```

### 4.2 특징 추출 상세

```python
def extract_features(self, audio: np.ndarray, sr: int) -> np.ndarray:
    """
    음성에서 감정 관련 특징을 추출합니다.
    
    추출 특징:
    - MFCC: 13개 계수의 평균 + 표준편차 = 26차원
    - Mel Spectrogram: 평균 에너지 = 1차원
    - Pitch (F0): 평균 + 표준편차 = 2차원
    - Energy (RMS): 평균 + 표준편차 = 2차원
    - Zero-Crossing Rate: 평균 = 1차원
    - Spectral Centroid: 평균 = 1차원
    - Spectral Bandwidth: 평균 = 1차원
    - Tempo: 1차원
    
    총 특징 차원: 35
    """
    features = []
    
    # 1. MFCC (13 계수 × 2 = 26)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
    features.extend(np.mean(mfcc, axis=1))
    features.extend(np.std(mfcc, axis=1))
    
    # 2. Mel Spectrogram 에너지 (1)
    mel = librosa.feature.melspectrogram(y=audio, sr=sr)
    features.append(np.mean(mel))
    
    # 3. Pitch F0 (2)
    pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    features.append(np.mean(pitch_values) if len(pitch_values) > 0 else 0)
    features.append(np.std(pitch_values) if len(pitch_values) > 0 else 0)
    
    # 4. Energy RMS (2)
    rms = librosa.feature.rms(y=audio)
    features.append(np.mean(rms))
    features.append(np.std(rms))
    
    # 5. Zero-Crossing Rate (1)
    zcr = librosa.feature.zero_crossing_rate(audio)
    features.append(np.mean(zcr))
    
    # 6. Spectral Centroid (1)
    centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
    features.append(np.mean(centroid))
    
    # 7. Spectral Bandwidth (1)
    bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)
    features.append(np.mean(bandwidth))
    
    # 8. Tempo (1)
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    features.append(float(tempo))
    
    return np.array(features, dtype=np.float32)
```

### 4.3 분류 모델 접근법

#### MVP 단계: scikit-learn 기반

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

class SimpleVoiceModel:
    """MVP용 간단한 음성 감정 분류기"""
    
    def __init__(self):
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    def train(self, features: np.ndarray, labels: np.ndarray):
        """학습"""
        scaled = self.scaler.fit_transform(features)
        self.classifier.fit(scaled, labels)
        self.is_fitted = True
    
    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """예측 (확률 분포 반환)"""
        scaled = self.scaler.transform(features.reshape(1, -1))
        proba = self.classifier.predict_proba(scaled)[0]
        return dict(zip(self.classifier.classes_, proba))
    
    def save(self, path: str):
        joblib.dump({"clf": self.classifier, "scaler": self.scaler}, path)
    
    def load(self, path: str):
        data = joblib.load(path)
        self.classifier = data["clf"]
        self.scaler = data["scaler"]
        self.is_fitted = True
```

#### 향후 확장: CNN 기반

```
[오디오 데이터]
     │
     ▼
[Mel Spectrogram 변환 (128×128 이미지)]
     │
     ▼
[CNN 모델 (ResNet-18 또는 VGG-like)]
     │
     ▼
[9개 감정 확률 분포]
```

---

## 5. 학습 데이터

### 5.1 공개 데이터셋

| 데이터셋 | 감정 수 | 화자 수 | 언어 | 용도 |
|----------|---------|---------|------|------|
| RAVDESS | 8 | 24 | 영어 | 기본 학습 |
| TESS | 7 | 2 | 영어 | 보조 학습 |
| SAVEE | 7 | 4 | 영어 | 검증 |
| EmoDB | 7 | 10 | 독일어 | 크로스 언어 테스트 |

### 5.2 감정 매핑 (데이터셋 → 내부 체계)

```python
RAVDESS_MAPPING = {
    "01": "neutral",
    "02": "calm",
    "03": "happy",
    "04": "sad",
    "05": "angry",
    "06": "fearful",
    "07": "disgusted",
    "08": "surprised",
}
# stressed: angry + fearful 조합으로 증강
```

---

## 6. 음성 분석 흐름 타이밍

```
주기 = 10초 기준:

0s          5s          10s
│───────────│───────────│
│← 오디오 수집 (연속) →│
│                       │
│                       ▼
│               [버퍼 데이터 추출]
│               [특징 추출: ~200ms]
│               [분류 추론: ~50ms]
│               [결과 전달]
│               [버퍼 초기화]
│
│← 새 주기 시작 ─────────
```

---

## 7. 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| 마이크 열기 실패 | UI에 경고, 음성 분석 비활성화 |
| 오디오 스트림 끊김 | 재연결 시도 (최대 3회) |
| 무음 상태 지속 | "음성 미감지" 상태 반환, 분류 스킵 |
| 특징 추출 실패 (NaN) | None 반환, 로그 기록 |
| 모델 추론 실패 | None 반환, 다음 주기에서 재시도 |
| 노이즈 과다 (SNR < 3dB) | "분석 불가" 상태, 로그 기록 |
