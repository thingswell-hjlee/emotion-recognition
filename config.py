"""
config.py - 전역 설정
Multimodal Emotion State Monitor의 모든 설정값을 관리합니다.
"""

from dataclasses import dataclass, field
from typing import Dict
import os


# === 감정 카테고리 ===
EMOTIONS = [
    "neutral", "happy", "sad", "angry", "surprised",
    "fearful", "disgusted", "stressed", "calm"
]

# === 감정 이모지 매핑 ===
EMOTION_EMOJI: Dict[str, str] = {
    "neutral": "😐",
    "happy": "😊",
    "sad": "😢",
    "angry": "😠",
    "surprised": "😲",
    "fearful": "😨",
    "disgusted": "🤢",
    "stressed": "😰",
    "calm": "😌",
}

# === 감정 Valence (긍정/부정 가치) ===
EMOTION_VALENCE: Dict[str, float] = {
    "happy": 1.0,
    "calm": 0.7,
    "surprised": 0.2,
    "neutral": 0.0,
    "sad": -0.5,
    "disgusted": -0.6,
    "angry": -0.7,
    "fearful": -0.8,
    "stressed": -0.9,
}

# === DeepFace → 내부 감정 매핑 ===
DEEPFACE_TO_INTERNAL: Dict[str, str] = {
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
    "surprise": "surprised",
    "neutral": "neutral",
    "fear": "fearful",
    "disgust": "disgusted",
}


@dataclass
class Config:
    """전역 설정 데이터클래스"""

    # --- 카메라 설정 ---
    camera_device_id: int = 0
    frame_width: int = 640
    frame_height: int = 480
    analysis_skip_frames: int = 3  # N프레임마다 1회 표정 분석

    # --- 마이크 설정 ---
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_chunk_size: int = 1024
    silence_threshold: float = 0.01  # RMS 기반 무음 판단 임계값
    silence_duration: float = 2.0  # 무음 지속 시간 (초)

    # --- 분석 설정 ---
    cycle_seconds: int = 10  # 감정 인식 주기 (5~20초)
    cycle_min: int = 5
    cycle_max: int = 20
    face_weight: float = 0.6  # 통합 시 표정 가중치
    voice_weight: float = 0.4  # 통합 시 음성 가중치
    analysis_mode: str = "integrated"  # face_only / voice_only / integrated

    # --- LSTM 설정 ---
    lstm_sequence_length: int = 10  # 입력 시퀀스 길이 (주기 수)
    lstm_min_data_points: int = 5  # 예측 시작 최소 데이터
    lstm_model_path: str = "models/lstm_model.h5"
    lstm_n_features: int = 9  # 감정 카테고리 수

    # --- TTS (음성 안내) 설정 ---
    tts_enabled: bool = True
    tts_volume: int = 70  # 0~100
    tts_min_interval: int = 10  # 동일 메시지 최소 간격 (초)
    tts_max_repeat: int = 3  # 동일 메시지 최대 연속 횟수
    tts_language: str = "ko"  # 한국어

    # --- UI 설정 ---
    window_title: str = "Multimodal Emotion State Monitor"
    log_max_size: int = 50  # UI 로그 최대 줄 수

    # --- 비교 임계값 ---
    comparison_stable_threshold: float = 0.05  # 안정적 판단 임계값
    comparison_stress_threshold: float = 0.1  # 스트레스 증가 판단 임계값
    comparison_volatile_threshold: float = 0.15  # 변동성 증가 판단 임계값

    # --- 파일 경로 ---
    log_file_path: str = "logs/emotion_log.jsonl"
    config_file_path: str = "config.json"
    voice_model_path: str = "models/voice_emotion_model.pkl"

    def validate(self) -> bool:
        """설정값 유효성 검증"""
        assert self.cycle_min <= self.cycle_seconds <= self.cycle_max, \
            f"cycle_seconds must be between {self.cycle_min} and {self.cycle_max}"
        assert 0 <= self.tts_volume <= 100, "tts_volume must be 0~100"
        assert 0.0 <= self.face_weight <= 1.0, "face_weight must be 0.0~1.0"
        assert 0.0 <= self.voice_weight <= 1.0, "voice_weight must be 0.0~1.0"
        assert self.analysis_mode in ("face_only", "voice_only", "integrated"), \
            "Invalid analysis_mode"
        return True

    def update_cycle(self, new_cycle: int):
        """주기 변경 (범위 제한 적용)"""
        self.cycle_seconds = max(self.cycle_min, min(self.cycle_max, new_cycle))

    def update_volume(self, new_volume: int):
        """볼륨 변경 (범위 제한 적용)"""
        self.tts_volume = max(0, min(100, new_volume))


# === 기본 설정 인스턴스 ===
DEFAULT_CONFIG = Config()
