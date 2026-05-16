"""
modules/vad_state_machine.py - Voice Activity Detection State Machine
Determines when a person is speaking based on audio chunk metrics.

State Machine:
    IDLE → POSSIBLE_SPEECH → SPEECH_ACTIVE → POSSIBLE_END → SPEECH_ENDED
      ↑         ↓                                    ↓            ↓
      └── SILENCE/NOISE_ONLY ←───────────────────────┘            └→ IDLE

States:
- IDLE: No speech detected, learning noise floor
- POSSIBLE_SPEECH: RMS exceeded threshold, waiting for confirmation
- SPEECH_ACTIVE: Confirmed speech, accumulating audio
- POSSIBLE_END: Brief silence during speech, might resume
- SPEECH_ENDED: Speech finished, segment ready for STT (transient)
- SILENCE: Extended silence after possible speech (resets to IDLE)
- NOISE_ONLY: Audio above threshold but not speech pattern

Adaptive Noise Floor:
- Learns ambient noise level during IDLE/SILENCE
- speech_threshold = noise_floor * factor + margin
- Adjusts automatically to environment changes

Design:
- Receives one audio chunk at a time via process_chunk()
- Returns current state after each chunk
- Stateless regarding audio storage (that's SpeechSegmentBuffer's job)
- All timing based on chunk count × chunk_duration_ms
"""

import sys
import os
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class VADState(str, Enum):
    """VAD state machine states."""
    IDLE = "IDLE"
    POSSIBLE_SPEECH = "POSSIBLE_SPEECH"
    SPEECH_ACTIVE = "SPEECH_ACTIVE"
    POSSIBLE_END = "POSSIBLE_END"
    SPEECH_ENDED = "SPEECH_ENDED"
    SILENCE = "SILENCE"
    NOISE_ONLY = "NOISE_ONLY"


@dataclass
class VADStatus:
    """Current VAD state for external observation (UI, controller)."""
    state: str = "IDLE"
    noise_floor: float = 0.01
    speech_threshold: float = 0.03
    current_rms: float = 0.0
    current_peak: float = 0.0
    segment_duration_ms: float = 0.0
    silence_duration_ms: float = 0.0
    speech_chunks: int = 0
    silence_chunks: int = 0
    total_chunks_processed: int = 0


@dataclass
class VADConfig:
    """Configuration for the VAD state machine."""
    # Chunk timing
    chunk_duration_ms: int = 100

    # Adaptive noise floor
    noise_floor_init: float = 0.01
    noise_floor_factor: float = 3.0        # threshold = noise_floor * factor
    noise_floor_margin: float = 0.005      # absolute margin added to threshold
    noise_floor_window_chunks: int = 20    # ~2s of noise floor learning
    noise_floor_min: float = 0.003         # minimum noise floor
    noise_floor_max: float = 0.05          # maximum noise floor (very noisy env)
    noise_floor_decay: float = 0.995       # slow decay toward current level

    # State transition thresholds (in chunks)
    min_speech_chunks: int = 7             # 700ms before confirming speech
    min_valid_segment_chunks: int = 10     # 1000ms minimum valid segment
    end_silence_chunks: int = 8            # 800ms silence to end speech
    possible_speech_timeout_chunks: int = 3  # 300ms to confirm or reject
    max_segment_chunks: int = 100          # 10000ms max segment

    # Energy thresholds
    peak_factor: float = 2.0              # peak must be > noise_floor * peak_factor


