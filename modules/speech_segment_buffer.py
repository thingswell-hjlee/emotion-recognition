"""
modules/speech_segment_buffer.py - Speech Segment Buffer
Accumulates audio during detected speech and produces completed segments
with metadata for STT processing.

Design:
- Receives audio chunks from AudioStreamWorker during SPEECH_ACTIVE
- Includes pre-roll audio (500ms before speech onset)
- Tracks segment metadata: duration, RMS, peak, voice ratio, quality
- Rejects segments that are too short (< min_valid_segment_ms)
- Caps segments at max length (max_segment_ms)
- Thread-safe for concurrent read/write

Usage:
    buffer = SpeechSegmentBuffer(sample_rate=16000)
    buffer.start_segment(pre_roll_audio)
    buffer.append(chunk)
    segment = buffer.end_segment()
    if segment and segment.is_valid:
        queue.put(segment)
"""

import sys
import os
import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class SegmentMetadata:
    """Metadata for a completed speech segment."""
    segment_id: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: float = 0.0
    sample_rate: int = 16000
    rms_avg: float = 0.0
    peak_max: float = 0.0
    voice_ratio: float = 0.0
    noise_floor: float = 0.0
    quality_score: float = 0.0
    reason_code: str = ""  # OK / TOO_SHORT / TOO_LONG / LOW_ENERGY / NOISE_ONLY


@dataclass
class SpeechSegment:
    """A completed speech segment ready for STT processing."""
    audio: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float32))
    metadata: SegmentMetadata = field(default_factory=SegmentMetadata)

    @property
    def is_valid(self) -> bool:
        """Whether this segment should be sent to STT."""
        return self.metadata.reason_code == "OK"

    @property
    def duration_sec(self) -> float:
        return self.metadata.duration_ms / 1000.0


