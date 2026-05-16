"""
modules/expression_sequence_buffer.py - 표정 시퀀스 링 버퍼
최근 30~120초의 표정 분석 결과를 ring buffer로 관리하며,
LSTM 입력용 fixed-length sequence를 생성합니다.

핵심 기능:
- 최근 30~120초 ring buffer (설정 가능)
- 저장 항목: timestamp, emotion_label, scores, confidence, face_detected, frame_quality
- sequence quality score 계산 (valid_face_ratio, avg_confidence, missing_ratio)
- LSTM 입력용 fixed-length sequence 생성 (균등 시간 간격 리샘플링)
- low confidence 결과에 낮은 weight 반영
"""

import time
import threading
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMOTIONS


@dataclass
class BufferEntry:
    """버퍼에 저장되는 단일 분석 결과"""
    timestamp: float                    # time.time() 기준
    emotion_label: str                  # dominant emotion
    scores: Dict[str, float]            # 9가지 감정별 점수
    confidence: float                   # 분석 confidence (0.0~1.0)
    face_detected: bool                 # 얼굴 감지 여부
    frame_quality: float = 1.0          # 프레임 품질 (0.0~1.0, 기본 1.0)


@dataclass
class SequenceQuality:
    """시퀀스 품질 지표"""
    valid_face_ratio: float = 0.0       # 유효 얼굴 감지 비율
    avg_confidence: float = 0.0         # 평균 confidence
    missing_ratio: float = 1.0          # 누락(미감지) 비율
    total_entries: int = 0              # 버퍼 내 총 엔트리 수
    time_span_sec: float = 0.0          # 버퍼가 커버하는 시간 범위

    @property
    def is_sufficient(self) -> bool:
        """LSTM 입력으로 사용하기에 충분한 품질인지"""
        return (
            self.valid_face_ratio >= 0.3 and
            self.avg_confidence >= 0.4 and
            self.total_entries >= 5
        )

    @property
    def quality_score(self) -> float:
        """종합 품질 점수 (0.0~1.0)"""
        if self.total_entries == 0:
            return 0.0
        # 가중 평균: face_ratio 40%, confidence 40%, (1-missing) 20%
        score = (
            self.valid_face_ratio * 0.4 +
            self.avg_confidence * 0.4 +
            (1.0 - self.missing_ratio) * 0.2
        )
        return max(0.0, min(1.0, score))


@dataclass
class LSTMSequence:
    """LSTM 입력용 고정 길이 시퀀스"""
    data: np.ndarray                    # shape: (sequence_length, n_features)
    weights: np.ndarray                 # shape: (sequence_length,) - 각 timestep의 가중치
    quality: SequenceQuality            # 시퀀스 품질 정보
    timestamp: float = field(default_factory=time.time)

    @property
    def is_valid(self) -> bool:
        """유효한 LSTM 입력인지"""
        return self.quality.is_sufficient and self.data.shape[0] > 0


