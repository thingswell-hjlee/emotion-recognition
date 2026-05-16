"""
modules/stt_engine.py - 한국어 STT (Speech-to-Text) 엔진
마이크 입력을 한국어 텍스트로 변환합니다.

엔진 구조:
- BaseSTTEngine (추상 인터페이스)
- FasterWhisperSTTEngine (faster-whisper 기반, 기본 엔진)
- LocalWhisperSTTEngine (openai-whisper 기반, fallback)
- DisabledSTTEngine (STT 비활성화 시)

엔진 선택 우선순위:
1. faster-whisper 사용 가능 → FasterWhisperSTTEngine
2. openai-whisper 사용 가능 → LocalWhisperSTTEngine
3. 둘 다 없음 → DisabledSTTEngine (STT_ENGINE_NOT_INSTALLED)

상태 코드:
- STT_DISABLED_BY_MODE: 현재 모드가 minimal/face
- STT_DISABLED_BY_USER: STT 토글 OFF
- STT_ENGINE_NOT_INSTALLED: faster-whisper/openai-whisper 미설치
- STT_MODEL_NOT_LOADED: 모델 로딩 전
- STT_READY: voice/full 모드에서 사용 가능
- STT_WAITING_FOR_SPEECH: 유효 발화 대기 중
- STT_TRANSCRIBING: 인식 중
- STT_OK: 인식 성공

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
from typing import Optional, List, Dict
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config, DEFAULT_CONFIG


# === 엔진 사용 가능 여부 감지 ===

def _check_faster_whisper() -> bool:
    """faster-whisper import 가능 여부"""
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        return True
    except ImportError:
        return False


def _check_openai_whisper() -> bool:
    """openai-whisper import 가능 여부"""
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


faster_whisper_available: bool = _check_faster_whisper()
openai_whisper_available: bool = _check_openai_whisper()


# === STT 상태 코드 ===
STT_OK = "STT_OK"
STT_NO_AUDIO = "NO_AUDIO"
STT_SILENCE = "SILENCE_DETECTED"
STT_DISABLED_BY_MODE = "STT_DISABLED_BY_MODE"
STT_DISABLED_BY_USER = "STT_DISABLED_BY_USER"
STT_ENGINE_NOT_INSTALLED = "STT_ENGINE_NOT_INSTALLED"
STT_MODEL_NOT_LOADED = "STT_MODEL_NOT_LOADED"
STT_READY = "STT_READY"
STT_WAITING_FOR_SPEECH = "STT_WAITING_FOR_SPEECH"
STT_TRANSCRIBING = "STT_TRANSCRIBING"
STT_ERROR = "STT_ERROR"

# 하위 호환: 이전 코드에서 사용하는 상수
STT_DISABLED = "STT_DISABLED_BY_USER"
STT_PROCESSING = "STT_TRANSCRIBING"


# === 상태 코드 → 사용자 메시지 매핑 ===
STT_STATUS_MESSAGES: Dict[str, str] = {
    STT_OK: "인식 성공",
    STT_NO_AUDIO: "오디오 없음",
    STT_SILENCE: "무음 감지 - STT 대기 중",
    STT_DISABLED_BY_MODE: "현재 모드가 minimal/face입니다",
    STT_DISABLED_BY_USER: "STT 토글이 OFF입니다",
    STT_ENGINE_NOT_INSTALLED: "faster-whisper/openai-whisper가 없습니다",
    STT_MODEL_NOT_LOADED: "모델 로딩 전입니다",
    STT_READY: "voice/full 모드에서 사용 가능",
    STT_WAITING_FOR_SPEECH: "유효 발화를 기다리는 중",
    STT_TRANSCRIBING: "인식 중...",
    STT_ERROR: "STT 오류 발생",
}


@dataclass
class STTResult:
    """STT 결과 구조체"""
    status: str = STT_DISABLED_BY_USER     # 상태 코드
    text: str = ""                         # 인식된 한국어 문장
    language: str = "ko"                   # 인식 언어
    confidence: Optional[float] = None     # 신뢰도 (가능한 경우)
    duration_sec: float = 0.0              # 입력 오디오 길이 (초)
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str = ""                # 에러 시 상세 메시지
    model_name: str = ""                   # 사용된 모델명

    def to_log_string(self) -> str:
        """구조화 로그 출력"""
        if self.status == STT_OK:
            conf_str = f" confidence={self.confidence:.2f}" if self.confidence else ""
            return (
                f'[STT] status=STT_OK text="{self.text}" language={self.language} '
                f'duration={self.duration_sec:.1f}s{conf_str}'
            )
        msg = self.error_message or STT_STATUS_MESSAGES.get(self.status, "unknown")
        return f"[STT] status={self.status} reason={msg}"


@dataclass
class STTEngineInfo:
    """STT 엔진 상태 정보 (UI 표시용)"""
    faster_whisper_available: bool = False
    openai_whisper_available: bool = False
    selected_engine: str = "disabled"
    engine_ready: bool = False
    model_loaded: bool = False
    model_name: str = ""
    stt_enabled_by_mode: bool = False
    stt_enabled_by_user: bool = False
    current_status: str = STT_DISABLED_BY_USER
    last_result: Optional[STTResult] = None
    init_error: str = ""


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

    def get_info(self) -> STTEngineInfo:
        """엔진 정보 반환"""
        return STTEngineInfo(
            faster_whisper_available=faster_whisper_available,
            openai_whisper_available=openai_whisper_available,
            selected_engine=self.engine_name,
            engine_ready=self.is_ready,
            model_loaded=self.is_ready,
        )


# === Faster Whisper Engine (기본 엔진) ===

class FasterWhisperSTTEngine(BaseSTTEngine):
    """
    faster-whisper 기반 STT (CTranslate2 최적화, 기본 권장 엔진).
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
                "faster-whisper 미설치. 설치: pip install -r requirements-stt.txt"
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