class VADStateMachine:
    """
    Voice Activity Detection state machine.

    Processes audio chunks one at a time and transitions between states
    based on energy levels relative to an adaptive noise floor.

    Args:
        config: VADConfig with timing and threshold parameters.
    """

    def __init__(self, config: Optional[VADConfig] = None):
        self._config = config or VADConfig()

        # State
        self._state = VADState.IDLE
        self._prev_state = VADState.IDLE

        # Noise floor estimation
        self._noise_floor = self._config.noise_floor_init
        self._noise_samples: deque = deque(maxlen=self._config.noise_floor_window_chunks)

        # Counters (reset on state transitions)
        self._speech_chunks = 0          # chunks in current speech
        self._silence_chunks = 0         # consecutive silence chunks
        self._possible_speech_chunks = 0 # chunks in POSSIBLE_SPEECH
        self._total_chunks = 0

        # Current chunk metrics
        self._current_rms = 0.0
        self._current_peak = 0.0

    @property
    def state(self) -> VADState:
        """Current VAD state."""
        return self._state

    @property
    def noise_floor(self) -> float:
        """Current adaptive noise floor."""
        return self._noise_floor

    @property
    def speech_threshold(self) -> float:
        """Current speech detection threshold."""
        return self._noise_floor * self._config.noise_floor_factor + self._config.noise_floor_margin

    def get_status(self) -> VADStatus:
        """Get full VAD status for UI display."""
        return VADStatus(
            state=self._state.value,
            noise_floor=self._noise_floor,
            speech_threshold=self.speech_threshold,
            current_rms=self._current_rms,
            current_peak=self._current_peak,
            segment_duration_ms=self._speech_chunks * self._config.chunk_duration_ms,
            silence_duration_ms=self._silence_chunks * self._config.chunk_duration_ms,
            speech_chunks=self._speech_chunks,
            silence_chunks=self._silence_chunks,
            total_chunks_processed=self._total_chunks,
        )

    def process_chunk(self, chunk: np.ndarray) -> VADState:
        """
        Process one audio chunk and return the new state.

        This is the main entry point. Call this for every audio chunk
        from AudioStreamWorker.

        Args:
            chunk: 1D float32 numpy array of audio samples.

        Returns:
            Current VADState after processing.
        """
        self._total_chunks += 1

        # Calculate chunk metrics
        if len(chunk) == 0:
            return self._state

        rms = float(np.sqrt(np.mean(chunk ** 2)))
        peak = float(np.max(np.abs(chunk)))
        self._current_rms = rms
        self._current_peak = peak

        # Determine if this chunk looks like speech
        is_speech = self._is_speech_chunk(rms, peak)

        # Save previous state for transition detection
        self._prev_state = self._state

        # State machine transitions
        if self._state == VADState.IDLE:
            self._handle_idle(rms, is_speech)

        elif self._state == VADState.POSSIBLE_SPEECH:
            self._handle_possible_speech(rms, is_speech)

        elif self._state == VADState.SPEECH_ACTIVE:
            self._handle_speech_active(rms, is_speech)

        elif self._state == VADState.POSSIBLE_END:
            self._handle_possible_end(rms, is_speech)

        elif self._state == VADState.SPEECH_ENDED:
            # Transient state - immediately go to IDLE
            self._transition_to(VADState.IDLE)
            self._speech_chunks = 0
            self._silence_chunks = 0

        elif self._state == VADState.SILENCE:
            self._handle_idle(rms, is_speech)  # Same as IDLE

        elif self._state == VADState.NOISE_ONLY:
            self._handle_idle(rms, is_speech)  # Same as IDLE

        # Log state changes
        if self._state != self._prev_state:
            self._log_transition()

        return self._state

    def reset(self) -> None:
        """Reset the state machine to initial state."""
        self._state = VADState.IDLE
        self._speech_chunks = 0
        self._silence_chunks = 0
        self._possible_speech_chunks = 0
        self._noise_samples.clear()
        self._noise_floor = self._config.noise_floor_init

    # ================================================================
    # State handlers
    # ================================================================

    def _handle_idle(self, rms: float, is_speech: bool) -> None:
        """Handle IDLE state: learn noise floor, detect speech onset."""
        if is_speech:
            self._possible_speech_chunks = 1
            self._transition_to(VADState.POSSIBLE_SPEECH)
        else:
            # Learn noise floor during silence
            self._update_noise_floor(rms)
            self._silence_chunks += 1

    def _handle_possible_speech(self, rms: float, is_speech: bool) -> None:
        """Handle POSSIBLE_SPEECH: confirm or reject speech onset."""
        if is_speech:
            self._possible_speech_chunks += 1
            # Enough consecutive speech chunks to confirm?
            if self._possible_speech_chunks >= self._config.possible_speech_timeout_chunks:
                self._speech_chunks = self._possible_speech_chunks
                self._silence_chunks = 0
                self._transition_to(VADState.SPEECH_ACTIVE)
        else:
            # False trigger - back to idle
            self._possible_speech_chunks = 0
            self._update_noise_floor(rms)
            self._transition_to(VADState.NOISE_ONLY if self._current_peak > self._noise_floor else VADState.SILENCE)

    def _handle_speech_active(self, rms: float, is_speech: bool) -> None:
        """Handle SPEECH_ACTIVE: accumulate speech, detect pauses."""
        self._speech_chunks += 1

        if is_speech:
            self._silence_chunks = 0
        else:
            self._silence_chunks += 1
            # Brief silence - might be a pause
            if self._silence_chunks >= self._config.end_silence_chunks:
                self._transition_to(VADState.POSSIBLE_END)
                return

        # Max segment length check
        if self._speech_chunks >= self._config.max_segment_chunks:
            self._transition_to(VADState.SPEECH_ENDED)

    def _handle_possible_end(self, rms: float, is_speech: bool) -> None:
        """Handle POSSIBLE_END: speech resumes or segment ends."""
        if is_speech:
            # Speech resumed - back to active
            self._silence_chunks = 0
            self._speech_chunks += 1
            self._transition_to(VADState.SPEECH_ACTIVE)
        else:
            self._silence_chunks += 1
            self._speech_chunks += 1

            # Confirm end: enough silence
            # Check if the segment is long enough to be valid
            total_duration_chunks = self._speech_chunks
            if total_duration_chunks >= self._config.min_valid_segment_chunks:
                self._transition_to(VADState.SPEECH_ENDED)
            elif total_duration_chunks >= self._config.min_speech_chunks:
                # Borderline - still end it
                self._transition_to(VADState.SPEECH_ENDED)
            else:
                # Too short - discard
                self._speech_chunks = 0
                self._silence_chunks = 0
                self._transition_to(VADState.SILENCE)

    # ================================================================
    # Helpers
    # ================================================================

    def _is_speech_chunk(self, rms: float, peak: float) -> bool:
        """Determine if a chunk contains speech based on adaptive threshold."""
        threshold = self.speech_threshold
        peak_threshold = self._noise_floor * self._config.peak_factor

        # Both RMS and peak must exceed their thresholds
        return rms > threshold and peak > peak_threshold

    def _update_noise_floor(self, rms: float) -> None:
        """Update adaptive noise floor during silence."""
        # Only update with quiet samples
        if rms < self._noise_floor * 3.0:
            self._noise_samples.append(rms)

        if len(self._noise_samples) >= 3:
            # Use median to be robust against outliers
            estimated = float(np.median(list(self._noise_samples)))
            # Clamp to reasonable range
            estimated = max(self._config.noise_floor_min, min(estimated, self._config.noise_floor_max))
            # Smooth update
            self._noise_floor = self._noise_floor * self._config.noise_floor_decay + estimated * (1.0 - self._config.noise_floor_decay)

    def _transition_to(self, new_state: VADState) -> None:
        """Transition to a new state."""
        self._state = new_state

    def _log_transition(self) -> None:
        """Log state transitions."""
        if self._state == VADState.IDLE:
            logger.debug("[VAD] state=IDLE noise_floor=%.4f", self._noise_floor)
        elif self._state == VADState.POSSIBLE_SPEECH:
            logger.debug("[VAD] state=POSSIBLE_SPEECH rms=%.4f threshold=%.4f",
                        self._current_rms, self.speech_threshold)
        elif self._state == VADState.SPEECH_ACTIVE:
            logger.info("[VAD] state=SPEECH_ACTIVE segment_ms=%d",
                       self._speech_chunks * self._config.chunk_duration_ms)
        elif self._state == VADState.POSSIBLE_END:
            logger.debug("[VAD] state=POSSIBLE_END silence_ms=%d",
                        self._silence_chunks * self._config.chunk_duration_ms)
        elif self._state == VADState.SPEECH_ENDED:
            duration_ms = self._speech_chunks * self._config.chunk_duration_ms
            logger.info("[VAD] state=SPEECH_ENDED duration_ms=%d", duration_ms)
        elif self._state == VADState.SILENCE:
            logger.debug("[VAD] state=SILENCE")
        elif self._state == VADState.NOISE_ONLY:
            logger.debug("[VAD] state=NOISE_ONLY rms=%.4f", self._current_rms)
