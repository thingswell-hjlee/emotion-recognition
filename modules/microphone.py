"""
modules/microphone.py - 마이크 오디오 캡처 모듈
노트북 마이크에서 실시간 오디오를 수집하고 버퍼를 관리합니다.
"""

import numpy as np
import threading
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DEFAULT_CONFIG


class AudioRingBuffer:
    """고정 크기 링 버퍼로 오디오 데이터 관리"""

    def __init__(self, max_samples: int):
        self.max_samples = max_samples
        self.buffer = np.zeros(max_samples, dtype=np.float32)
        self.write_pos = 0
        self.total_written = 0
        self._lock = threading.Lock()

    def write(self, data: np.ndarray):
        """새 오디오 데이터 추가"""
        with self._lock:
            n = len(data)
            if n == 0:
                return

            if self.write_pos + n <= self.max_samples:
                self.buffer[self.write_pos:self.write_pos + n] = data
                self.write_pos += n
            else:
                overflow = (self.write_pos + n) - self.max_samples
                self.buffer[self.write_pos:] = data[:n - overflow]
                self.buffer[:overflow] = data[n - overflow:]
                self.write_pos = overflow

            self.total_written += n

    def read_all(self) -> np.ndarray:
        """버퍼 전체 데이터 반환 (복사본)"""
        with self._lock:
            if self.total_written >= self.max_samples:
                # 링 버퍼가 한 바퀴 이상 돌았으면 정렬하여 반환
                return np.concatenate([
                    self.buffer[self.write_pos:],
                    self.buffer[:self.write_pos]
                ]).copy()
            else:
                return self.buffer[:self.write_pos].copy()

    def clear(self):
        """버퍼 초기화"""
        with self._lock:
            self.buffer[:] = 0
            self.write_pos = 0
            self.total_written = 0

    @property
    def is_full(self) -> bool:
        return self.total_written >= self.max_samples

    @property
    def current_size(self) -> int:
        return min(self.total_written, self.max_samples)


class MicrophoneCapture:
    """실시간 마이크 오디오 캡처"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._stream = None
        self._sd = None
        self._is_opened = False
        self._is_capturing = False
        self._tts_playing = False

        buffer_size = config.audio_sample_rate * config.cycle_seconds
        self.buffer = AudioRingBuffer(buffer_size)

    def open(self) -> bool:
        """마이크를 열고 캡처 준비"""
        try:
            import sounddevice as sd
            self._sd = sd

            # 기본 입력 장치 확인
            device_info = sd.query_devices(kind='input')
            if device_info is None:
                return False

            self._is_opened = True
            return True

        except ImportError:
            print("[ERROR] sounddevice가 설치되지 않았습니다: pip install sounddevice")
            return False
        except Exception as e:
            print(f"[ERROR] 마이크 초기화 실패: {e}")
            return False

    def start_capture(self):
        """오디오 캡처 시작"""
        if not self._is_opened or self._sd is None:
            return

        if self._is_capturing:
            return

        try:
            self._stream = self._sd.InputStream(
                samplerate=self.config.audio_sample_rate,
                channels=self.config.audio_channels,
                dtype='float32',
                blocksize=self.config.audio_chunk_size,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._is_capturing = True
        except Exception as e:
            print(f"[ERROR] 오디오 캡처 시작 실패: {e}")

    def stop_capture(self):
        """오디오 캡처 정지"""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self._stream = None
        self._is_capturing = False

    def get_buffer(self) -> np.ndarray:
        """현재 버퍼의 오디오 데이터 반환"""
        return self.buffer.read_all()

    def clear_buffer(self):
        """버퍼 초기화"""
        self.buffer.clear()

    def update_cycle(self, new_cycle_seconds: int):
        """주기 변경 시 버퍼 크기 재설정"""
        new_size = self.config.audio_sample_rate * new_cycle_seconds
        self.buffer = AudioRingBuffer(new_size)
        self.config.cycle_seconds = new_cycle_seconds

    def is_silence(self) -> bool:
        """현재 버퍼가 무음인지 판단"""
        data = self.buffer.read_all()
        if len(data) == 0:
            return True
        rms = np.sqrt(np.mean(data ** 2))
        return rms < self.config.silence_threshold

    def set_tts_playing(self, playing: bool):
        """TTS 출력 중 마이크 간섭 방지"""
        self._tts_playing = playing

    def close(self):
        """마이크 리소스 해제"""
        self.stop_capture()
        self._is_opened = False

    @property
    def is_opened(self) -> bool:
        return self._is_opened

    @property
    def is_capturing(self) -> bool:
        return self._is_capturing

    def _audio_callback(self, indata, frames, time_info, status):
        """오디오 스트림 콜백 (별도 스레드에서 호출됨)"""
        if self._tts_playing:
            return  # TTS 출력 중에는 캡처 중단

        audio_data = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        self.buffer.write(audio_data)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