# === Local Whisper Engine (openai-whisper, fallback) ===

class LocalWhisperSTTEngine(BaseSTTEngine):
    """
    OpenAI Whisper 기반 로컬 STT (fallback 엔진).
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
                "openai-whisper 미설치. 설치: pip install openai-whisper"
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


# === Disabled Engine (STT OFF) ===

class DisabledSTTEngine(BaseSTTEngine):
    """STT 비활성화 시 사용"""

    def __init__(self, reason: str = STT_DISABLED_BY_USER):
        self._reason = reason

    def initialize(self) -> bool:
        return True

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> STTResult:
        return STTResult(
            status=self._reason,
            error_message=STT_STATUS_MESSAGES.get(self._reason, "비활성화"),
        )

    @property
    def is_ready(self) -> bool:
        return False

    @property
    def engine_name(self) -> str:
        return "disabled"

    @property
    def init_error(self) -> Optional[str]:
        if self._reason == STT_ENGINE_NOT_INSTALLED:
            return "faster-whisper/openai-whisper가 설치되지 않았습니다. pip install -r requirements-stt.txt"
        return None


# === Factory (auto-detection 포함) ===

def detect_best_engine() -> str:
    """
    사용 가능한 최적 엔진을 자동 감지합니다.
    우선순위: faster-whisper > openai-whisper > disabled

    Returns:
        "faster-whisper" / "whisper-local" / "disabled"
    """
    if faster_whisper_available:
        return "faster-whisper"
    elif openai_whisper_available:
        return "whisper-local"
    else:
        return "disabled"


def create_stt_engine(config: Config = DEFAULT_CONFIG) -> BaseSTTEngine:
    """
    설정에 따라 적절한 STT 엔진 인스턴스 생성.

    엔진 선택 로직:
    1. config.stt_enabled=False → DisabledSTTEngine(STT_DISABLED_BY_USER)
    2. config.stt_engine_type="auto" → 자동 감지
    3. config.stt_engine_type="faster-whisper" → FasterWhisperSTTEngine
    4. config.stt_engine_type="whisper-local" → LocalWhisperSTTEngine
    5. 선택된 엔진 import 불가 → fallback 시도 → DisabledSTTEngine
    """
    if not config.stt_enabled:
        return DisabledSTTEngine(reason=STT_DISABLED_BY_USER)

    engine_type = config.stt_engine_type

    # "auto" 또는 "faster-whisper" (기본값): 자동 감지
    if engine_type in ("auto", "faster-whisper"):
        if faster_whisper_available:
            engine = FasterWhisperSTTEngine(config)
            engine.initialize()
            return engine
        elif openai_whisper_available:
            # faster-whisper 없지만 openai-whisper는 있음 → fallback
            engine = LocalWhisperSTTEngine(config)
            engine.initialize()
            return engine
        else:
            return DisabledSTTEngine(reason=STT_ENGINE_NOT_INSTALLED)

    elif engine_type == "whisper-local":
        if openai_whisper_available:
            engine = LocalWhisperSTTEngine(config)
            engine.initialize()
            return engine
        elif faster_whisper_available:
            # openai-whisper 없지만 faster-whisper는 있음 → fallback
            engine = FasterWhisperSTTEngine(config)
            engine.initialize()
            return engine
        else:
            return DisabledSTTEngine(reason=STT_ENGINE_NOT_INSTALLED)

    elif engine_type == "disabled":
        return DisabledSTTEngine(reason=STT_DISABLED_BY_USER)

    else:
        # 알 수 없는 엔진 타입 → 자동 감지
        best = detect_best_engine()
        if best == "faster-whisper":
            engine = FasterWhisperSTTEngine(config)
            engine.initialize()
            return engine
        elif best == "whisper-local":
            engine = LocalWhisperSTTEngine(config)
            engine.initialize()
            return engine
        else:
            return DisabledSTTEngine(reason=STT_ENGINE_NOT_INSTALLED)


def get_stt_engine_info(config: Config = DEFAULT_CONFIG, engine: Optional[BaseSTTEngine] = None) -> STTEngineInfo:
    """현재 STT 엔진 상태 정보를 종합적으로 반환 (UI 표시용)"""
    mode = config.run_mode
    stt_enabled_by_mode = mode in ("voice", "full")
    stt_enabled_by_user = config.stt_enabled

    # 현재 상태 결정
    if not stt_enabled_by_mode:
        current_status = STT_DISABLED_BY_MODE
    elif not stt_enabled_by_user:
        current_status = STT_DISABLED_BY_USER
    elif not faster_whisper_available and not openai_whisper_available:
        current_status = STT_ENGINE_NOT_INSTALLED
    elif engine and not engine.is_ready:
        current_status = STT_MODEL_NOT_LOADED
    elif engine and engine.is_ready:
        current_status = STT_READY
    else:
        current_status = STT_ENGINE_NOT_INSTALLED

    selected = "disabled"
    model_name = ""
    init_error = ""
    if engine:
        selected = engine.engine_name
        if engine.init_error:
            init_error = engine.init_error
        if engine.is_ready:
            model_name = selected

    return STTEngineInfo(
        faster_whisper_available=faster_whisper_available,
        openai_whisper_available=openai_whisper_available,
        selected_engine=selected,
        engine_ready=engine.is_ready if engine else False,
        model_loaded=engine.is_ready if engine else False,
        model_name=model_name,
        stt_enabled_by_mode=stt_enabled_by_mode,
        stt_enabled_by_user=stt_enabled_by_user,
        current_status=current_status,
        init_error=init_error,
    )


# === STT Self Test ===

@dataclass
class STTSelfTestResult:
    """셀프 테스트 결과"""
    step: str = ""
    success: bool = False
    message: str = ""
    duration_ms: float = 0.0


def run_stt_self_test(config: Config = DEFAULT_CONFIG) -> List[STTSelfTestResult]:
    """
    STT 셀프 테스트 실행.
    단계:
    1. faster-whisper import 확인
    2. 모델 tiny 로딩 확인
    3. 더미 오디오로 transcribe 테스트
    4. 결과 또는 실패 원인 반환
    """
    results: List[STTSelfTestResult] = []

    # Step 1: Import 확인
    t0 = time.time()
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        results.append(STTSelfTestResult(
            step="faster-whisper import",
            success=True,
            message="faster-whisper 라이브러리 import 성공",
            duration_ms=(time.time() - t0) * 1000,
        ))
    except ImportError as e:
        results.append(STTSelfTestResult(
            step="faster-whisper import",
            success=False,
            message=f"faster-whisper import 실패: {e}. pip install faster-whisper 실행 필요",
            duration_ms=(time.time() - t0) * 1000,
        ))
        # openai-whisper fallback 체크
        t1 = time.time()
        try:
            import whisper  # noqa: F401
            results.append(STTSelfTestResult(
                step="openai-whisper import (fallback)",
                success=True,
                message="openai-whisper import 성공 (fallback 가능)",
                duration_ms=(time.time() - t1) * 1000,
            ))
        except ImportError as e2:
            results.append(STTSelfTestResult(
                step="openai-whisper import (fallback)",
                success=False,
                message=f"openai-whisper도 없음: {e2}",
                duration_ms=(time.time() - t1) * 1000,
            ))
        return results

    # Step 2: 모델 로딩
    t0 = time.time()
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        results.append(STTSelfTestResult(
            step="모델 로딩 (tiny)",
            success=True,
            message="faster-whisper tiny 모델 로딩 성공",
            duration_ms=(time.time() - t0) * 1000,
        ))
    except Exception as e:
        results.append(STTSelfTestResult(
            step="모델 로딩 (tiny)",
            success=False,
            message=f"모델 로딩 실패: {e}",
            duration_ms=(time.time() - t0) * 1000,
        ))
        return results

    # Step 3: 더미 오디오 transcribe 테스트
    t0 = time.time()
    try:
        # 1초 무음 오디오 생성
        dummy_audio = np.zeros(16000, dtype=np.float32)
        segments, info = model.transcribe(
            dummy_audio,
            language="ko",
            beam_size=1,
        )
        # segments 소비 (generator)
        text_parts = [s.text for s in segments]
        results.append(STTSelfTestResult(
            step="Transcribe 테스트 (무음)",
            success=True,
            message=f"transcribe 호출 성공 (언어: {info.language}, 확률: {info.language_probability:.2f})",
            duration_ms=(time.time() - t0) * 1000,
        ))
    except Exception as e:
        results.append(STTSelfTestResult(
            step="Transcribe 테스트 (무음)",
            success=False,
            message=f"transcribe 실패: {e}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    # Step 4: 마이크 확인
    t0 = time.time()
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        default_input = sd.query_devices(kind='input')
        results.append(STTSelfTestResult(
            step="마이크 확인",
            success=True,
            message=f"기본 입력: {default_input['name']} (SR: {int(default_input['default_samplerate'])}Hz)",
            duration_ms=(time.time() - t0) * 1000,
        ))
    except ImportError:
        results.append(STTSelfTestResult(
            step="마이크 확인",
            success=False,
            message="sounddevice 미설치. pip install sounddevice 필요",
            duration_ms=(time.time() - t0) * 1000,
        ))
    except Exception as e:
        results.append(STTSelfTestResult(
            step="마이크 확인",
            success=False,
            message=f"마이크 확인 실패: {e}",
            duration_ms=(time.time() - t0) * 1000,
        ))

    return results


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
