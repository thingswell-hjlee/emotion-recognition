"""
modules/stt_worker.py - Background STT Worker
Processes speech segments from a queue in a background thread using faster-whisper.

Design:
- Runs as a daemon thread, independent of UI
- Receives SpeechSegment objects via a bounded queue (max 3)
- When queue is full, drops oldest segment (never blocks producer)
- Loads faster-whisper model on first use (lazy loading)
- Reports status: STT_DISABLED, ENGINE_NOT_INSTALLED, MODEL_NOT_LOADED,
  MODEL_LOADING, MODEL_READY, WAITING_FOR_SPEECH, TRANSCRIBING, OK, STT_ERROR
- Stores recent results for UI polling
- Thread-safe status/result access

Usage:
    worker = STTWorker(model_size="tiny", language="ko")
    worker.start()
    worker.submit(segment)  # non-blocking
    status = worker.get_status()
    results = worker.get_results(5)
    worker.stop()
"""

import sys
import os
import time
import threading
import queue
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# --- STT Status Codes ---
STT_DISABLED = "STT_DISABLED"
ENGINE_NOT_INSTALLED = "ENGINE_NOT_INSTALLED"
MODEL_NOT_LOADED = "MODEL_NOT_LOADED"
MODEL_LOADING = "MODEL_LOADING"
MODEL_READY = "MODEL_READY"
WAITING_FOR_SPEECH = "WAITING_FOR_SPEECH"
TRANSCRIBING = "TRANSCRIBING"
STT_OK = "OK"
STT_ERROR = "STT_ERROR"


@dataclass
class STTResult:
    """Result of a single STT transcription."""
    text: str = ""
    confidence: Optional[float] = None
    duration_sec: float = 0.0
    latency_ms: float = 0.0
    segment_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = STT_OK
    error_message: str = ""
    model_name: str = ""

    @property
    def is_success(self) -> bool:
        return self.status == STT_OK and len(self.text.strip()) > 0


@dataclass
class STTWorkerStatus:
    """Current status of the STT worker for UI display."""
    status: str = STT_DISABLED
    model_name: str = ""
    model_loaded: bool = False
    queue_size: int = 0
    queue_max: int = 3
    total_processed: int = 0
    total_success: int = 0
    total_errors: int = 0
    last_text: str = ""
    last_confidence: Optional[float] = None
    last_latency_ms: float = 0.0
    last_status: str = ""
    last_timestamp: Optional[datetime] = None
    error_message: str = ""
    is_running: bool = False