class SpeechSegmentBuffer:
    """
    Accumulates audio chunks during a speech segment and produces
    a finalized SpeechSegment with metadata when speech ends.

    Thread-safe: can be written to from audio callback thread
    and read from main/STT thread.

    Args:
        sample_rate: Audio sample rate (Hz).
        min_valid_segment_ms: Minimum duration to accept a segment.
        max_segment_ms: Maximum duration before forced cut.
        min_rms_threshold: Minimum average RMS for a valid segment.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        min_valid_segment_ms: float = 1000.0,
        max_segment_ms: float = 10000.0,
        min_rms_threshold: float = 0.005,
    ):
        self._sample_rate = sample_rate
        self._min_valid_ms = min_valid_segment_ms
        self._max_segment_ms = max_segment_ms
        self._min_rms = min_rms_threshold

        # Active segment state
        self._lock = threading.Lock()
        self._chunks: List[np.ndarray] = []
        self._is_recording = False
        self._segment_start: float = 0.0
        self._total_samples: int = 0
        self._rms_sum: float = 0.0
        self._rms_count: int = 0
        self._peak_max: float = 0.0
        self._voice_chunk_count: int = 0
        self._total_chunk_count: int = 0
        self._noise_floor: float = 0.01

    @property
    def is_recording(self) -> bool:
        """Whether the buffer is currently accumulating speech."""
        with self._lock:
            return self._is_recording

    @property
    def current_duration_ms(self) -> float:
        """Current segment duration in milliseconds."""
        with self._lock:
            return (self._total_samples / self._sample_rate) * 1000.0

    @property
    def is_max_exceeded(self) -> bool:
        """Whether the current segment has exceeded max length."""
        return self.current_duration_ms >= self._max_segment_ms

    def start_segment(
        self,
        pre_roll_audio: Optional[np.ndarray] = None,
        noise_floor: float = 0.01,
    ) -> None:
        """
        Begin recording a new speech segment.

        Args:
            pre_roll_audio: Audio from before speech onset (pre-roll buffer).
            noise_floor: Current adaptive noise floor value.
        """
        with self._lock:
            self._chunks = []
            self._is_recording = True
            self._segment_start = time.time()
            self._total_samples = 0
            self._rms_sum = 0.0
            self._rms_count = 0
            self._peak_max = 0.0
            self._voice_chunk_count = 0
            self._total_chunk_count = 0
            self._noise_floor = noise_floor

            # Include pre-roll if provided
            if pre_roll_audio is not None and len(pre_roll_audio) > 0:
                self._chunks.append(pre_roll_audio.astype(np.float32))
                self._total_samples += len(pre_roll_audio)

    def append(self, chunk: np.ndarray, is_voice: bool = True) -> None:
        """
        Append an audio chunk to the current segment.

        Args:
            chunk: Audio samples (float32, mono).
            is_voice: Whether this chunk was classified as voice by VAD.
        """
        with self._lock:
            if not self._is_recording:
                return

            chunk_f32 = chunk.astype(np.float32) if chunk.dtype != np.float32 else chunk
            self._chunks.append(chunk_f32)
            self._total_samples += len(chunk_f32)

            # Track metrics
            rms = float(np.sqrt(np.mean(chunk_f32 ** 2)))
            peak = float(np.max(np.abs(chunk_f32)))
            self._rms_sum += rms
            self._rms_count += 1
            self._peak_max = max(self._peak_max, peak)
            self._total_chunk_count += 1
            if is_voice:
                self._voice_chunk_count += 1

    def end_segment(self) -> Optional[SpeechSegment]:
        """
        Finalize the current segment and return it with metadata.

        Returns:
            SpeechSegment with audio and metadata, or None if not recording.
            The segment includes a reason_code indicating validity.
        """
        with self._lock:
            if not self._is_recording:
                return None

            self._is_recording = False
            ended_at = time.time()

            # No data case
            if not self._chunks or self._total_samples == 0:
                return None

            # Concatenate all chunks
            audio = np.concatenate(self._chunks)
            duration_ms = (len(audio) / self._sample_rate) * 1000.0

            # Calculate metrics
            rms_avg = self._rms_sum / max(self._rms_count, 1)
            voice_ratio = self._voice_chunk_count / max(self._total_chunk_count, 1)

            # Quality score: weighted combination
            # Higher is better. Range 0.0 - 1.0
            energy_score = min(1.0, rms_avg / max(self._noise_floor * 5, 0.01))
            duration_score = min(1.0, duration_ms / 3000.0)  # 3s = perfect
            voice_score = voice_ratio
            quality_score = (energy_score * 0.3 + duration_score * 0.3 + voice_score * 0.4)

            # Determine reason code
            reason_code = "OK"
            if duration_ms < self._min_valid_ms:
                reason_code = "TOO_SHORT"
            elif duration_ms > self._max_segment_ms:
                reason_code = "TOO_LONG"
            elif rms_avg < self._min_rms:
                reason_code = "LOW_ENERGY"
            elif voice_ratio < 0.2:
                reason_code = "NOISE_ONLY"

            metadata = SegmentMetadata(
                segment_id=str(uuid.uuid4())[:8],
                started_at=self._segment_start,
                ended_at=ended_at,
                duration_ms=duration_ms,
                sample_rate=self._sample_rate,
                rms_avg=rms_avg,
                peak_max=self._peak_max,
                voice_ratio=voice_ratio,
                noise_floor=self._noise_floor,
                quality_score=quality_score,
                reason_code=reason_code,
            )

            # Clear state
            self._chunks = []
            self._total_samples = 0

            return SpeechSegment(audio=audio, metadata=metadata)

    def cancel_segment(self) -> None:
        """Discard the current segment without producing output."""
        with self._lock:
            self._is_recording = False
            self._chunks = []
            self._total_samples = 0

    def reset(self) -> None:
        """Full reset of the buffer state."""
        with self._lock:
            self._is_recording = False
            self._chunks = []
            self._total_samples = 0
            self._rms_sum = 0.0
            self._rms_count = 0
            self._peak_max = 0.0
            self._voice_chunk_count = 0
            self._total_chunk_count = 0
