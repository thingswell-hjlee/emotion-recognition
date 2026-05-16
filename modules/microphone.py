"""
modules/microphone.py - 마이크 오디오 캡처 모듈
노트북 마이크에서 실시간 오디오를 수집하고 버퍼를 관리합니다.

강화된 기능:
- 장치 목록 조회 (query_devices)
- 장치 선택 (device_id 지정)
- 실시간 메트릭 (RMS, peak, dBFS)
- 장치 정보 (이름, SR, 채널)
- TTS 간섭 방지
"""

import numpy as np
import threading
from typing import Optional, List, Dict
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DEFAULT_CONFIG


@dataclass
class AudioDeviceInfo:
    """마이크 장치 정보"""
    device_id: int
    name: str
    sample_rate: float
    channels: int
    is_default: bool = False


@dataclass
class AudioMetrics:
    """실시간 오디오 메트릭"""
    rms: float = 0.0
    peak: float = 0.0
    dbfs: float = -96.0
    is_silence: bool = True
    buffer_seconds: float = 0.0
    buffer_samples: int = 0


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
                return np.concatenate([
                    self.buffer[self.write_pos:],
                    self.buffer[:self.write_pos]
                ]).copy()
            else:
                return self.buffer[:self.write_pos].copy()

    def read_recent(self, n_samples: int) -> np.ndarray:
        """최근 N개 샘플만 반환 (실시간 메트릭용)"""
        with self._lock:
            available = min(self.total_written, self.max_samples)
            n = min(n_samples, available)
            if n == 0:
                return np.zeros(0, dtype=np.float32)
            # 가장 최근 n개
            end = self.write_pos
            start = end - n
            if start >= 0:
                return self.buffer[start:end].copy()
            else:
                return np.concatenate([
                    self.buffer[start:],
                    self.buffer[:end]
                ]).copy()

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
    """실시간 마이크 오디오 캡처 (장치 정보 + 메트릭 기능 강화)"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self._stream = None
        self._sd = None
        self._is_opened = False
        self._is_capturing = False
        self._tts_playing = False
        self._device_info: Optional[AudioDeviceInfo] = None

        buffer_size = config.audio_sample_rate * config.cycle_seconds
        self.buffer = AudioRingBuffer(buffer_size)

    # ================================================================
    # 장치 관리
    # ================================================================

    def open(self, device_id: Optional[int] = None) -> bool:
        """
        마이크를 열고 캡처 준비.

        Args:
            device_id: 특정 장치 ID (None이면 config 또는 시스템 기본값)
        """
        try:
            import sounddevice as sd
            self._sd = sd

            # 장치 ID 결정
            target_id = device_id or self.config.audio_device_id

            if target_id is not None:
                info = sd.query_devices(target_id)
            else:
                info = sd.query_devices(kind='input')
                target_id = sd.default.device[0]  # 기본 입력 장치

            if info is None:
                return False

            # 장치 정보 저장
            self._device_info = AudioDeviceInfo(
                device_id=target_id if target_id is not None else 0,
                name=info.get('name', 'Unknown'),
                sample_rate=info.get('default_samplerate', 16000),
                channels=info.get('max_input_channels', 1),
                is_default=(target_id == sd.default.device[0]),
            )

            self._is_opened = True
            return True

        except ImportError:
            print("[ERROR] sounddevice가 설치되지 않았습니다: pip install sounddevice")
            return False
        except Exception as e:
            print(f"[ERROR] 마이크 초기화 실패: {e}")
            return False

    @staticmethod
    def list_devices() -> List[AudioDeviceInfo]:
        """사용 가능한 입력 장치 목록 반환"""
        try:
            import sounddevice as sd
            devices = []
            all_devices = sd.query_devices()
            default_input = sd.default.device[0]

            for i, dev in enumerate(all_devices):
                if dev.get('max_input_channels', 0) > 0:
                    devices.append(AudioDeviceInfo(
                        device_id=i,
                        name=dev.get('name', f'Device {i}'),
                        sample_rate=dev.get('default_samplerate', 16000),
                        channels=dev.get('max_input_channels', 1),
                        is_default=(i == default_input),
                    ))
            return devices

        except ImportError:
            return []
        except Exception:
            return []

    def get_device_info(self) -> Optional[AudioDeviceInfo]:
        """현재 열려있는 장치 정보 반환"""
        return self._device_info

    def select_device(self, device_id: int) -> bool:
        """장치 변경 (캡처 중이면 재시작)"""
        was_capturing = self._is_capturing
        if was_capturing:
            self.stop_capture()

        self.close()
        success = self.open(device_id=device_id)

        if success and was_capturing:
            self.start_capture()

        return success

    # ================================================================
    # 캡처 제어
    # ================================================================

    def start_capture(self):
        """오디오 캡처 시작"""
        if not self._is_opened or self._sd is None:
            return

        if self._is_capturing:
            return

        try:
            device_id = self._device_info.device_id if self._device_info else None
            self._stream = self._sd.InputStream(
                device=device_id,
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

    # ================================================================
    # 데이터 접근
    # ================================================================

    def get_buffer(self) -> np.ndarray:
        """현재 버퍼의 전체 오디오 데이터 반환"""
        return self.buffer.read_all()

    def clear_buffer(self):
        """버퍼 초기화"""
        self.buffer.clear()

    def update_cycle(self, new_cycle_seconds: int):
        """주기 변경 시 버퍼 크기 재설정"""
        new_size = self.config.audio_sample_rate * new_cycle_seconds
        self.buffer = AudioRingBuffer(new_size)

    # ================================================================
    # 실시간 메트릭
    # ================================================================

    def get_metrics(self) -> AudioMetrics:
        """
        실시간 오디오 메트릭 반환.
        UI에서 RMS/peak/dBFS/silence 상태를 표시하는 데 사용합니다.
        """
        # 최근 0.5초 데이터로 계산 (빠른 반응)
        recent_samples = int(self.config.audio_sample_rate * 0.5)
        data = self.buffer.read_recent(recent_samples)

        if len(data) == 0:
            return AudioMetrics()

        rms = float(np.sqrt(np.mean(data ** 2)))
        peak = float(np.max(np.abs(data)))
        dbfs = float(20 * np.log10(max(rms, 1e-10)))
        is_silence = rms < self.config.silence_threshold

        buffer_total = self.buffer.current_size
        buffer_seconds = buffer_total / self.config.audio_sample_rate

        return AudioMetrics(
            rms=rms,
            peak=peak,
            dbfs=dbfs,
            is_silence=is_silence,
            buffer_seconds=buffer_seconds,
            buffer_samples=buffer_total,
        )

    def is_silence(self) -> bool:
        """현재 버퍼가 무음인지 판단 (간단 버전)"""
        metrics = self.get_metrics()
        return metrics.is_silence

    # ================================================================
    # TTS 간섭 방지
    # ================================================================

    def set_tts_playing(self, playing: bool):
        """TTS 출력 중 마이크 간섭 방지"""
        self._tts_playing = playing

    # ================================================================
    # 리소스 관리
    # ================================================================

    def close(self):
        """마이크 리소스 해제"""
        self.stop_capture()
        self._is_opened = False
        self._device_info = None

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
