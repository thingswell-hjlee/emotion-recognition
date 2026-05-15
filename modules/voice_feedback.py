"""
modules/voice_feedback.py - 음성 안내 모듈
감정 상태를 짧은 문장으로 음성 출력합니다.
"""

import threading
import time
from typing import Optional, Dict

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

# 비교 결과별 추가 메시지
COMPARISON_MESSAGES: Dict[str, str] = {
    "안정적": "",
    "긍정 방향 변화": "감정이 긍정적으로 변하고 있습니다.",
    "부정 방향 변화": "감정이 부정적으로 변하고 있습니다.",
    "스트레스 증가 가능성": "스트레스가 증가하는 신호가 있습니다.",
    "감정 변동성 증가": "감정 변화가 커지고 있습니다.",
}


class VoiceFeedback:
    """감정 상태 음성 안내"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._engine = None
        self._initialized = False
        self._last_message = ""
        self._repeat_count = 0
        self._last_speak_time = 0.0
        self._speaking = False
        self._on_speak_start = None  # 콜백: 음성 시작 시
        self._on_speak_end = None  # 콜백: 음성 종료 시

    def initialize(self) -> bool:
        """TTS 엔진 초기화"""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', 150)
            self._update_volume()
            self._initialized = True
            return True
        except Exception as e:
            print(f"[WARNING] TTS 초기화 실패: {e}. 텍스트 안내만 제공합니다.")
            self._initialized = True  # 텍스트 모드로 동작
            return True

    def speak(self, emotion: str, comparison_label: Optional[str] = None) -> str:
        """
        감정 상태를 음성으로 안내합니다.

        Args:
            emotion: 대표 감정 레이블
            comparison_label: 비교 결과 레이블 (선택)

        Returns:
            안내 문장 텍스트
        """
        if not self.config.tts_enabled:
            return ""

        if not self._initialized:
            self.initialize()

        # 메시지 생성
        message = EMOTION_MESSAGES.get(emotion, "감정 상태를 분석 중입니다.")

        # 비교 결과 메시지 추가
        if comparison_label and comparison_label != "안정적":
            extra = COMPARISON_MESSAGES.get(comparison_label, "")
            if extra:
                message = extra  # 변화 메시지를 우선

        # 중복 억제
        if not self._should_speak(message):
            return message

        # 음성 출력 (비동기)
        self._last_message = message
        self._last_speak_time = time.time()

        if self._engine is not None:
            thread = threading.Thread(target=self._do_speak, args=(message,), daemon=True)
            thread.start()

        return message

    def set_volume(self, volume: int):
        """볼륨 변경 (0~100)"""
        self.config.tts_volume = max(0, min(100, volume))
        self._update_volume()

    def set_enabled(self, enabled: bool):
        """음성 안내 ON/OFF"""
        self.config.tts_enabled = enabled

    def set_callbacks(self, on_start=None, on_end=None):
        """음성 시작/종료 콜백 설정 (마이크 간섭 방지용)"""
        self._on_speak_start = on_start
        self._on_speak_end = on_end

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def _should_speak(self, message: str) -> bool:
        """중복 억제 로직"""
        now = time.time()

        # 최소 간격 체크
        if now - self._last_speak_time < self.config.tts_min_interval:
            return False

        # 동일 메시지 반복 횟수 체크
        if message == self._last_message:
            self._repeat_count += 1
            if self._repeat_count >= self.config.tts_max_repeat:
                return False
        else:
            self._repeat_count = 0

        return True

    def _do_speak(self, message: str):
        """실제 음성 출력 (별도 스레드)"""
        self._speaking = True
        if self._on_speak_start:
            self._on_speak_start()

        try:
            if self._engine is not None:
                self._engine.say(message)
                self._engine.runAndWait()
        except Exception:
            pass
        finally:
            self._speaking = False
            if self._on_speak_end:
                self._on_speak_end()

    def _update_volume(self):
        """엔진 볼륨 업데이트"""
        if self._engine is not None:
            try:
                vol = self.config.tts_volume / 100.0
                self._engine.setProperty('volume', vol)
            except Exception:
                pass
