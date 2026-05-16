"""
modules/voice_features.py - 구조화된 음성 특징 추출
librosa 기반 특징 추출 결과를 UI/로그에 표시 가능한 형태로 구조화합니다.

추출 특징:
- Energy: RMS mean/std, peak, dBFS
- Pitch: F0 mean/std/range
- Spectral: centroid, bandwidth, rolloff, ZCR
- MFCC: 13계수 mean/std
- Rhythm: tempo indicator

UI 요약 출력:
- energy_level (low/medium/high)
- pitch_level (low/medium/high)
- pitch_variation (stable/moderate/variable)
- speech_activity (none/low/medium/high)
- spectral_brightness (dark/neutral/bright)
- feature_confidence (low/medium/high)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config, DEFAULT_CONFIG


@dataclass
class VoiceFeatures:
    """구조화된 음성 특징 데이터"""
    # Raw values
    rms_mean: float = 0.0
    rms_std: float = 0.0
    peak_amplitude: float = 0.0
    dbfs: float = -96.0
    zcr: float = 0.0
    spectral_centroid: float = 0.0
    spectral_bandwidth: float = 0.0
    spectral_rolloff: float = 0.0
    pitch_mean: float = 0.0
    pitch_std: float = 0.0
    pitch_range: float = 0.0
    tempo: float = 0.0
    energy_variation: float = 0.0
    mfcc_mean: List[float] = field(default_factory=lambda: [0.0] * 13)
    mfcc_std: List[float] = field(default_factory=lambda: [0.0] * 13)

    # UI 요약 (사람이 읽기 쉬운 형태)
    energy_level: str = "low"          # low / medium / high
    pitch_level: str = "medium"        # low / medium / high
    pitch_variation: str = "stable"    # stable / moderate / variable
    speech_activity: str = "none"      # none / low / medium / high
    spectral_brightness: str = "neutral"  # dark / neutral / bright
    feature_confidence: str = "low"    # low / medium / high

    # 추출 성공 여부
    is_valid: bool = False
    error: Optional[str] = None

    def to_feature_vector(self) -> np.ndarray:
        """분류기 입력용 특징 벡터 (35차원)"""
        vec = []
        vec.extend(self.mfcc_mean)        # 13
        vec.extend(self.mfcc_std)         # 13
        vec.append(self.rms_mean)         # 1
        vec.append(self.pitch_mean)       # 1
        vec.append(self.pitch_std)        # 1
        vec.append(self.rms_std)          # 1 (energy as RMS std)
        vec.append(self.zcr)              # 1
        vec.append(self.spectral_centroid) # 1
        vec.append(self.spectral_bandwidth) # 1
        vec.append(self.tempo)            # 1
        vec.append(self.energy_variation) # 1
        return np.array(vec, dtype=np.float32)

    def to_log_string(self) -> str:
        """로그 출력용 요약 문자열"""
        return (
            f"rms={self.rms_mean:.4f} pitch_mean={self.pitch_mean:.1f} "
            f"pitch_std={self.pitch_std:.1f} zcr={self.zcr:.3f} "
            f"centroid={self.spectral_centroid:.0f} "
            f"energy={self.energy_level} pitch={self.pitch_level} "
            f"variation={self.pitch_variation}"
        )

    def to_ui_summary(self) -> Dict[str, str]:
        """UI 표시용 딕셔너리"""
        return {
            "에너지": self.energy_level,
            "피치": self.pitch_level,
            "피치 변동": self.pitch_variation,
            "발화 활동": self.speech_activity,
            "음색 밝기": self.spectral_brightness,
            "특징 신뢰도": self.feature_confidence,
        }


class VoiceFeatureExtractor:
    """librosa 기반 음성 특징 추출기"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._librosa = None
        self._initialized = False

    def initialize(self) -> bool:
        """librosa 로드"""
        try:
            import librosa
            self._librosa = librosa
            self._initialized = True
            return True
        except ImportError:
            return False

    def extract(self, audio: np.ndarray, sample_rate: int = 16000) -> VoiceFeatures:
        """
        오디오에서 음성 특징을 추출합니다.

        Args:
            audio: float32 mono 오디오
            sample_rate: 샘플레이트

        Returns:
            VoiceFeatures (is_valid=True if success)
        """
        if not self._initialized:
            if not self.initialize():
                return VoiceFeatures(error="librosa 미설치", is_valid=False)

        if audio is None or len(audio) < sample_rate * 0.5:
            return VoiceFeatures(error="오디오 데이터 부족", is_valid=False)

        try:
            librosa = self._librosa
            features = VoiceFeatures()

            # Energy
            rms = librosa.feature.rms(y=audio)
            features.rms_mean = float(np.mean(rms))
            features.rms_std = float(np.std(rms))
            features.peak_amplitude = float(np.max(np.abs(audio)))
            features.dbfs = float(20 * np.log10(max(features.rms_mean, 1e-10)))
            features.energy_variation = features.rms_std / max(features.rms_mean, 1e-6)

            # ZCR
            zcr = librosa.feature.zero_crossing_rate(audio)
            features.zcr = float(np.mean(zcr))

            # Spectral
            centroid = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)
            features.spectral_centroid = float(np.mean(centroid))

            bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sample_rate)
            features.spectral_bandwidth = float(np.mean(bandwidth))

            rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sample_rate)
            features.spectral_rolloff = float(np.mean(rolloff))

            # Pitch
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sample_rate)
            pitch_vals = pitches[magnitudes > np.median(magnitudes)]
            pitch_vals = pitch_vals[pitch_vals > 50]  # 50Hz 이하 제거 (노이즈)

            if len(pitch_vals) > 0:
                features.pitch_mean = float(np.mean(pitch_vals))
                features.pitch_std = float(np.std(pitch_vals))
                features.pitch_range = float(np.max(pitch_vals) - np.min(pitch_vals))
            else:
                features.pitch_mean = 0.0
                features.pitch_std = 0.0
                features.pitch_range = 0.0

            # MFCC
            mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=13)
            features.mfcc_mean = np.mean(mfcc, axis=1).tolist()
            features.mfcc_std = np.std(mfcc, axis=1).tolist()

            # Tempo
            try:
                tempo, _ = librosa.beat.beat_track(y=audio, sr=sample_rate)
                features.tempo = float(np.atleast_1d(tempo)[0])
            except Exception:
                features.tempo = 0.0

            # UI 요약 계산
            self._compute_ui_summary(features)

            features.is_valid = True
            return features

        except Exception as e:
            return VoiceFeatures(error=f"특징 추출 실패: {e}", is_valid=False)

    def _compute_ui_summary(self, f: VoiceFeatures):
        """특징값에서 사람이 읽을 수 있는 요약을 계산"""
        # Energy level
        if f.rms_mean < 0.01:
            f.energy_level = "low"
        elif f.rms_mean < 0.05:
            f.energy_level = "medium"
        else:
            f.energy_level = "high"

        # Pitch level
        if f.pitch_mean < 120:
            f.pitch_level = "low"
        elif f.pitch_mean < 250:
            f.pitch_level = "medium"
        else:
            f.pitch_level = "high"

        # Pitch variation
        if f.pitch_std < 20:
            f.pitch_variation = "stable"
        elif f.pitch_std < 50:
            f.pitch_variation = "moderate"
        else:
            f.pitch_variation = "variable"

        # Speech activity (from energy variation)
        if f.rms_mean < 0.005:
            f.speech_activity = "none"
        elif f.energy_variation < 0.3:
            f.speech_activity = "low"
        elif f.energy_variation < 0.8:
            f.speech_activity = "medium"
        else:
            f.speech_activity = "high"

        # Spectral brightness
        if f.spectral_centroid < 1000:
            f.spectral_brightness = "dark"
        elif f.spectral_centroid < 2500:
            f.spectral_brightness = "neutral"
        else:
            f.spectral_brightness = "bright"

        # Feature confidence (based on data quality)
        if f.rms_mean < 0.005 or f.pitch_mean == 0:
            f.feature_confidence = "low"
        elif f.rms_mean > 0.02 and f.pitch_mean > 80:
            f.feature_confidence = "high"
        else:
            f.feature_confidence = "medium"
