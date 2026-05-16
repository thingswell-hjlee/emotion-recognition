"""
modules/voice_activity_detector.py - 음성 활동 감지 (VAD)
다중 기준 기반으로 유효한 음성 구간을 판별합니다.

단순 RMS 임계값 대신 복합 조건을 사용:
- RMS threshold
- Peak amplitude threshold
- Zero Crossing Rate
- 최소 유효 음성 길이
- 연속 유효 프레임 수
- 전체 발화 비율

출력 상태:
- VOICE_DETECTED: 유효한 음성 감지됨
- SILENCE_DETECTED: 무음 상태
- INSUFFICIENT_VOICE_DATA: 발화 있으나 시간/비율 부족
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config, DEFAULT_CONFIG


# === VAD 결과 상태 코드 ===
VAD_VOICE_DETECTED = "VOICE_DETECTED"
VAD_SILENCE_DETECTED = "SILENCE_DETECTED"
VAD_INSUFFICIENT_DATA = "INSUFFICIENT_VOICE_DATA"


@dataclass
class VADResult:
    """VAD 판별 결과"""
    status: str                 # VOICE_DETECTED / SILENCE_DETECTED / INSUFFICIENT_VOICE_DATA
    rms: float = 0.0           # 전체 RMS
    peak: float = 0.0          # peak amplitude
    dbfs: float = -96.0        # dBFS (0 = max, -96 = silence)
    zcr: float = 0.0           # zero crossing rate
    voice_ratio: float = 0.0   # 유효 발화 비율 (0~1)
    valid_seconds: float = 0.0 # 유효 발화 시간 (초)
    total_seconds: float = 0.0 # 전체 오디오 길이 (초)
    is_valid: bool = False     # 분석 가능 여부


class VoiceActivityDetector:
    """다중 기준 음성 활동 감지기"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config

    def analyze(self, audio: np.ndarray, sample_rate: int = 16000) -> VADResult:
        """
        오디오 데이터의 음성 활동을 분석합니다.

        Args:
            audio: float32 mono 오디오 데이터
            sample_rate: 샘플레이트 (Hz)

        Returns:
            VADResult with status and metrics
        """
        if audio is None or len(audio) == 0:
            return VADResult(status=VAD_SILENCE_DETECTED)

        total_seconds = len(audio) / sample_rate

        # 전체 메트릭 계산
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))
        dbfs = float(20 * np.log10(max(rms, 1e-10)))
        zcr = self._calculate_zcr(audio)

        # 프레임 단위 음성 활동 판별 (50ms 프레임)
        frame_size = int(sample_rate * 0.05)  # 50ms
        n_frames = max(1, len(audio) // frame_size)
        voice_frames = 0
        consecutive_voice = 0
        max_consecutive = 0

        for i in range(n_frames):
            start = i * frame_size
            end = min(start + frame_size, len(audio))
            frame = audio[start:end]

            if len(frame) == 0:
                continue

            frame_rms = float(np.sqrt(np.mean(frame ** 2)))
            frame_peak = float(np.max(np.abs(frame)))

            # 프레임이 유효한 음성인지 판별
            is_voice_frame = (
                frame_rms >= self.config.silence_threshold and
                frame_peak >= self.config.peak_threshold
            )

            if is_voice_frame:
                voice_frames += 1
                consecutive_voice += 1
                max_consecutive = max(max_consecutive, consecutive_voice)
            else:
                consecutive_voice = 0

        # 발화 비율과 유효 시간 계산
        voice_ratio = voice_frames / max(n_frames, 1)
        valid_seconds = voice_ratio * total_seconds

        # 최종 판정
        status = self._determine_status(
            rms, peak, zcr, voice_ratio, valid_seconds, max_consecutive
        )

        return VADResult(
            status=status,
            rms=rms,
            peak=peak,
            dbfs=dbfs,
            zcr=zcr,
            voice_ratio=voice_ratio,
            valid_seconds=valid_seconds,
            total_seconds=total_seconds,
            is_valid=(status == VAD_VOICE_DETECTED),
        )

    def _determine_status(self, rms: float, peak: float, zcr: float,
                          voice_ratio: float, valid_seconds: float,
                          max_consecutive: int) -> str:
        """최종 VAD 상태 결정"""
        # 1. 전체가 무음인지 확인
        if rms < self.config.silence_threshold * 0.5:
            return VAD_SILENCE_DETECTED

        # 2. peak도 낮으면 무음
        if peak < self.config.peak_threshold * 0.5:
            return VAD_SILENCE_DETECTED

        # 3. 발화 비율 체크
        if voice_ratio < self.config.min_voice_ratio:
            if voice_ratio < 0.05:  # 거의 없음
                return VAD_SILENCE_DETECTED
            return VAD_INSUFFICIENT_DATA

        # 4. 최소 유효 발화 시간 체크
        if valid_seconds < self.config.min_valid_voice_seconds:
            return VAD_INSUFFICIENT_DATA

        # 5. 연속 유효 프레임 체크
        if max_consecutive < self.config.vad_min_consecutive_frames:
            return VAD_INSUFFICIENT_DATA

        # 모든 조건 통과
        return VAD_VOICE_DETECTED

    def _calculate_zcr(self, audio: np.ndarray) -> float:
        """Zero Crossing Rate 계산"""
        if len(audio) < 2:
            return 0.0
        signs = np.sign(audio)
        sign_changes = np.abs(np.diff(signs))
        return float(np.mean(sign_changes > 0))

    def get_realtime_metrics(self, audio: np.ndarray) -> dict:
        """
        실시간 UI 표시용 메트릭 (빠른 계산).
        전체 VAD 없이 현재 RMS/peak만 반환.
        """
        if audio is None or len(audio) == 0:
            return {"rms": 0.0, "peak": 0.0, "dbfs": -96.0, "is_silence": True}

        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))
        dbfs = float(20 * np.log10(max(rms, 1e-10)))
        is_silence = rms < self.config.silence_threshold

        return {
            "rms": rms,
            "peak": peak,
            "dbfs": dbfs,
            "is_silence": is_silence,
        }
