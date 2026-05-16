"""
modules/stt_realtime.py - 실시간 STT 트리거 엔진
마이크 background audio stream에서 VAD 상태 머신으로 발화를 감지하고,
speech segment를 faster-whisper background worker에 전달하여 한국어 STT를 수행합니다.

아키텍처:
┌─────────────┐    100ms chunks    ┌──────────────┐    SPEECH_ENDED    ┌─────────────┐
│ Audio Stream │ ────────────────> │ VAD State    │ ──────────────────> │ STT Worker  │
│ (sounddevice)│                    │ Machine      │                    │ (Thread)    │
└─────────────┘                    └──────────────┘                    └─────────────┘
                                         │                                    │
                                   pre-roll 500ms                       faster-whisper
                                   speech buffer                        tiny/ko/cpu/int8

VAD 상태 머신:
- SILENCE: noise floor 학습, pre-roll 버퍼 유지
- SPEECH_START: RMS > noise_floor * factor 감지, pre-roll 포함 시작
- SPEAKING: 음성 누적 중
- SPEECH_END: silence_duration 초과 → segment 완성 → STT queue 전달

핵심 설계:
- 자체 audio stream (controller의 MicrophoneCapture와 독립)
- adaptive noise floor (최근 2초 무음 구간 평균)
- pre-roll buffer 500ms (발화 시작 부분 보존)
- background STT worker thread (UI 블로킹 없음)
- queue 기반 비동기 처리
- voice/full/debug mode에서만 동작
"""

import numpy as np
import threading
import queue
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Callable
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# 상수 및 데이터 구조
# ============================================================

class VADState(str, Enum):
    """VAD 상태 머신 상태"""
    SILENCE = "SILENCE"
    SPEECH_START = "SPEECH_START"
    SPEAKING = "SPEAKING"
    SPEECH_END = "SPEECH_END"


@dataclass
class ChunkMetrics:
    """100ms chunk 메트릭"""
    rms: float = 0.0
    peak: float = 0.0
    dbfs: float = -96.0
    is_speech: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class SpeechSegment:
    """완성된 speech segment (STT queue에 전달)"""
    audio: np.ndarray               # float32 mono PCM
    duration_sec: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    peak_rms: float = 0.0


@dataclass
class STTRealtimeResult:
    """실시간 STT 결과"""
    text: str = ""
    confidence: Optional[float] = None
    duration_sec: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    model_name: str = ""
    error: str = ""
    is_success: bool = False


@dataclass
class STTRealtimeStatus:
    """UI 표시용 실시간 상태"""
    # VAD
    vad_state: str = "SILENCE"
    noise_floor: float = 0.0
    current_rms: float = 0.0
    current_peak: float = 0.0
    current_dbfs: float = -96.0
    speech_threshold: float = 0.0

    # Segment
    segment_duration_sec: float = 0.0
    segments_total: int = 0

    # STT Worker
    queue_size: int = 0
    model_loaded: bool = False
    model_name: str = ""
    worker_active: bool = False

    # Results
    last_text: str = ""
    last_confidence: Optional[float] = None
    last_timestamp: Optional[datetime] = None
    total_transcriptions: int = 0

    # Stream
    stream_active: bool = False
    sample_rate: int = 16000
    device_name: str = ""


# ============================================================
# 실시간 STT 엔진
# ============================================================

