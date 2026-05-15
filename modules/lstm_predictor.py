"""
modules/lstm_predictor.py - LSTM 기반 감정 예측 모듈
시계열 감정 데이터를 기반으로 다음 주기의 감정을 예측합니다.
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
        self.timestamps: List[datetime] = []
        self._max_buffer = sequence_length * 3

    def add(self, scores: Dict[str, float], timestamp: Optional[datetime] = None):
        """새 주기 평균 점수 추가"""
        self.buffer.append(scores)
        self.timestamps.append(timestamp or datetime.now())

        if len(self.buffer) > self._max_buffer:
            self.buffer = self.buffer[-self._max_buffer:]
            self.timestamps = self.timestamps[-self._max_buffer:]

    def is_ready(self) -> bool:
        """예측 가능 여부"""
        return len(self.buffer) >= self.min_data_points

    def get_input_sequence(self) -> np.ndarray:
        """
        LSTM 입력 형태로 변환

        Returns:
            shape: (1, sequence_length, n_features)
        """
        recent = self.buffer[-self.sequence_length:]

        # 패딩: 데이터 부족 시 첫 데이터로 채움
        while len(recent) < self.sequence_length:
            recent.insert(0, recent[0])

        sequence = np.array([
            [scores.get(e, 0.0) for e in EMOTIONS]
            for scores in recent
        ], dtype=np.float32)

        return sequence.reshape(1, self.sequence_length, len(EMOTIONS))

    def reset(self):
        """버퍼 초기화"""
        self.buffer.clear()
        self.timestamps.clear()

    @property
    def count(self) -> int:
        return len(self.buffer)


class LSTMPredictor:
    """LSTM 기반 감정 예측"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self.model = None
        self.time_series = TimeSeriesBuffer(
            sequence_length=config.lstm_sequence_length,
            min_data_points=config.lstm_min_data_points,
        )
        self._initialized = False

    def initialize(self) -> bool:
        """모델 로드 또는 생성"""
        try:
            if os.path.exists(self.config.lstm_model_path):
                import tensorflow as tf
                self.model = tf.keras.models.load_model(
                    self.config.lstm_model_path, compile=False
                )
            else:
                self.model = self._build_model()

            self._initialized = True
            return True

        except ImportError:
            print("[WARNING] TensorFlow 미설치. 단순 예측 모드로 동작합니다.")
            self._initialized = True  # 폴백 모드
            return True
        except Exception as e:
            print(f"[ERROR] LSTM 모델 초기화 실패: {e}")
            self._initialized = True  # 폴백 모드로 계속 동작
            return True

    def add_data_point(self, avg_scores: Dict[str, float],
                       timestamp: Optional[datetime] = None):
        """주기 평균 데이터 추가"""
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

        # 모델이 있으면 모델 추론
        if self.model is not None:
            try:
                input_seq = self.time_series.get_input_sequence()
                prediction = self.model.predict(input_seq, verbose=0)[0]
                scores = dict(zip(EMOTIONS, prediction.tolist()))
            except Exception:
                scores = self._simple_prediction()
        else:
            # 모델 없으면 단순 이동 평균 기반 예측
            scores = self._simple_prediction()

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
        """시계열 데이터 초기화"""
        self.time_series.reset()

    @property
    def is_ready(self) -> bool:
        return self.time_series.is_ready()

    @property
    def data_count(self) -> int:
        return self.time_series.count

    def _build_model(self):
        """LSTM 모델 생성"""
        try:
            import tensorflow as tf
            from tensorflow.keras import layers, Model

            inputs = layers.Input(shape=(self.config.lstm_sequence_length,
                                         self.config.lstm_n_features))
            x = layers.LSTM(64, return_sequences=True)(inputs)
            x = layers.Dropout(0.2)(x)
            x = layers.LSTM(32)(x)
            x = layers.Dropout(0.2)(x)
            x = layers.Dense(16, activation='relu')(x)
            outputs = layers.Dense(self.config.lstm_n_features,
                                   activation='softmax')(x)

            model = Model(inputs=inputs, outputs=outputs)
            model.compile(optimizer='adam', loss='categorical_crossentropy')
            return model

        except Exception:
            return None

    def _simple_prediction(self) -> Dict[str, float]:
        """단순 이동 평균 기반 예측 (폴백)"""
        recent = self.time_series.buffer[-3:]
        if not recent:
            return {e: 1.0 / len(EMOTIONS) for e in EMOTIONS}

        avg_scores = {e: 0.0 for e in EMOTIONS}
        for scores in recent:
            for e in EMOTIONS:
                avg_scores[e] += scores.get(e, 0.0)

        n = len(recent)
        return {e: s / n for e, s in avg_scores.items()}
