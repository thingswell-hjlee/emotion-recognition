"""
modules/voice_stt_pipeline.py - Reliable Voice STT Pipeline Orchestrator
Ties together AudioStreamWorker, VADStateMachine, SpeechSegmentBuffer, and STTWorker
into a single cohesive pipeline that runs independently in a background thread.

Architecture:
    AudioStreamWorker (background) → chunks → VAD monitor thread → SpeechSegmentBuffer → STTWorker (background)

This module:
- Runs a monitor thread that polls AudioStreamWorker for new chunks
- Feeds chunks to VADStateMachine
- On SPEECH_ACTIVE: starts SpeechSegmentBuffer with pre-roll
- On SPEECH_ENDED: finalizes segment and submits to STTWorker
- Provides get_status() for UI polling (all pipeline state in one call)
- Only active in voice/full/debug modes
- Never opens audio in minimal/face modes
- Never crashes the app
"""

import sys
import os
import time
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.audio_stream import AudioStreamWorker, AudioStreamStatus, AUDIO_RUNNING
from modules.vad_state_machine import VADStateMachine, VADState, VADConfig, VADStatus
from modules.speech_segment_buffer import SpeechSegmentBuffer, SpeechSegment
from modules.stt_worker import STTWorker, STTWorkerStatus, STTResult

logger = logging.getLogger(__name__)


@dataclass
class VoicePipelineStatus:
    """Combined status of the entire voice STT pipeline for UI display."""
    # Overall
    is_running: bool = False
    mode: str = "OFF"  # OFF / MONITORING / ACTIVE

    # Audio stream
    audio_status: str = "AUDIO_STOPPED"
    device_name: str = ""
    sample_rate: int = 16000
    rms: float = 0.0
    peak: float = 0.0
    dbfs: float = -96.0

    # VAD
    vad_state: str = "IDLE"
    noise_floor: float = 0.01
    speech_threshold: float = 0.03
    segment_duration_ms: float = 0.0

    # STT Worker
    stt_status: str = "STT_DISABLED"
    stt_model_loaded: bool = False
    stt_model_name: str = ""
    stt_queue_size: int = 0
    stt_total_processed: int = 0

    # Last result
    last_text: str = ""
    last_confidence: Optional[float] = None
    last_latency_ms: float = 0.0
    last_timestamp: Optional[datetime] = None
    last_error: str = ""