class ExpressionSequenceBuffer:
    """
    표정 분석 결과를 시간 기반 ring buffer로 관리하고,
    LSTM 입력용 fixed-length sequence를 생성합니다.
    """

    def __init__(
        self,
        buffer_duration_sec: float = 60.0,
        min_duration_sec: float = 30.0,
        max_duration_sec: float = 120.0,
        sequence_length: int = 10,
        n_features: int = 9,
        confidence_weight_threshold: float = 0.6,
        low_confidence_weight: float = 0.3,
    ):
        """
        Args:
            buffer_duration_sec: 기본 버퍼 유지 시간 (초)
            min_duration_sec: 최소 버퍼 시간 (30초)
            max_duration_sec: 최대 버퍼 시간 (120초)
            sequence_length: LSTM 입력 시퀀스 길이
            n_features: 감정 feature 수 (기본 9 = EMOTIONS 개수)
            confidence_weight_threshold: 이 미만이면 low confidence로 간주
            low_confidence_weight: low confidence 결과의 가중치
        """
        self._buffer_duration = max(min_duration_sec, min(max_duration_sec, buffer_duration_sec))
        self._min_duration = min_duration_sec
        self._max_duration = max_duration_sec
        self._sequence_length = sequence_length
        self._n_features = n_features
        self._confidence_threshold = confidence_weight_threshold
        self._low_confidence_weight = low_confidence_weight

        # Ring buffer (deque로 구현, 시간 기반 만료)
        self._buffer: deque = deque()
        self._lock = threading.Lock()

        # 감정 키 목록 (순서 고정)
        self._emotion_keys = list(EMOTIONS)

    @property
    def size(self) -> int:
        """현재 버퍼 크기"""
        with self._lock:
            return len(self._buffer)

    @property
    def duration_sec(self) -> float:
        """설정된 버퍼 유지 시간"""
        return self._buffer_duration

    # ================================================================
    # 데이터 추가
    # ================================================================

    def add(
        self,
        emotion_label: str,
        scores: Dict[str, float],
        confidence: float,
        face_detected: bool = True,
        frame_quality: float = 1.0,
        timestamp: Optional[float] = None,
    ):
        """
        분석 결과를 버퍼에 추가합니다.

        Args:
            emotion_label: dominant 감정 라벨
            scores: 감정별 스코어 딕셔너리
            confidence: 분석 confidence
            face_detected: 얼굴 감지 여부
            frame_quality: 프레임 품질 (0~1)
            timestamp: 타임스탬프 (None이면 현재 시간)
        """
        entry = BufferEntry(
            timestamp=timestamp or time.time(),
            emotion_label=emotion_label,
            scores=dict(scores),
            confidence=confidence,
            face_detected=face_detected,
            frame_quality=frame_quality,
        )

        with self._lock:
            self._buffer.append(entry)
            self._evict_expired()

    def add_no_face(self, timestamp: Optional[float] = None):
        """
        얼굴 미감지 엔트리 추가 (missing data marker).
        """
        empty_scores = {e: 0.0 for e in self._emotion_keys}
        entry = BufferEntry(
            timestamp=timestamp or time.time(),
            emotion_label="none",
            scores=empty_scores,
            confidence=0.0,
            face_detected=False,
            frame_quality=0.0,
        )

        with self._lock:
            self._buffer.append(entry)
            self._evict_expired()

    # ================================================================
    # 품질 계산
    # ================================================================

    def get_quality(self) -> SequenceQuality:
        """현재 버퍼의 시퀀스 품질을 계산합니다."""
        with self._lock:
            return self._compute_quality()

    def _compute_quality(self) -> SequenceQuality:
        """품질 계산 (lock 보유 상태에서 호출)"""
        if not self._buffer:
            return SequenceQuality()

        total = len(self._buffer)
        face_detected_count = sum(1 for e in self._buffer if e.face_detected)
        confidences = [e.confidence for e in self._buffer if e.face_detected]

        valid_face_ratio = face_detected_count / total if total > 0 else 0.0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        missing_ratio = 1.0 - valid_face_ratio

        time_span = 0.0
        if total >= 2:
            time_span = self._buffer[-1].timestamp - self._buffer[0].timestamp

        return SequenceQuality(
            valid_face_ratio=valid_face_ratio,
            avg_confidence=avg_confidence,
            missing_ratio=missing_ratio,
            total_entries=total,
            time_span_sec=time_span,
        )

    # ================================================================
    # LSTM 시퀀스 생성
    # ================================================================

    def get_lstm_sequence(self) -> Optional[LSTMSequence]:
        """
        LSTM 입력용 fixed-length sequence를 생성합니다.
        - 버퍼 내 데이터를 시간 기준으로 균등 리샘플링
        - confidence에 따른 가중치 반영
        - 품질이 부족하면 None 반환

        Returns:
            LSTMSequence 또는 None (데이터 부족 시)
        """
        with self._lock:
            quality = self._compute_quality()

            if not quality.is_sufficient:
                return None

            # face_detected인 엔트리만 필터링
            valid_entries = [e for e in self._buffer if e.face_detected]
            if len(valid_entries) < 3:
                return None

            # 시간 기준 균등 리샘플링
            data, weights = self._resample_to_fixed_length(valid_entries)

            return LSTMSequence(
                data=data,
                weights=weights,
                quality=quality,
            )

    def get_lstm_sequence_raw(self) -> Optional[LSTMSequence]:
        """
        리샘플링 없이 최근 N개 엔트리로 시퀀스 생성 (간단한 버전).
        sequence_length 만큼의 최근 유효 결과를 사용합니다.

        Returns:
            LSTMSequence 또는 None
        """
        with self._lock:
            quality = self._compute_quality()

            valid_entries = [e for e in self._buffer if e.face_detected]
            if len(valid_entries) < self._sequence_length:
                # 부족하면 있는 만큼 패딩
                if len(valid_entries) < 3:
                    return None
                entries = valid_entries
            else:
                # 최근 sequence_length 개
                entries = valid_entries[-self._sequence_length:]

            data = np.zeros((self._sequence_length, self._n_features), dtype=np.float32)
            weights = np.zeros(self._sequence_length, dtype=np.float32)

            for i, entry in enumerate(entries):
                if i >= self._sequence_length:
                    break
                # 스코어를 feature 벡터로 변환
                data[i] = self._entry_to_features(entry)
                # confidence 기반 가중치
                weights[i] = self._compute_entry_weight(entry)

            # 데이터 부족 시 마지막 유효 값으로 패딩
            if len(entries) < self._sequence_length:
                last_valid_idx = len(entries) - 1
                for i in range(len(entries), self._sequence_length):
                    data[i] = data[last_valid_idx]
                    weights[i] = weights[last_valid_idx] * 0.5  # 패딩 데이터는 낮은 가중치

            return LSTMSequence(
                data=data,
                weights=weights,
                quality=quality,
            )

    # ================================================================
    # 유틸리티
    # ================================================================

    def clear(self):
        """버퍼 초기화"""
        with self._lock:
            self._buffer.clear()

    def set_duration(self, duration_sec: float):
        """버퍼 유지 시간 변경"""
        self._buffer_duration = max(
            self._min_duration,
            min(self._max_duration, duration_sec),
        )
        with self._lock:
            self._evict_expired()

    def get_recent_entries(self, count: int = 10) -> List[BufferEntry]:
        """최근 N개 엔트리 조회"""
        with self._lock:
            entries = list(self._buffer)
            return entries[-count:] if len(entries) > count else entries

    def get_stats(self) -> Dict:
        """버퍼 통계 정보"""
        with self._lock:
            quality = self._compute_quality()
            return {
                "buffer_size": len(self._buffer),
                "buffer_duration_sec": self._buffer_duration,
                "time_span_sec": quality.time_span_sec,
                "valid_face_ratio": quality.valid_face_ratio,
                "avg_confidence": quality.avg_confidence,
                "missing_ratio": quality.missing_ratio,
                "quality_score": quality.quality_score,
                "is_sufficient": quality.is_sufficient,
            }

    # ================================================================
    # 내부 헬퍼
    # ================================================================

    def _evict_expired(self):
        """만료된 엔트리 제거 (lock 보유 상태에서 호출)"""
        if not self._buffer:
            return

        cutoff = time.time() - self._buffer_duration
        while self._buffer and self._buffer[0].timestamp < cutoff:
            self._buffer.popleft()

    def _entry_to_features(self, entry: BufferEntry) -> np.ndarray:
        """BufferEntry를 feature 벡터(np.array)로 변환"""
        features = np.zeros(self._n_features, dtype=np.float32)
        for i, emotion in enumerate(self._emotion_keys):
            if i < self._n_features:
                features[i] = entry.scores.get(emotion, 0.0)
        return features

    def _compute_entry_weight(self, entry: BufferEntry) -> float:
        """
        엔트리의 가중치 계산.
        - confidence >= threshold: weight = confidence * frame_quality
        - confidence < threshold: weight = low_confidence_weight * frame_quality
        """
        if not entry.face_detected:
            return 0.0

        if entry.confidence >= self._confidence_threshold:
            base_weight = entry.confidence
        else:
            base_weight = self._low_confidence_weight

        return base_weight * entry.frame_quality

    def _resample_to_fixed_length(
        self,
        entries: List[BufferEntry],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        유효 엔트리를 시간 기준으로 균등 리샘플링하여
        (sequence_length, n_features) 배열과 weights 배열을 생성합니다.

        시간 축을 sequence_length 등분하고, 각 구간에 해당하는
        엔트리들의 가중 평균을 사용합니다.
        """
        data = np.zeros((self._sequence_length, self._n_features), dtype=np.float32)
        weights = np.zeros(self._sequence_length, dtype=np.float32)

        if not entries:
            return data, weights

        # 시간 범위
        t_start = entries[0].timestamp
        t_end = entries[-1].timestamp
        t_span = t_end - t_start

        if t_span <= 0:
            # 모든 엔트리가 같은 시간 - 마지막 값으로 채움
            features = self._entry_to_features(entries[-1])
            w = self._compute_entry_weight(entries[-1])
            for i in range(self._sequence_length):
                data[i] = features
                weights[i] = w
            return data, weights

        # 각 time step의 경계 계산
        step_duration = t_span / self._sequence_length

        entry_idx = 0
        for step in range(self._sequence_length):
            step_start = t_start + step * step_duration
            step_end = step_start + step_duration

            # 이 구간에 해당하는 엔트리 수집
            step_features = []
            step_weights = []

            while entry_idx < len(entries) and entries[entry_idx].timestamp < step_end:
                if entries[entry_idx].timestamp >= step_start:
                    feat = self._entry_to_features(entries[entry_idx])
                    w = self._compute_entry_weight(entries[entry_idx])
                    step_features.append(feat)
                    step_weights.append(w)
                entry_idx += 1

            if step_features:
                # 가중 평균
                total_w = sum(step_weights)
                if total_w > 0:
                    weighted_sum = np.zeros(self._n_features, dtype=np.float32)
                    for feat, w in zip(step_features, step_weights):
                        weighted_sum += feat * w
                    data[step] = weighted_sum / total_w
                    weights[step] = total_w / len(step_weights)  # 평균 가중치
                else:
                    data[step] = np.mean(step_features, axis=0)
                    weights[step] = self._low_confidence_weight
            else:
                # 구간에 데이터 없음 - 이전 step 값 유지 (보간)
                if step > 0:
                    data[step] = data[step - 1]
                    weights[step] = weights[step - 1] * 0.5  # 보간 데이터는 낮은 가중치
                # else: 첫 step이면 0으로 유지

        # entry_idx를 되감기 (구간 경계에서 놓친 엔트리 처리)
        # deque 특성상 순서 보장되므로 추가 처리 불필요

        return data, weights
