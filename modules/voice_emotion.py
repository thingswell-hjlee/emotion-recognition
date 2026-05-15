"""
modules/voice_emotion.py - 음성 감정 분류 모듈
librosa로 음성 특징을 추출하고 감정을 분류합니다.
"""

import numpy as np
from typing import Dict, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMOTIONS, Config, DEFAULT_CONFIG
from utils.data_types import EmotionScores


class VoiceEmotionClassifier:
    """음성 특징 기반 감정 분류"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._model = None
        self._scaler = None
        self._initialized = False
        self._librosa = None

    def initialize(self) -> bool:
        """모델 및 라이브러리 로드"""
        try:
            import librosa
            self._librosa = librosa
        except ImportError:
            print("[ERROR] librosa가 설치되지 않았습니다: pip install librosa")
            return False

        # 학습된 모델 로드 시도
        if os.path.exists(self.config.voice_model_path):
            try:
                import joblib
                data = joblib.load(self.config.voice_model_path)
                self._model = data.get("clf")
                self._scaler = data.get("scaler")
                self._initialized = True
                return True
            except Exception as e:
                print(f"[WARNING] 음성 모델 로드 실패: {e}")

        # 모델 없으면 규칙 기반 분류 사용 (MVP)
        self._initialized = True
        return True

    def classify(self, audio_data: np.ndarray,
                 sample_rate: int = 16000) -> Optional[EmotionScores]:
        """
        오디오 데이터로 감정 분류

        Args:
            audio_data: float32 mono 오디오 신호
            sample_rate: 샘플레이트 (Hz)

        Returns:
            EmotionScores 또는 실패 시 None
        """
        if not self._initialized:
            if not self.initialize():
                return None

        # 유효성 검증
        if not self._is_valid_audio(audio_data):
            return None

        # 특징 추출
        features = self.extract_features(audio_data, sample_rate)
        if features is None:
            return None

        # 분류
        if self._model is not None:
            scores = self._model_predict(features)
        else:
            scores = self._rule_based_classify(features)

        if scores is None:
            return None

        dominant = max(scores, key=scores.get)
        return EmotionScores(
            scores=scores,
            dominant=dominant,
            confidence=scores[dominant],
            source="voice",
        )

    def extract_features(self, audio: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """
        음성 특징 벡터 추출 (35차원)

        Features:
        - MFCC 13계수 × 2 (mean, std) = 26
        - Mel spectrogram mean = 1
        - Pitch mean, std = 2
        - RMS mean, std = 2
        - ZCR mean = 1
        - Spectral centroid mean = 1
        - Spectral bandwidth mean = 1
        - Tempo = 1
        Total = 35
        """
        try:
            librosa = self._librosa
            features = []

            # MFCC (26)
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            features.extend(np.mean(mfcc, axis=1).tolist())
            features.extend(np.std(mfcc, axis=1).tolist())

            # Mel spectrogram energy (1)
            mel = librosa.feature.melspectrogram(y=audio, sr=sr)
            features.append(float(np.mean(mel)))

            # Pitch (2)
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
            pitch_vals = pitches[magnitudes > np.median(magnitudes)]
            features.append(float(np.mean(pitch_vals)) if len(pitch_vals) > 0 else 0.0)
            features.append(float(np.std(pitch_vals)) if len(pitch_vals) > 0 else 0.0)

            # RMS energy (2)
            rms = librosa.feature.rms(y=audio)
            features.append(float(np.mean(rms)))
            features.append(float(np.std(rms)))

            # Zero-crossing rate (1)
            zcr = librosa.feature.zero_crossing_rate(audio)
            features.append(float(np.mean(zcr)))

            # Spectral centroid (1)
            centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
            features.append(float(np.mean(centroid)))

            # Spectral bandwidth (1)
            bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)
            features.append(float(np.mean(bandwidth)))

            # Tempo (1)
            tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
            features.append(float(np.atleast_1d(tempo)[0]))

            return np.array(features, dtype=np.float32)

        except Exception:
            return None

    def _model_predict(self, features: np.ndarray) -> Optional[Dict[str, float]]:
        """학습된 모델로 예측"""
        try:
            scaled = self._scaler.transform(features.reshape(1, -1))
            proba = self._model.predict_proba(scaled)[0]
            classes = self._model.classes_
            return dict(zip(classes, proba.tolist()))
        except Exception:
            return None

    def _rule_based_classify(self, features: np.ndarray) -> Dict[str, float]:
        """
        규칙 기반 간이 분류 (MVP, 모델 없을 때)
        에너지, 피치, ZCR 등을 기반으로 대략적 분류
        """
        # 특징 인덱스: MFCC(0-25), mel(26), pitch_mean(27), pitch_std(28),
        #             rms_mean(29), rms_std(30), zcr(31), centroid(32), bw(33), tempo(34)
        rms_mean = features[29] if len(features) > 29 else 0.01
        pitch_mean = features[27] if len(features) > 27 else 200.0
        zcr_mean = features[31] if len(features) > 31 else 0.05

        scores = {e: 0.05 for e in EMOTIONS}  # 기본값

        # 에너지 높으면 → angry/happy/surprised
        if rms_mean > 0.05:
            scores["angry"] += 0.2
            scores["happy"] += 0.15
            scores["surprised"] += 0.1
        # 에너지 낮으면 → sad/calm/neutral
        elif rms_mean < 0.01:
            scores["sad"] += 0.15
            scores["calm"] += 0.2
            scores["neutral"] += 0.15

        # 피치 높으면 → happy/surprised/fearful
        if pitch_mean > 300:
            scores["happy"] += 0.15
            scores["surprised"] += 0.15
            scores["fearful"] += 0.1
        # 피치 낮으면 → sad/angry
        elif pitch_mean < 150:
            scores["sad"] += 0.1
            scores["angry"] += 0.1

        # ZCR 높으면 → stressed
        if zcr_mean > 0.1:
            scores["stressed"] += 0.15

        # 정규화
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores

    def _is_valid_audio(self, audio: np.ndarray) -> bool:
        """유효한 음성 데이터인지 검증"""
        if audio is None or len(audio) == 0:
            return False
        if len(audio) < 1600:  # 최소 0.1초 (16kHz 기준)
            return False
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 0.001:  # 거의 무음
            return False
        return True

    @property
    def is_ready(self) -> bool:
        return self._initialized