class STTWorker:
    """
    Background STT worker that processes speech segments using faster-whisper.

    Runs a daemon thread that:
    1. Waits for segments in a bounded queue
    2. Transcribes each segment using faster-whisper (tiny/ko/cpu/int8)
    3. Stores results for UI polling
    4. Never blocks the producer (drops oldest on full queue)

    Args:
        model_size: Whisper model size ("tiny", "base", "small"). Default "tiny".
        language: Language code. Default "ko".
        device: Compute device. Default "cpu".
        compute_type: Quantization type. Default "int8".
        queue_max_size: Maximum segments in queue. Default 3.
        enabled: Whether STT is enabled. Default True.
    """

    def __init__(
        self,
        model_size: str = "tiny",
        language: str = "ko",
        device: str = "cpu",
        compute_type: str = "int8",
        queue_max_size: int = 3,
        enabled: bool = True,
    ):
        self._model_size = model_size
        self._language = language
        self._device = device
        self._compute_type = compute_type
        self._queue_max = queue_max_size
        self._enabled = enabled

        # Queue for segments
        self._queue: queue.Queue = queue.Queue(maxsize=queue_max_size)

        # Model state
        self._model = None
        self._model_loaded = False
        self._model_name = f"faster-whisper-{model_size}"

        # Worker thread
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()

        # Status tracking
        self._lock = threading.Lock()
        self._status = STT_DISABLED if not enabled else MODEL_NOT_LOADED
        self._error_message = ""
        self._total_processed = 0
        self._total_success = 0
        self._total_errors = 0

        # Results history
        self._results: deque = deque(maxlen=20)
        self._last_result: Optional[STTResult] = None

    def start(self) -> None:
        """Start the STT worker thread. Loads model on first segment."""
        if self._running:
            return

        if not self._enabled:
            with self._lock:
                self._status = STT_DISABLED
            return

        self._stop_event.clear()
        self._running = True

        self._thread = threading.Thread(
            target=self._worker_loop,
            name="STT-Worker",
            daemon=True,
        )
        self._thread.start()

        with self._lock:
            self._status = MODEL_NOT_LOADED

        logger.info("[STT] Worker thread started (model=%s, lang=%s)", self._model_size, self._language)

    def stop(self) -> None:
        """Stop the STT worker thread."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        # Put sentinel to unblock queue.get()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)

        self._thread = None

        with self._lock:
            self._status = STT_DISABLED

        logger.info("[STT] Worker thread stopped.")

    def submit(self, segment) -> bool:
        """
        Submit a speech segment for transcription (non-blocking).

        If queue is full, drops the oldest segment and adds the new one.

        Args:
            segment: A SpeechSegment object with .audio and .metadata.

        Returns:
            True if submitted successfully, False if worker not running.
        """
        if not self._running or not self._enabled:
            return False

        # Drop oldest if full
        if self._queue.full():
            try:
                dropped = self._queue.get_nowait()
                if dropped is not None:
                    logger.warning("[STT] Queue full, dropped segment id=%s",
                                   getattr(getattr(dropped, 'metadata', None), 'segment_id', '?'))
            except queue.Empty:
                pass

        try:
            self._queue.put_nowait(segment)
            return True
        except queue.Full:
            return False

    def get_status(self) -> STTWorkerStatus:
        """Get current worker status for UI display."""
        with self._lock:
            return STTWorkerStatus(
                status=self._status,
                model_name=self._model_name,
                model_loaded=self._model_loaded,
                queue_size=self._queue.qsize(),
                queue_max=self._queue_max,
                total_processed=self._total_processed,
                total_success=self._total_success,
                total_errors=self._total_errors,
                last_text=self._last_result.text if self._last_result else "",
                last_confidence=self._last_result.confidence if self._last_result else None,
                last_latency_ms=self._last_result.latency_ms if self._last_result else 0.0,
                last_status=self._last_result.status if self._last_result else "",
                last_timestamp=self._last_result.timestamp if self._last_result else None,
                error_message=self._error_message,
                is_running=self._running,
            )

    def get_results(self, count: int = 5) -> List[STTResult]:
        """Get recent STT results (newest first)."""
        with self._lock:
            results = list(self._results)
        return list(reversed(results[-count:]))

    # ================================================================
    # Internal worker loop
    # ================================================================

    def _worker_loop(self) -> None:
        """Main worker thread loop."""
        # Load model first
        if not self._load_model():
            return

        with self._lock:
            self._status = WAITING_FOR_SPEECH

        logger.info("[STT] model_ready engine=faster-whisper model=%s", self._model_size)

        while not self._stop_event.is_set():
            try:
                segment = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Sentinel check
            if segment is None:
                break

            # Process segment
            self._transcribe(segment)

        logger.info("[STT] Worker loop exited.")

    def _load_model(self) -> bool:
        """Load the faster-whisper model. Returns True on success."""
        with self._lock:
            self._status = MODEL_LOADING
            self._error_message = ""

        logger.info("[STT] model_loading engine=faster-whisper model=%s", self._model_size)

        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            with self._lock:
                self._model_loaded = True
                self._status = MODEL_READY
                self._error_message = ""
            return True

        except ImportError:
            with self._lock:
                self._status = ENGINE_NOT_INSTALLED
                self._model_loaded = False
                self._error_message = "faster-whisper not installed. Run: pip install -r requirements-stt.txt"
            logger.error("[STT] error reason=faster-whisper not installed")
            return False

        except Exception as e:
            with self._lock:
                self._status = STT_ERROR
                self._model_loaded = False
                self._error_message = f"Model load failed: {e}"
            logger.error("[STT] error reason=model_load_failed: %s", e)
            return False

    def _transcribe(self, segment) -> None:
        """Transcribe a single segment."""
        seg_id = getattr(getattr(segment, 'metadata', None), 'segment_id', 'unknown')
        duration = getattr(getattr(segment, 'metadata', None), 'duration_ms', 0) / 1000.0

        with self._lock:
            self._status = TRANSCRIBING

        logger.info("[STT] transcribing segment_id=%s duration=%.1fs", seg_id, duration)

        t0 = time.time()

        try:
            audio = segment.audio if hasattr(segment, 'audio') else np.array([], dtype=np.float32)

            if len(audio) == 0:
                result = STTResult(
                    segment_id=seg_id,
                    status=STT_ERROR,
                    error_message="Empty audio",
                    duration_sec=duration,
                )
            else:
                segments_iter, info = self._model.transcribe(
                    audio,
                    language=self._language,
                    beam_size=3,
                    vad_filter=True,
                )

                texts = []
                confidences = []
                for seg in segments_iter:
                    t = seg.text.strip()
                    if t:
                        texts.append(t)
                        if hasattr(seg, 'avg_logprob'):
                            import math
                            confidences.append(math.exp(seg.avg_logprob))

                text = " ".join(texts).strip()
                avg_conf = sum(confidences) / len(confidences) if confidences else None
                latency_ms = (time.time() - t0) * 1000.0

                result = STTResult(
                    text=text,
                    confidence=avg_conf,
                    duration_sec=duration,
                    latency_ms=latency_ms,
                    segment_id=seg_id,
                    status=STT_OK,
                    model_name=self._model_name,
                )

                logger.info('[STT] done text="%s" latency_ms=%.0f', text[:50], latency_ms)

        except Exception as e:
            latency_ms = (time.time() - t0) * 1000.0
            result = STTResult(
                segment_id=seg_id,
                status=STT_ERROR,
                error_message=str(e),
                duration_sec=duration,
                latency_ms=latency_ms,
            )
            logger.error("[STT] error reason=%s", e)

        # Store result
        with self._lock:
            self._last_result = result
            self._results.append(result)
            self._total_processed += 1
            if result.is_success:
                self._total_success += 1
                self._status = WAITING_FOR_SPEECH
            else:
                self._total_errors += 1
                self._status = WAITING_FOR_SPEECH
                self._error_message = result.error_message