class VoiceSTTPipeline:
    """
    Orchestrates the full voice → STT pipeline.

    Components:
    1. AudioStreamWorker: background audio capture
    2. VADStateMachine: detects speech/silence boundaries
    3. SpeechSegmentBuffer: accumulates speech with pre-roll
    4. STTWorker: background transcription

    The pipeline runs a lightweight monitor thread (~10ms polling)
    that reads chunks from AudioStreamWorker and drives the VAD.

    Args:
        sample_rate: Audio sample rate. Default 16000.
        chunk_duration_ms: Chunk size in ms. Default 100.
        stt_model_size: Whisper model size. Default "tiny".
        stt_enabled: Whether STT is enabled. Default True.
        pre_roll_ms: Pre-roll buffer size. Default 500.
        device_id: Audio device ID. Default None (system default).
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration_ms: int = 100,
        stt_model_size: str = "tiny",
        stt_enabled: bool = True,
        pre_roll_ms: int = 500,
        device_id: Optional[int] = None,
        min_valid_segment_ms: float = 1000.0,
        max_segment_ms: float = 10000.0,
        end_silence_ms: float = 800.0,
    ):
        self._sample_rate = sample_rate
        self._chunk_ms = chunk_duration_ms
        self._chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        self._pre_roll_ms = pre_roll_ms
        self._device_id = device_id
        self._stt_enabled = stt_enabled

        # Build VAD config from parameters
        vad_config = VADConfig(
            chunk_duration_ms=chunk_duration_ms,
            end_silence_chunks=int(end_silence_ms / chunk_duration_ms),
            min_valid_segment_chunks=int(min_valid_segment_ms / chunk_duration_ms),
            max_segment_chunks=int(max_segment_ms / chunk_duration_ms),
        )

        # Create components
        self._audio = AudioStreamWorker(
            sample_rate=sample_rate,
            chunk_duration_ms=chunk_duration_ms,
            buffer_duration_s=30.0,
        )
        self._vad = VADStateMachine(config=vad_config)
        self._segment_buffer = SpeechSegmentBuffer(
            sample_rate=sample_rate,
            min_valid_segment_ms=min_valid_segment_ms,
            max_segment_ms=max_segment_ms,
        )
        self._stt_worker = STTWorker(
            model_size=stt_model_size,
            language="ko",
            device="cpu",
            compute_type="int8",
            queue_max_size=3,
            enabled=stt_enabled,
        )

        # Monitor thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()

        # Track last chunk position for polling
        self._last_read_pos = 0

    def start(self) -> bool:
        """
        Start the full pipeline: audio stream + VAD monitor + STT worker.

        Returns:
            True if started successfully.
        """
        if self._running:
            return True

        logger.info("[AUDIO] stream_started sample_rate=%d chunk_ms=%d",
                   self._sample_rate, self._chunk_ms)

        # Start audio stream
        self._audio.start(device_id=self._device_id)

        # Wait briefly for audio to start
        time.sleep(0.2)
        audio_status = self._audio.get_status()
        if audio_status.status != AUDIO_RUNNING:
            logger.error("[AUDIO] Failed to start: %s", audio_status.error_message)
            # Don't fail completely - STT just won't work
            # Return True so the app continues

        # Start STT worker
        if self._stt_enabled:
            self._stt_worker.start()

        # Start monitor thread
        self._running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="VoicePipeline-Monitor",
            daemon=True,
        )
        self._monitor_thread.start()

        logger.info("[PIPELINE] Voice STT pipeline started.")
        return True

    def stop(self) -> None:
        """Stop the full pipeline."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        # Stop monitor thread
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)

        # Stop components
        self._stt_worker.stop()
        self._audio.stop()

        # Reset VAD
        self._vad.reset()
        self._segment_buffer.reset()

        logger.info("[PIPELINE] Voice STT pipeline stopped.")

    def get_status(self) -> VoicePipelineStatus:
        """Get combined pipeline status for UI."""
        audio_st = self._audio.get_status()
        vad_st = self._vad.get_status()
        stt_st = self._stt_worker.get_status()

        # Determine mode
        if not self._running:
            mode = "OFF"
        elif self._vad.state in (VADState.SPEECH_ACTIVE, VADState.POSSIBLE_END):
            mode = "ACTIVE"
        else:
            mode = "MONITORING"

        return VoicePipelineStatus(
            is_running=self._running,
            mode=mode,
            # Audio
            audio_status=audio_st.status,
            device_name=str(audio_st.device_id) if audio_st.device_id is not None else "default",
            sample_rate=audio_st.sample_rate,
            rms=audio_st.rms,
            peak=audio_st.peak,
            dbfs=audio_st.dbfs,
            # VAD
            vad_state=vad_st.state,
            noise_floor=vad_st.noise_floor,
            speech_threshold=vad_st.speech_threshold,
            segment_duration_ms=vad_st.segment_duration_ms if self._segment_buffer.is_recording else 0.0,
            # STT
            stt_status=stt_st.status,
            stt_model_loaded=stt_st.model_loaded,
            stt_model_name=stt_st.model_name,
            stt_queue_size=stt_st.queue_size,
            stt_total_processed=stt_st.total_processed,
            # Results
            last_text=stt_st.last_text,
            last_confidence=stt_st.last_confidence,
            last_latency_ms=stt_st.last_latency_ms,
            last_timestamp=stt_st.last_timestamp,
            last_error=stt_st.error_message,
        )

    def get_stt_results(self, count: int = 5) -> List[STTResult]:
        """Get recent STT results."""
        return self._stt_worker.get_results(count)

    # ================================================================
    # Monitor loop
    # ================================================================

    def _monitor_loop(self) -> None:
        """
        Monitor thread: polls audio stream, feeds VAD, manages segments.

        Runs at ~chunk_duration_ms intervals (100ms by default).
        """
        poll_interval = self._chunk_ms / 1000.0  # Convert ms to seconds

        while not self._stop_event.is_set():
            try:
                self._process_one_cycle()
            except Exception as e:
                logger.error("[PIPELINE] Monitor error: %s", e)

            # Sleep for one chunk duration
            time.sleep(poll_interval)

    def _process_one_cycle(self) -> None:
        """Process one monitoring cycle: read audio, run VAD, manage segment."""
        # Get latest audio metrics from the stream
        audio_status = self._audio.get_status()

        if audio_status.status != AUDIO_RUNNING:
            return

        # Get the most recent chunk-sized audio from ring buffer
        chunk = self._audio.get_pre_roll(ms=self._chunk_ms)
        if len(chunk) < self._chunk_samples * 0.5:
            return  # Not enough data yet

        # Feed to VAD
        prev_state = self._vad.state
        new_state = self._vad.process_chunk(chunk)

        # State transition handling
        self._handle_vad_transition(prev_state, new_state, chunk)

    def _handle_vad_transition(self, prev: VADState, curr: VADState, chunk: np.ndarray) -> None:
        """Handle VAD state transitions to manage segment recording."""

        # Transition to SPEECH_ACTIVE: start recording
        if curr == VADState.SPEECH_ACTIVE and prev != VADState.SPEECH_ACTIVE:
            if not self._segment_buffer.is_recording:
                # Get pre-roll from audio ring buffer
                pre_roll = self._audio.get_pre_roll(ms=self._pre_roll_ms)
                self._segment_buffer.start_segment(
                    pre_roll_audio=pre_roll,
                    noise_floor=self._vad.noise_floor,
                )
                logger.info("[VAD] Recording started with %dms pre-roll", self._pre_roll_ms)

        # While in speech states: append audio
        if curr in (VADState.SPEECH_ACTIVE, VADState.POSSIBLE_END, VADState.POSSIBLE_SPEECH):
            if self._segment_buffer.is_recording:
                is_voice = curr == VADState.SPEECH_ACTIVE
                self._segment_buffer.append(chunk, is_voice=is_voice)

                # Check max length
                if self._segment_buffer.is_max_exceeded:
                    self._finalize_and_submit()

        # Transition to SPEECH_ENDED: finalize segment
        if curr == VADState.SPEECH_ENDED:
            self._finalize_and_submit()

        # Transition to SILENCE/NOISE_ONLY from POSSIBLE_SPEECH: cancel
        if curr in (VADState.SILENCE, VADState.NOISE_ONLY) and prev == VADState.POSSIBLE_SPEECH:
            if self._segment_buffer.is_recording:
                self._segment_buffer.cancel_segment()

    def _finalize_and_submit(self) -> None:
        """Finalize current segment and submit to STT if valid."""
        segment = self._segment_buffer.end_segment()
        if segment is None:
            return

        if segment.is_valid:
            submitted = self._stt_worker.submit(segment)
            logger.info(
                "[VAD] state=SPEECH_ENDED duration_ms=%.0f queued=%s",
                segment.metadata.duration_ms, submitted
            )
        else:
            logger.info(
                "[VAD] Segment rejected: reason=%s duration_ms=%.0f",
                segment.metadata.reason_code, segment.metadata.duration_ms
            )
