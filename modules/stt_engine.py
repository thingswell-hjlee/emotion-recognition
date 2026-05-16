"""
modules/stt_engine.py - 한국어 STT (Speech-to-Text) 엔진
마이크 입력을 한국어 텍스트로 변환합니다.

엔진 구조:
- BaseSTTEngine (추상 인터페이스)
- LocalWhisperSTTEngine (openai-whisper 기반, 로컬 실행)
- FasterWhisperSTTEngine (faster-whisper 기반, 최적화)
- DisabledSTTEngine (STT 비활성화 시)

핵심 정책:
- VAD가 유효 발화를 감지한 경우에만 STT 실행
- 무음 시 STT 수행 안 함
- 모델 미설치 시 앱 중단 없이 상태 메시지 표시
- 한국어 고정 (language="ko")
- 모델 크기: tiny / base / small (기본: base)
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config, DEFAULT_CONFIG


# === STT 상태 코드 ===
STT_OK = "OK"
STT_NO_AUDIO = "NO_AUDIO"
STT_SILENCE = "SILENCE_DETECTED"
STT_DISABLED = "STT_DISABLED"
STT_MODEL_NOT_LOADED = "STT_MODEL_NOT_LOADED"
STT_ERROR = "STT_ERROR"
STT_PROCESSING = "PROCESSING"


@dataclass
class STTResult:
    """STT 결과 구조체"""
    status: str = STT_DISABLED          # OK / NO_AUDIO / SILENCE_DETECTED / etc.
    text: str = ""                      # 인식된 한국어 문장
    language: str = "ko"                # 인식 언어
    confidence: Optional[float] = None  # 신뢰도 (가능한 경우)
    duration_sec: float = 0.0           # 입력 오디오 길이 (초)
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str = ""             # 에러 시 상세 메시지
    model_name: str = ""                # 사용된 모델명

    def to_log_string(self) -> str:
        """구조화 로그 출력"""
        if self.status == STT_OK:
            conf_str = f" confidence={self.confidence:.2f}" if self.confidence else ""
            return (
                f'[STT] status=OK text="{self.text}" language={self.language} '
                f'duration={self.duration_sec:.1f}{conf_str}'
            )
        return f"[STT] status={self.status} reason={self.error_message or 'N/A'}"


# === Base Interface ===

class BaseSTTEngine(ABC):
    """STT 엔진 추상 인터페이스"""

    @abstractmethod
    def initialize(self) -> bool:
        """모델 로드. 실패 시 False 반환 (앱은 계속 실행)."""
        pass

    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> STTResult:
        """오디오를 텍스트로 변환."""
        pass

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        pass

    @property
    @abstractmethod
    def engine_name(self) -> str:
        pass

    @property
    def init_error(self) -> Optional[str]:
        return None


# === Local Whisper Engine (openai-whisper) ===

class LocalWhisperSTTEngine(BaseSTTEngine):
    """
    OpenAI Whisper 기반 로컬 STT.
    pip install openai-whisper
    """

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._model = None
        self._initialized = False
        self._init_error: Optional[str] = None
        self._model_size = config.stt_model_size  # tiny / base / small

    def initialize(self) -> bool:
        """Whisper 모델 로드 (최초 실행 시 다운로드 발생)"""
        try:
            import whisper
            self._model = whisper.load_model(self._model_size)
            self._initialized = True
            return True
        except ImportError:
            self._init_error = (
                "openai-whisper 미설치. 설치: pip install -r requirements-stt.txt"
            )
            return False
        except Exception as e:
            self._init_error = f"Whisper 모델 로드 실패: {e}"
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> STTResult:
        """Whisper로 한국어 음성 인식"""
        if not self._initialized or self._model is None:
            return STTResult(
                status=STT_MODEL_NOT_LOADED,
                error_message=self._init_error or "모델 미로드"
            )

        if audio is None or len(audio) == 0:
            return STTResult(status=STT_NO_AUDIO)

        duration = len(audio) / sample_rate

        try:
            # Whisper는 float32, 16kHz mono를 기대
            audio_float = audio.astype(np.float32)

            # 리샘플링 (16kHz가 아닌 경우)
            if sample_rate != 16000:
                try:
                    import librosa
                    audio_float = librosa.resample(audio_float, orig_sr=sample_rate, target_sr=16000)
                except ImportError:
                    pass  # 16kHz 아니면 그냥 진행

            result = self._model.transcribe(
                audio_float,
                language="ko",
                fp16=False,  # CPU 환경
                verbose=False,
            )

            text = result.get("text", "").strip()

            if not text:
                return STTResult(
                    status=STT_OK,
                    text="",
                    duration_sec=duration,
                    model_name=f"whisper-{self._model_size}",
                )

            # segments에서 평균 confidence 추출 (가능한 경우)
            segments = result.get("segments", [])
            avg_conf = None
            if segments:
                probs = [s.get("avg_logprob", 0) for s in segments]
                if probs:
                    import math
                    avg_conf = math.exp(sum(probs) / len(probs))  # log prob → prob

            return STTResult(
                status=STT_OK,
                text=text,
                language="ko",
                confidence=avg_conf,
                duration_sec=duration,
                model_name=f"whisper-{self._model_size}",
            )

        except Exception as e:
            return STTResult(
                status=STT_ERROR,
                error_message=str(e),
                duration_sec=duration,
            )

    @property
    def is_ready(self) -> bool:
        return self._initialized

    @property
    def engine_name(self) -> str:
        return f"whisper-local ({self._model_size})"

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error


# === Faster Whisper Engine ===

class FasterWhisperSTTEngine(BaseSTTEngine):
    """
    faster-whisper 기반 STT (CTranslate2 최적화).
    pip install faster-whisper
    """

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._model = None
        self._initialized = False
        self._init_error: Optional[str] = None
        self._model_size = config.stt_model_size

    def initialize(self) -> bool:
        """faster-whisper 모델 로드"""
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
            self._initialized = True
            return True
        except ImportError:
            self._init_error = (
                "faster-whisper 미설치. 설치: pip install faster-whisper"
            )
            return False
        except Exception as e:
            self._init_error = f"faster-whisper 모델 로드 실패: {e}"
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> STTResult:
        """faster-whisper로 한국어 음성 인식"""
        if not self._initialized or self._model is None:
            return STTResult(
                status=STT_MODEL_NOT_LOADED,
                error_message=self._init_error or "모델 미로드"
            )

        if audio is None or len(audio) == 0:
            return STTResult(status=STT_NO_AUDIO)

        duration = len(audio) / sample_rate

        try:
            audio_float = audio.astype(np.float32)

            segments, info = self._model.transcribe(
                audio_float,
                language="ko",
                beam_size=3,
                vad_filter=True,
            )

            texts = []
            confidences = []
            for segment in segments:
                texts.append(segment.text.strip())
                if hasattr(segment, 'avg_logprob'):
                    import math
                    confidences.append(math.exp(segment.avg_logprob))

            text = " ".join(texts).strip()
            avg_conf = sum(confidences) / len(confidences) if confidences else None

            return STTResult(
                status=STT_OK,
                text=text,
                language="ko",
                confidence=avg_conf,
                duration_sec=duration,
                model_name=f"faster-whisper-{self._model_size}",
            )

        except Exception as e:
            return STTResult(
                status=STT_ERROR,
                error_message=str(e),
                duration_sec=duration,
            )

    @property
    def is_ready(self) -> bool:
        return self._initialized

    @property
    def engine_name(self) -> str:
        return f"faster-whisper ({self._model_size})"

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error


# === Disabled Engine (STT OFF) ===

class DisabledSTTEngine(BaseSTTEngine):
    """STT 비활성화 시 사용"""

    def initialize(self) -> bool:
        return True

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> STTResult:
        return STTResult(status=STT_DISABLED)

    @property
    def is_ready(self) -> bool:
        return True

    @property
    def engine_name(self) -> str:
        return "disabled"


# === Factory ===

def create_stt_engine(config: Config = DEFAULT_CONFIG) -> BaseSTTEngine:
    """설정에 따라 적절한 STT 엔진 인스턴스 생성"""
    if not config.stt_enabled:
        return DisabledSTTEngine()

    engine_type = config.stt_engine_type

    if engine_type == "whisper-local":
        engine = LocalWhisperSTTEngine(config)
    elif engine_type == "faster-whisper":
        engine = FasterWhisperSTTEngine(config)
    else:
        return DisabledSTTEngine()

    engine.initialize()
    return engine


# === STT History (최근 5개 문장 관리) ===

class STTHistory:
    """최근 인식 문장 히스토리 (UI 표시용)"""

    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self._history: List[STTResult] = []

    def add(self, result: STTResult):
        """새 결과 추가 (OK이고 텍스트가 있는 경우만)"""
        if result.status == STT_OK and result.text:
            self._history.append(result)
            if len(self._history) > self.max_size:
                self._history = self._history[-self.max_size:]

    def get_recent(self) -> List[STTResult]:
        """최근 결과 리스트 반환 (최신 순)"""
        return list(reversed(self._history))

    def get_latest(self) -> Optional[STTResult]:
        """가장 최근 결과"""
        return self._history[-1] if self._history else None

    @property
    def count(self) -> int:
        return len(self._history)

    def clear(self):
        self._history.clear()