class STTRealtimeEngine:
    """
    실시간 STT 트리거 엔진.
    자체 audio stream → VAD state machine → STT worker thread.
    """

    # VAD 설정
    CHUNK_DURATION_MS = 100             # 100ms per chunk
    NOISE_FLOOR_WINDOW_SEC = 2.0       # noise floor 학습 윈도우
    NOISE_FLOOR_FACTOR = 3.0           # speech threshold = noise_floor * factor
    NOISE_FLOOR_MIN = 0.005            # 최소 noise floor (완전 무음 방지)
    PRE_ROLL_SEC = 0.5                 # pre-roll buffer (500ms)
    SILENCE_TIMEOUT_SEC = 1.5          # 무음 지속 시 SPEECH_END
    MIN_SPEECH_SEC = 0.8               # 최소 speech segment 길이
    MAX_SPEECH_SEC = 30.0              # 최대 speech segment 길이

    def __init__(self, config=None):
        from config import Config, DEFAULT_CONFIG
        self._config = config or DEFAULT_CONFIG

        self._sample_rate = self._config.audio_sample_rate
        self._chunk_samples = int(self._sample_rate * self.CHUNK_DURATION_MS / 1000)

        # Apply config overrides
        self.CHUNK_DURATION_MS = getattr(self._config, 'stt_rt_chunk_ms', 100)
        self.PRE_ROLL_SEC = getattr(self._config, 'stt_rt_pre_roll_sec', 0.5)
        self.SILENCE_TIMEOUT_SEC = getattr(self._config, 'stt_rt_silence_timeout_sec', 1.5)
        self.MIN_SPEECH_SEC = getattr(self._config, 'stt_rt_min_speech_sec', 0.8)
        self.MAX_SPEECH_SEC = getattr(self._config, 'stt_rt_max_speech_sec', 30.0)
        self.NOISE_FLOOR_FACTOR = getattr(self._config, 'stt_rt_noise_floor_factor', 3.0)
        self.NOISE_FLOOR_MIN = getattr(self._config, 'stt_rt_noise_floor_min', 0.005)
        self.NOISE_FLOOR_WINDOW_SEC = getattr(self._config, 'stt_rt_noise_floor_window_sec', 2.0)

        # Recalculate with updated config
        self._chunk_samples = int(self._sample_rate * self.CHUNK_DURATION_MS / 1000)

        # Audio stream
        self._stream = None
        self._stream_active = False
        self._device_id: Optional[int] = None
        self._device_name: str = ""

        # VAD state machine
        self._vad_state = VADState.SILENCE
        self._noise_floor = 0.01
        self._noise_samples: deque = deque(maxlen=int(self.NOISE_FLOOR_WINDOW_SEC * 1000 / self.CHUNK_DURATION_MS))
        self._silence_start: float = 0.0
        self._speech_start: float = 0.0

        # Pre-roll buffer (500ms worth of chunks)
        pre_roll_chunks = int(self.PRE_ROLL_SEC * 1000 / self.CHUNK_DURATION_MS)
        self._pre_roll: deque = deque(maxlen=max(pre_roll_chunks, 1))

        # Speech segment buffer
        self._speech_buffer: List[np.ndarray] = []
        self._speech_peak_rms: float = 0.0

        # STT queue and worker
        queue_size = getattr(self._config, 'stt_rt_queue_size', 10)
        self._stt_queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._stt_worker_thread: Optional[threading.Thread] = None
        self._stt_model = None
        self._model_loaded = False
        self._model_name = ""

        # Results
        self._results: deque = deque(maxlen=20)
        self._last_result: Optional[STTRealtimeResult] = None
        self._total_transcriptions = 0
        self._segments_total = 0

        # Control
        self._running = False
        self._lock = threading.Lock()

        # Callbacks
        self._on_result: Optional[Callable[[STTRealtimeResult], None]] = None

    # ================================================================
    # Lifecycle
    # ================================================================

    def start(self, device_id: Optional[int] = None,
              on_result: Optional[Callable[[STTRealtimeResult], None]] = None) -> bool:
        """
        실시간 STT 시작.
        1. faster-whisper 모델 로드
        2. STT worker thread 시작
        3. Audio stream 시작

        Args:
            device_id: 마이크 장치 ID (None=시스템 기본)
            on_result: STT 결과 콜백

        Returns:
            True if started successfully
        """
        if self._running:
            return True

        self._on_result = on_result
        self._device_id = device_id or self._config.audio_device_id

        # 1. 모델 로드
        if not self._load_model():
            return False

        # 2. Worker thread 시작
        self._running = True
        self._stt_worker_thread = threading.Thread(
            target=self._stt_worker_loop, daemon=True, name="STT-Worker"
        )
        self._stt_worker_thread.start()

        # 3. Audio stream 시작
        if not self._start_stream():
            self._running = False
            return False

        return True

    def stop(self):
        """실시간 STT 정지"""
        if not self._running:
            return

        self._running = False
        self._stop_stream()

        # Worker 종료 대기
        if self._stt_worker_thread and self._stt_worker_thread.is_alive():
            self._stt_queue.put(None)  # sentinel
            self._stt_worker_thread.join(timeout=5.0)

        # 상태 리셋
        self._vad_state = VADState.SILENCE
        self._speech_buffer.clear()
        self._pre_roll.clear()

    def is_running(self) -> bool:
        return self._running

    # ================================================================
    # Status (UI용)
    # ================================================================

    def get_status(self) -> STTRealtimeStatus:
        """현재 상태 반환 (UI 표시용)"""
        with self._lock:
            segment_dur = 0.0
            if self._speech_buffer:
                total_samples = sum(len(chunk) for chunk in self._speech_buffer)
                segment_dur = total_samples / self._sample_rate

            return STTRealtimeStatus(
                vad_state=self._vad_state.value,
                noise_floor=self._noise_floor,
                current_rms=self._last_chunk_rms if hasattr(self, '_last_chunk_rms') else 0.0,
                current_peak=self._last_chunk_peak if hasattr(self, '_last_chunk_peak') else 0.0,
                current_dbfs=self._last_chunk_dbfs if hasattr(self, '_last_chunk_dbfs') else -96.0,
                speech_threshold=self._noise_floor * self.NOISE_FLOOR_FACTOR,
                segment_duration_sec=segment_dur,
                segments_total=self._segments_total,
                queue_size=self._stt_queue.qsize(),
                model_loaded=self._model_loaded,
                model_name=self._model_name,
                worker_active=self._running,
                last_text=self._last_result.text if self._last_result else "",
                last_confidence=self._last_result.confidence if self._last_result else None,
                last_timestamp=self._last_result.timestamp if self._last_result else None,
                total_transcriptions=self._total_transcriptions,
                stream_active=self._stream_active,
                sample_rate=self._sample_rate,
                device_name=self._device_name,
            )

    def get_results(self, count: int = 5) -> List[STTRealtimeResult]:
        """최근 N개 결과 반환"""
        with self._lock:
            results = list(self._results)
            return results[-count:] if len(results) > count else results

    # ================================================================
    # Audio Stream
    # ================================================================

    def _start_stream(self) -> bool:
        """sounddevice InputStream 시작"""
        try:
            import sounddevice as sd

            # 장치 정보
            if self._device_id is not None:
                info = sd.query_devices(self._device_id)
            else:
                info = sd.query_devices(kind='input')
                self._device_id = sd.default.device[0]

            self._device_name = info.get('name', 'Unknown') if info else 'Unknown'

            self._stream = sd.InputStream(
                device=self._device_id,
                samplerate=self._sample_rate,
                channels=1,
                dtype='float32',
                blocksize=self._chunk_samples,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._stream_active = True
            return True

        except ImportError:
            return False
        except Exception:
            return False

    def _stop_stream(self):
        """Audio stream 정지"""
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self._stream = None
        self._stream_active = False

    def _audio_callback(self, indata, frames, time_info, status):
        """
        Audio stream callback (100ms chunk 단위).
        VAD state machine 처리.
        """
        if not self._running:
            return

        # mono로 변환
        chunk = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        chunk = chunk.astype(np.float32)

        # 메트릭 계산
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        peak = float(np.max(np.abs(chunk)))
        dbfs = float(20 * np.log10(max(rms, 1e-10)))

        with self._lock:
            self._last_chunk_rms = rms
            self._last_chunk_peak = peak
            self._last_chunk_dbfs = dbfs

        # VAD state machine 처리
        self._process_vad(chunk, rms)

    # ================================================================
    # VAD State Machine
    # ================================================================

    def _process_vad(self, chunk: np.ndarray, rms: float):
        """
        VAD 상태 머신 처리.
        SILENCE → SPEECH_START → SPEAKING → SPEECH_END → SILENCE
        """
        now = time.time()
        threshold = self._noise_floor * self.NOISE_FLOOR_FACTOR
        is_speech = rms > max(threshold, self.NOISE_FLOOR_MIN * self.NOISE_FLOOR_FACTOR)

        with self._lock:
            if self._vad_state == VADState.SILENCE:
                # noise floor 학습
                if not is_speech:
                    self._noise_samples.append(rms)
                    if self._noise_samples:
                        self._noise_floor = max(
                            np.mean(list(self._noise_samples)),
                            self.NOISE_FLOOR_MIN,
                        )

                # pre-roll 유지
                self._pre_roll.append(chunk.copy())

                # speech 감지?
                if is_speech:
                    self._vad_state = VADState.SPEECH_START
                    self._speech_start = now
                    # pre-roll을 speech buffer에 추가
                    self._speech_buffer = [np.concatenate(list(self._pre_roll))]
                    self._speech_peak_rms = rms
                    self._pre_roll.clear()

            elif self._vad_state == VADState.SPEECH_START:
                # 바로 SPEAKING으로 전환
                self._speech_buffer.append(chunk.copy())
                self._speech_peak_rms = max(self._speech_peak_rms, rms)
                self._vad_state = VADState.SPEAKING
                self._silence_start = 0.0

            elif self._vad_state == VADState.SPEAKING:
                self._speech_buffer.append(chunk.copy())
                self._speech_peak_rms = max(self._speech_peak_rms, rms)

                if not is_speech:
                    if self._silence_start == 0.0:
                        self._silence_start = now
                    elif now - self._silence_start >= self.SILENCE_TIMEOUT_SEC:
                        # SPEECH_END
                        self._vad_state = VADState.SPEECH_END
                else:
                    self._silence_start = 0.0

                # 최대 길이 초과 시 강제 종료
                total_samples = sum(len(c) for c in self._speech_buffer)
                if total_samples / self._sample_rate >= self.MAX_SPEECH_SEC:
                    self._vad_state = VADState.SPEECH_END

            if self._vad_state == VADState.SPEECH_END:
                self._finalize_segment()
                self._vad_state = VADState.SILENCE
                self._silence_start = 0.0

    def _finalize_segment(self):
        """Speech segment 완성 → STT queue에 전달"""
        if not self._speech_buffer:
            return

        audio = np.concatenate(self._speech_buffer)
        duration = len(audio) / self._sample_rate

        # 최소 길이 미달 시 버림
        if duration < self.MIN_SPEECH_SEC:
            self._speech_buffer.clear()
            return

        segment = SpeechSegment(
            audio=audio,
            duration_sec=duration,
            start_time=self._speech_start,
            end_time=time.time(),
            peak_rms=self._speech_peak_rms,
        )

        self._segments_total += 1
        self._speech_buffer.clear()
        self._speech_peak_rms = 0.0

        # Queue에 추가 (가득 차면 가장 오래된 것 버림)
        try:
            self._stt_queue.put_nowait(segment)
        except queue.Full:
            try:
                self._stt_queue.get_nowait()
                self._stt_queue.put_nowait(segment)
            except queue.Empty:
                pass

    # ================================================================
    # STT Worker Thread
    # ================================================================

    def _load_model(self) -> bool:
        """faster-whisper 모델 로드 (config.stt_rt_model_size, 기본 tiny)"""
        try:
            from faster_whisper import WhisperModel
            model_size = getattr(self._config, 'stt_rt_model_size', 'tiny')
            self._stt_model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
            )
            self._model_loaded = True
            self._model_name = f"faster-whisper-{model_size}"
            return True
        except ImportError:
            self._model_loaded = False
            self._model_name = "NOT_INSTALLED"
            return False
        except Exception:
            self._model_loaded = False
            self._model_name = "LOAD_FAILED"
            return False

    def _stt_worker_loop(self):
        """Background STT worker thread - queue에서 segment를 꺼내 transcribe"""
        while self._running:
            try:
                segment = self._stt_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if segment is None:
                break  # sentinel → 종료

            result = self._transcribe_segment(segment)

            with self._lock:
                self._last_result = result
                if result.is_success and result.text.strip():
                    self._results.append(result)
                    self._total_transcriptions += 1

            # 콜백 호출
            if self._on_result and result.is_success and result.text.strip():
                try:
                    self._on_result(result)
                except Exception:
                    pass

    def _transcribe_segment(self, segment: SpeechSegment) -> STTRealtimeResult:
        """단일 segment를 faster-whisper로 transcribe"""
        if not self._model_loaded or self._stt_model is None:
            return STTRealtimeResult(error="모델 미로드", is_success=False)

        try:
            segments_iter, info = self._stt_model.transcribe(
                segment.audio,
                language="ko",
                beam_size=3,
                vad_filter=True,
            )

            texts = []
            confidences = []
            for seg in segments_iter:
                text = seg.text.strip()
                if text:
                    texts.append(text)
                    if hasattr(seg, 'avg_logprob'):
                        import math
                        confidences.append(math.exp(seg.avg_logprob))

            text = " ".join(texts).strip()
            avg_conf = sum(confidences) / len(confidences) if confidences else None

            return STTRealtimeResult(
                text=text,
                confidence=avg_conf,
                duration_sec=segment.duration_sec,
                model_name=self._model_name,
                is_success=True,
            )

        except Exception as e:
            return STTRealtimeResult(
                error=str(e),
                duration_sec=segment.duration_sec,
                is_success=False,
            )

    # ================================================================
    # Self Test
    # ================================================================

    @staticmethod
    def self_test() -> List[dict]:
        """
        STT Self Test: import → 모델 로드 → 더미 transcribe → 마이크 확인
        Returns: list of {step, success, message, duration_ms}
        """
        results = []

        # Step 1: faster-whisper import
        t0 = time.time()
        try:
            from faster_whisper import WhisperModel  # noqa: F401
            results.append({
                "step": "faster-whisper import",
                "success": True,
                "message": "OK",
                "duration_ms": (time.time() - t0) * 1000,
            })
        except ImportError as e:
            results.append({
                "step": "faster-whisper import",
                "success": False,
                "message": f"미설치: {e}",
                "duration_ms": (time.time() - t0) * 1000,
            })
            return results

        # Step 2: 모델 로드 (tiny)
        t0 = time.time()
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            results.append({
                "step": "모델 로드 (tiny/cpu/int8)",
                "success": True,
                "message": "OK",
                "duration_ms": (time.time() - t0) * 1000,
            })
        except Exception as e:
            results.append({
                "step": "모델 로드 (tiny/cpu/int8)",
                "success": False,
                "message": str(e),
                "duration_ms": (time.time() - t0) * 1000,
            })
            return results

        # Step 3: 더미 transcribe
        t0 = time.time()
        try:
            dummy = np.zeros(16000, dtype=np.float32)  # 1초 무음
            segs, info = model.transcribe(dummy, language="ko", beam_size=1)
            _ = [s.text for s in segs]
            results.append({
                "step": "Transcribe 테스트 (1s 무음)",
                "success": True,
                "message": f"language_prob={info.language_probability:.2f}",
                "duration_ms": (time.time() - t0) * 1000,
            })
        except Exception as e:
            results.append({
                "step": "Transcribe 테스트",
                "success": False,
                "message": str(e),
                "duration_ms": (time.time() - t0) * 1000,
            })

        # Step 4: sounddevice / 마이크 확인
        t0 = time.time()
        try:
            import sounddevice as sd
            default = sd.query_devices(kind='input')
            results.append({
                "step": "마이크 확인",
                "success": True,
                "message": f"{default['name']} (SR={int(default['default_samplerate'])}Hz)",
                "duration_ms": (time.time() - t0) * 1000,
            })
        except ImportError:
            results.append({
                "step": "마이크 확인",
                "success": False,
                "message": "sounddevice 미설치",
                "duration_ms": (time.time() - t0) * 1000,
            })
        except Exception as e:
            results.append({
                "step": "마이크 확인",
                "success": False,
                "message": str(e),
                "duration_ms": (time.time() - t0) * 1000,
            })

        return results
