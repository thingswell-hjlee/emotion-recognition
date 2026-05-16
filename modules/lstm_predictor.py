"""
modules/lstm_predictor.py - LSTM 기반 감정 예측 모듈
모델 파일 없어도 안전하게 동작 (더미 예측기 폴백)

동작 모드:
1) LSTM 모델 파일 있음 → 모델 추론
2) TensorFlow 설치됨 + 모델 없음 → 모델 생성 후 추론
3) TensorFlow 미설치 or 모든 실패 → 단순 이동평균 예측 (폴백)
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMOTIONS, Config, DEFAULT_CONFIG
from utils.data_types import EmotionScores


class TimeSeriesBuffer:
    """LSTM 입력을 위한 시계열 데이터 관리"""

    def __init__(self, sequence_length: int = 10, min_data_points: int = 5):
        self.sequence_length = sequence_length
        self.min_data_points = min_data_points
        self.buffer: List[Dict[str, float]] = []
        self._max_buffer = sequence_length * 3

    def add(self, scores: Dict[str, float]):
        """새 주기 평균 점수 추가"""
        self.buffer.append(scores)
        if len(self.buffer) > self._max_buffer:
            self.buffer = self.buffer[-self._max_buffer:]

    def is_ready(self) -> bool:
        return len(self.buffer) >= self.min_data_points

    def get_input_sequence(self) -> np.ndarray:
        """LSTM 입력 형태로 변환: (1, seq_len, n_features)"""
        recent = self.buffer[-self.sequence_length:]
        while len(recent) < self.sequence_length:
            recent.insert(0, recent[0])
        sequence = np.array([
            [scores.get(e, 0.0) for e in EMOTIONS]
            for scores in recent
        ], dtype=np.float32)
        return sequence.reshape(1, self.sequence_length, len(EMOTIONS))

    def reset(self):
        self.buffer.clear()

    @property
    def count(self) -> int:
        return len(self.buffer)


class LSTMPredictor:
    """LSTM 기반 감정 예측 (안전한 폴백 포함)"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self.model = None
        self.time_series = TimeSeriesBuffer(
            sequence_length=config.lstm_sequence_length,
            min_data_points=config.lstm_min_data_points,
        )
        self._initialized = False
        self._use_model = False
        self._init_error: Optional[str] = None

    def initialize(self) -> bool:
        """모델 로드 시도 (실패 시 폴백 모드)"""
        if not self.config.use_lstm:
            # minimal/face/voice 모드: 더미 예측만 사용
            self._initialized = True
            self._use_model = False
            return True

        # LSTM 모델 로드 시도
        try:
            import tensorflow as tf
            if os.path.exists(self.config.lstm_model_path):
                self.model = tf.keras.models.load_model(
                    self.config.lstm_model_path, compile=False
                )
                self._use_model = True
            else:
                # 모델 파일 없음 → 생성 시도
                self.model = self._build_model()
                self._use_model = (self.model is not None)

        except ImportError:
            self._init_error = "TensorFlow 미설치. 단순 예측 모드로 동작합니다."
            self._use_model = False
        except Exception as e:
            self._init_error = f"LSTM 초기화 실패: {e}. 단순 예측 모드로 동작합니다."
            self._use_model = False

        self._initialized = True
        return True

    def add_data_point(self, avg_scores: Dict[str, float]):
        """주기 평균 데이터 추가"""
        self.time_series.add(avg_scores)

    def predict(self) -> Optional[EmotionScores]:
        """
        다음 주기 감정 예측
        어떤 상황에서도 예외를 외부로 전파하지 않음
        """
        if not self.time_series.is_ready():
            return None

        if not self._initialized:
            self.initialize()

        try:
            if self._use_model and self.model is not None:
                scores = self._model_predict()
            else:
                scores = self._dummy_predict()
        except Exception:
            scores = self._dummy_predict()

        if scores is None:
            scores = self._dummy_predict()

        # 정규화
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        dominant = max(scores, key=scores.get)
        return EmotionScores(
            scores=scores,
            dominant=dominant,
            confidence=scores[dominant],
            source="predicted",
        )

    def reset(self):
        """시계열 초기화"""
        self.time_series.reset()

    @property
    def is_ready(self) -> bool:
        return self.time_series.is_ready()

    @property
    def data_count(self) -> int:
        return self.time_series.count

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    @property
    def mode_name(self) -> str:
        if self._use_model:
            return "LSTM 모델"
        return "이동평균 예측"

    def _model_predict(self) -> Optional[Dict[str, float]]:
        """LSTM 모델 추론"""
        try:
            input_seq = self.time_series.get_input_sequence()
            prediction = self.model.predict(input_seq, verbose=0)[0]
            return dict(zip(EMOTIONS, prediction.tolist()))
        except Exception:
            return None

    def _dummy_predict(self) -> Dict[str, float]:
        """
        더미 예측: 최근 3개 주기 이동평균 + neutral/calm 방향 편향
        모델 없어도 합리적인 예측 제공
        """
        recent = self.time_series.buffer[-3:]
        if not recent:
            return {e: 1.0 / len(EMOTIONS) for e in EMOTIONS}

        # 이동 평균
        avg_scores = {e: 0.0 for e in EMOTIONS}
        for scores in recent:
            for e in EMOTIONS:
                avg_scores[e] += scores.get(e, 0.0)
        n = len(recent)
        avg_scores = {e: s / n for e, s in avg_scores.items()}

        # neutral/calm 방향으로 약간 편향 (안정화 예측)
        avg_scores["neutral"] = avg_scores.get("neutral", 0) * 1.1 + 0.02
        avg_scores["calm"] = avg_scores.get("calm", 0) * 1.05 + 0.01

        return avg_scores

    def _build_model(self):
        """간단한 LSTM 모델 생성 (학습 없이 구조만)"""
        try:
            import tensorflow as tf
            from tensorflow.keras import layers, Model

            inputs = layers.Input(shape=(self.config.lstm_sequence_length,
                                         self.config.lstm_n_features))
            x = layers.LSTM(32, return_sequences=False)(inputs)
            x = layers.Dropout(0.2)(x)
            x = layers.Dense(16, activation='relu')(x)
            outputs = layers.Dense(self.config.lstm_n_features,
                                   activation='softmax')(x)

            model = Model(inputs=inputs, outputs=outputs)
            model.compile(optimizer='adam', loss='categorical_crossentropy')
            return model
        except Exception:
            return None
