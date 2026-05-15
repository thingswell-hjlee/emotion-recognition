"""
modules/voice_feedback.py - 음성 안내 모듈
pyttsx3 기반 TTS. 초기화 실패 시 텍스트만 반환.
기본 OFF (안정성 우선).
"""

import threading
import time
from typing import Optional, Dict, Callable
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DEFAULT_CONFIG


# 감정별 안내 메시지
EMOTION_MESSAGES: Dict[str, str] = {
    "neutral": "현재 상태는 안정적으로 보입니다.",
    "happy": "긍정적인 감정이 감지되었습니다.",
    "sad": "약간 우울한 상태로 보입니다.",
    "angry": "긴장되거나 화난 상태로 보입니다.",
    "surprised": "놀라운 반응이 감지되었습니다.",
    "fearful": "약간 긴장된 상태로 보입니다.",
    "disgusted": "불쾌한 감정이 감지되었습니다.",
    "stressed": "피로 또는 스트레스 신호가 있습니다.",
    "calm": "평온한 상태가 유지되고 있습니다.",
}

COMPARISON_MESSAGES: Dict[str, str] = {
    "안정적": "",
    "긍정 방향 변화": "감정이 긍정적으로 변하고 있습니다.",
    "부정 방향 변화": "감정이 부정적으로 변하고 있습니다.",
    "스트레스 증가 가능성": "스트레스가 증가하는 신호가 있습니다.",
    "감정 변동성 증가": "감정 변화가 커지고 있습니다.",
}


class VoiceFeedback:
    """감정 상태 음성 안내 (안전한 초기화, 기본 OFF)"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._engine = None
        self._initialized = False
        self._tts_available = False
        self._last_message = ""
        self._repeat_count = 0
        self._last_speak_time = 0.0
        self._speaking = False
        self._on_speak_start: Optional[Callable] = None
        self._on_speak_end: Optional[Callable] = None
        self._init_error: Optional[str] = None

    def initialize(self) -> bool:
        """TTS 엔진 초기화 (실패해도 앱은 계속 동작)"""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', 150)
            self._update_volume()
            self._tts_available = True
        except ImportError:
            self._init_error = "pyttsx3 미설치. 음성 안내 비활성화."
            self._tts_available = False
        except Exception as e:
            self._init_error = f"TTS 초기화 실패: {e}. 텍스트 안내만 제공."
            self._tts_available = False

        self._initialized = True
        return True  # 항상 True (앱 중단 방지)

    def speak(self, emotion: str, comparison_label: Optional[str] = None) -> str:
        """
        감정 상태 음성 안내.
        TTS 비활성화/실패 시에도 메시지 텍스트는 반환함.
        """
        # OFF면 빈 문자열 반환
        if not self.config.tts_enabled:
            return ""

        if not self._initialized:
            self.initialize()

        # 메시지 생성
        message = EMOTION_MESSAGES.get(emotion, "감정 상태를 분석 중입니다.")
        if comparison_label and comparison_label != "안정적":
            extra = COMPARISON_MESSAGES.get(comparison_label, "")
            if extra:
                message = extra

        # 중복 억제
        if not self._should_speak(message):
            return message

        self._last_message = message
        self._last_speak_time = time.time()

        # TTS 출력 (가능한 경우만, 비동기)
        if self._tts_available and self._engine is not None:
            thread = threading.Thread(target=self._do_speak, args=(message,), daemon=True)
            thread.start()

        return message

    def set_volume(self, volume: int):
        """볼륨 변경"""
        self.config.tts_volume = max(0, min(100, volume))
        self._update_volume()

    def set_enabled(self, enabled: bool):
        """음성 안내 ON/OFF"""
        self.config.tts_enabled = enabled

    def set_callbacks(self, on_start=None, on_end=None):
        """음성 시작/종료 콜백 (마이크 간섭 방지용)"""
        self._on_speak_start = on_start
        self._on_speak_end = on_end

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    @property
    def is_available(self) -> bool:
        return self._tts_available

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    def _should_speak(self, message: str) -> bool:
        """중복 억제"""
        now = time.time()
        if now - self._last_speak_time < self.config.tts_min_interval:
            return False
        if message == self._last_message:
            self._repeat_count += 1
            if self._repeat_count >= self.config.tts_max_repeat:
                return False
        else:
            self._repeat_count = 0
        return True

    def _do_speak(self, message: str):
        """실제 음성 출력 (별도 스레드, 모든 예외 내부 처리)"""
        self._speaking = True
        if self._on_speak_start:
            try:
                self._on_speak_start()
            except Exception:
                pass

        try:
            if self._engine is not None:
                self._engine.say(message)
                self._engine.runAndWait()
        except Exception:
            # TTS 실패해도 앱은 계속 동작
            self._tts_available = False
        finally:
            self._speaking = False
            if self._on_speak_end:
                try:
                    self._on_speak_end()
                except Exception:
                    pass

    def _update_volume(self):
        """엔진 볼륨 업데이트"""
        if self._engine is not None:
            try:
                self._engine.setProperty('volume', self.config.tts_volume / 100.0)
            except Exception:
                pass
